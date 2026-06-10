# CI/CD & Deployment — Hands-On Guide (SiningAI)

This guide walks you through four ways to build, test, and deploy the **same app** —
SiningAI, a Python AI agent backend plus a Vite/React frontend. By the end you will have
read, run, and broken real config files instead of memorising abstract definitions.

---

## Before you start

**The one distinction that makes everything click:**

Three of these tools — GitHub Actions, GitLab CI/CD, and Jenkins — are **pipeline
orchestrators**. They watch for events (a push, a PR, a schedule) and then run a sequence
of steps automatically.

Docker Compose is something different entirely. It is a **runtime definer**. It does not
watch for events or run pipelines. It just describes a set of containers and starts them.

A pipeline often *calls* Docker Compose as one of its steps. They are not competing tools.

| Tool | Category | What it watches | What it does when triggered |
|---|---|---|---|
| GitHub Actions | Pipeline orchestrator | Push / PR / schedule | Runs a YAML workflow on a GitHub-hosted VM |
| GitLab CI/CD | Pipeline orchestrator | Push / MR / schedule | Runs `.gitlab-ci.yml` on a GitLab runner |
| Jenkins | Pipeline orchestrator | Push (webhook) / manual | Runs a `Jenkinsfile` on your own server |
| Docker Compose | Runtime definer | Nothing — you run it | Starts and connects a set of containers |

---

## Repository layout

```
siningai/
├── siningai_agent/          ← Python ADK agent (the AI backend)
│   ├── Dockerfile           ← build context is repo ROOT, not this folder (see Method 1)
│   ├── agent.py
│   ├── __init__.py
│   └── .env                 ← gitignored; never baked into the image
├── frontend/                ← Vite + React + Tailwind
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
├── requirements.txt         ← at REPO ROOT — this is why build context matters
├── docker-compose.yml
├── .github/workflows/
│   └── build-and-push.yml
├── .gitlab-ci.yml
└── Jenkinsfile
```

> **Why does `requirements.txt` live at the root?**
> ADK (the Python framework the agent uses) expects to be run from the parent directory of the
> agent package — i.e., from `siningai/`, not from inside `siningai_agent/`. Running from the
> root is also how `adk api_server` discovers the agent by its folder name.
> The consequence: every Docker build must use `.` as its context (not `./siningai_agent`).

---

## Method 1 — Docker Compose

**File:** `docker-compose.yml`  
**Goal:** get the entire stack running locally with one command.

### Run it

```bash
# from the siningai/ directory
docker compose up --build
```

After about 30 seconds:
- Frontend (nginx): `http://localhost:5173`
- Agent API: `http://localhost:8000`

To also start a local MongoDB MCP server instead of using the Cloud Run one:

```bash
docker compose --profile full up --build
```

### Read the file — key decisions explained

**Service: `backend`**

```yaml
build:
  context: .                        # repo root — requirements.txt is here
  dockerfile: siningai_agent/Dockerfile
env_file:
  - ./siningai_agent/.env           # secrets loaded at runtime, not baked in
environment:
  PORT: "8000"                      # overrides the Cloud Run default (8080)
```

Two things to notice:

1. The build context is `.` (repo root), not `./siningai_agent`. If you set it to
   `./siningai_agent`, the `COPY requirements.txt .` step inside the Dockerfile would fail
   because `requirements.txt` would not be in scope. This is the most common Docker context
   mistake beginners make.

2. `env_file` passes the `.env` file to the *running container*. The `.env` file is never
   copied into the image itself. This means you can rebuild the image and ship it to anyone
   without leaking credentials.

**Service: `frontend`**

```yaml
build:
  args:
    VITE_API_URL: "http://localhost:8000"
ports:
  - "5173:80"
depends_on:
  backend:
    condition: service_healthy
```

Two things to notice:

1. `VITE_API_URL` is a build argument, not an environment variable. Vite bakes
   `VITE_*` variables into the static bundle *at build time*. You cannot change this value
   after the image is built — if you switch API URLs you must rebuild the image.

2. `condition: service_healthy` means Docker will not start nginx until the agent's
   `HEALTHCHECK` passes (a `GET /list-apps` that must return 200). This is real startup
   ordering, not a sleep hack.

**Service: `mcp` (profile: full)**

```yaml
command: ["--transport", "http", "--httpHost", "0.0.0.0", "--httpPort", "3000"]
profiles: ["full"]
```

The MCP server binds to `127.0.0.1` by default. Without `--httpHost 0.0.0.0`, other
containers cannot reach it even on the same Compose network. Try removing that flag,
rebuild, and watch the agent fail to connect — then add it back.

### Checkpoint

1. Run `docker compose up --build`. Confirm both URLs respond.
2. Run `docker compose ps`. What does the `STATUS` column show for `backend`?
3. Break it intentionally: open `siningai_agent/Dockerfile` and change the `HEALTHCHECK`
   path to `/wrong-path`. Rebuild. What happens to `frontend`?
4. Fix it, then run `docker compose --profile full up --build`. What new port appears?

---

## Method 2 — GitHub Actions

**File:** `.github/workflows/build-and-push.yml`  
**Goal:** every push to `main` builds the agent container and pushes it to GitHub Container
Registry (GHCR). Pull requests build but do not push.

### How to activate it

Drop the file at `.github/workflows/build-and-push.yml` in your repo, push, and open the
**Actions** tab. No secrets need to be configured — GHCR auth uses the auto-injected
`GITHUB_TOKEN`.

### Read the file — key decisions explained

**Triggers**

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

This runs on two different events. The `push` event fires when a commit lands on `main`.
The `pull_request` event fires when a PR *targets* `main` — the branch doesn't need to be
merged yet. You get build feedback on PRs before anything ships.

**Least-privilege permissions**

```yaml
permissions:
  contents: read
  packages: write
```

By default a GitHub Actions job gets a token with broad repo permissions. Explicitly
declaring `contents: read` + `packages: write` drops everything else. If this job is ever
compromised, the blast radius is limited to pushing images — it cannot push code, create
releases, or manage secrets.

**Conditional push**

```yaml
- name: Log in to GHCR
  if: github.event_name != 'pull_request'

- name: Build and push
  with:
    push: ${{ github.event_name != 'pull_request' }}
```

The same workflow handles both events. On a PR it builds (to prove nothing is broken) but
does not log in or push. On a push to `main` it does both. One file, two behaviours.

**Build context**

```yaml
context: .
file: ./siningai_agent/Dockerfile
```

Same rule as Compose: context is the repo root so `requirements.txt` is in scope.

**Image tagging**

```yaml
tags: |
  type=sha,format=long      # e.g. sha-abc1234...  — immutable, great for rollbacks
  type=ref,event=branch     # e.g. main
  type=raw,value=latest,enable={{is_default_branch}}
```

Every push gets a unique SHA tag you can roll back to. `latest` only moves on the default
branch, so feature branches never pollute the tag that production pulls from.

**Layer caching**

```yaml
cache-from: type=gha
cache-to:   type=gha,mode=max
```

GitHub stores Docker layer cache between runs. A code-only change reuses cached dependency
layers and drops build time from ~2 min to ~20 s.

### Checkpoint

1. Push this file and open the Actions tab. Which steps take the longest?
2. Open a pull request (change a comment). Does the job push an image? Check GHCR.
3. Find the SHA tag for your last `main` push. How would you pull that exact image locally?
4. Remove the `cache-from`/`cache-to` lines, push again, and compare build times.

---

## Method 3 — GitLab CI/CD

**File:** `.gitlab-ci.yml`  
**Goal:** validate the frontend build on every push; deploy a live preview URL on merge
requests; deploy to production on merge to `main`.

### Setup (one-time)

```bash
# 1. Link your project to Vercel
cd frontend
vercel link     # creates .vercel/project.json with org and project IDs

# 2. Add three variables in GitLab: Settings → CI/CD → Variables (mask all three)
#    VERCEL_TOKEN      – from vercel.com/account/tokens
#    VERCEL_ORG_ID     – from .vercel/project.json
#    VERCEL_PROJECT_ID – from .vercel/project.json
```

### Read the file — key decisions explained

**Stages**

```yaml
stages:
  - validate
  - deploy
```

Stages run in order. All jobs in `validate` must pass before any job in `deploy` starts.
If your build breaks, Vercel is never called — you get the error immediately without
wasting a deploy.

**Dependency caching**

```yaml
cache:
  key:
    files:
      - frontend/package-lock.json
  paths:
    - frontend/node_modules/
```

`node_modules/` is cached and keyed to the lockfile hash. If `package-lock.json` has not
changed since the last run, `npm ci` skips the full install and restores from cache. This
turns a 45-second install into a 3-second restore.

**Three jobs, three situations**

```yaml
# Job 1: runs on EVERY push and MR
build:validate:
  stage: validate
  script:
    - cd frontend && npm ci && npm run build

# Job 2: runs ONLY on merge requests
deploy:preview:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - vercel deploy --prebuilt --token="$VERCEL_TOKEN"
  environment:
    name: review/$CI_COMMIT_REF_SLUG   # GitLab creates a named environment per branch

# Job 3: runs ONLY on the default branch
deploy:production:
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  script:
    - vercel deploy --prebuilt --prod --token="$VERCEL_TOKEN"
  environment:
    name: production
    url: https://siningai.vercel.app
```

The Vercel deploy pattern — `vercel pull → vercel build → vercel deploy --prebuilt` —
compiles locally on the runner, then ships only the output. Building locally is faster and
more reproducible than letting Vercel re-build from source on their servers.

### Checkpoint

1. What prevents the `deploy:preview` job from running on a direct push to `main`?
2. What prevents the `deploy:production` job from running on a feature branch?
3. If `npm run build` fails in `build:validate`, does `deploy:preview` run? Why not?
4. Open a merge request on GitLab and find the preview URL under
   **Operate → Environments → review/your-branch**.

---

## Method 4 — Jenkins

**File:** `Jenkinsfile`  
**Goal:** build the agent image, push to Google Artifact Registry, and deploy to Cloud Run.

### Setup — running Jenkins locally with Docker

The base Jenkins image has no `docker` CLI or `gcloud` inside it. You need a custom image
that includes both. Create a file called `Dockerfile.jenkins` anywhere convenient:

```dockerfile
FROM jenkins/jenkins:lts-jdk17
USER root

# Docker CLI — lets Jenkins run `docker build` and `docker push`
RUN apt-get update && apt-get install -y docker.io

# gcloud CLI — lets Jenkins run `gcloud run deploy`
RUN curl -sSL https://sdk.cloud.google.com | bash -s -- --disable-prompts
ENV PATH="/root/google-cloud-sdk/bin:$PATH"

# Allow the jenkins user to run docker without sudo
RUN usermod -aG docker jenkins

USER jenkins
```

Build and start it:

```bash
# Build the custom image once
docker build -f Dockerfile.jenkins -t jenkins-with-gcloud .

# Run Jenkins
# -v jenkins_home persists all config between restarts
# -v /var/run/docker.sock mounts the host Docker socket so Jenkins can build images
docker run -d \
  --name jenkins \
  -p 8080:8080 \
  -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  jenkins-with-gcloud
```

Open `http://localhost:8080`. Get the first-time unlock password:

```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Paste it into the browser, install the **suggested plugins**, and create an admin user.

> **Why `-v /var/run/docker.sock:/var/run/docker.sock`?**  
> This mounts your machine's Docker daemon into the container. When Jenkins runs
> `docker build`, it uses your host's Docker — so built images appear in your local
> `docker images` list and can be pushed from there. The alternative (Docker-in-Docker)
> is more isolated but significantly harder to set up.

**Add the GCP credential**

*Manage Jenkins → Credentials → System → Global → Add Credential*

- **Kind:** Secret file
- **ID:** `gcp-sa-key` ← must match the `credentialsId` in the Jenkinsfile exactly
- **File:** your GCP service-account JSON key

The service account needs three IAM roles on project `cryptic-now-495905-r2`:
- `roles/artifactregistry.writer`
- `roles/run.admin`
- `roles/iam.serviceAccountUser`

**Create the pipeline job**

*New Item → Pipeline* (not Multibranch for a quick local test)

- Under **Pipeline → Definition**, choose **Pipeline script from SCM**
- SCM: Git, paste your repo URL
- Script Path: `Jenkinsfile`
- Save, then click **Build Now**

Watch the stage view update in real time. Click any stage to expand its console output.

**Verify `docker` and `gcloud` are available before your first real build:**

```bash
docker exec -it jenkins bash
docker --version
gcloud --version
exit
```

If either command is missing, rebuild the `Dockerfile.jenkins` image and recreate the
container.

### Read the file — key decisions explained

**Environment block**

```groovy
environment {
    REGISTRY      = 'us-central1-docker.pkg.dev'
    GCP_PROJECT   = 'cryptic-now-495905-r2'
    AR_REPO       = 'siningai-images'
    IMAGE         = "${REGISTRY}/${GCP_PROJECT}/${AR_REPO}/siningai-agent"
    CLOUD_RUN_SVC = 'siningai-agent'
    REGION        = 'us-central1'
}
```

These are Groovy strings, resolved once at pipeline start. `IMAGE` is assembled from the
other variables so there is one place to change the registry or region.

**Immutable image tags**

```groovy
env.TAG = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
sh 'docker build -f siningai_agent/Dockerfile -t $IMAGE:$TAG -t $IMAGE:latest .'
```

The short commit SHA is used as a tag. Unlike `latest`, SHA tags are immutable — you can
always roll back by re-deploying `$IMAGE:abc1234`. `latest` is also pushed, as a
convenience for "give me the most recent build."

**Secret injection with `withCredentials`**

```groovy
withCredentials([file(credentialsId: 'gcp-sa-key', variable: 'GCP_KEY')]) {
    sh 'gcloud auth activate-service-account --key-file="$GCP_KEY"'
}
```

`withCredentials` writes the JSON key to a temporary file, makes the path available as
`$GCP_KEY` for that block only, then deletes the file and removes the variable from the
environment. The key is never in plain text in logs or environment dumps outside this block.

**Config vs. secrets in Cloud Run**

```groovy
--set-env-vars  GOOGLE_GENAI_USE_VERTEXAI=TRUE,...,SININGAI_MODEL=gemini-2.5-pro
--set-secrets   MCP_SERVER_URL=mcp-server-url:latest
```

`--set-env-vars` values are visible in `gcloud run services describe` output. Use them
for non-sensitive config. `--set-secrets` pulls from Secret Manager at deploy time — the
actual value never appears in any gcloud output or log. Rule: if you would be embarrassed
to see it in a screenshot, it belongs in `--set-secrets`.

**Branch guard on the deploy stage**

```groovy
stage('Deploy to Cloud Run') {
    when { branch 'main' }
```

All stages before this one run on every branch. Only `main` reaches Cloud Run. Feature
branches get build + push (you can pull and test the image) without touching production.

**`post` block**

```groovy
post {
    success { echo "✅ Deployed ..." }
    failure { echo "❌ Pipeline failed ..." }
    always  { sh 'docker image prune -f || true' }
}
```

`post` runs after all stages regardless of outcome. The `always` block prunes dangling
images to reclaim disk on the Jenkins agent. `|| true` prevents a failed prune from
marking the pipeline as failed.

### Checkpoint

1. What would happen if you changed `when { branch 'main' }` to `when { branch 'dev' }`?
2. If the "Push image" stage fails, does the `always` post block still run?
3. Why does `withCredentials` use a file type instead of a username/password?
4. Find the `--set-env-vars` line. Which of those values would be dangerous to put
   in `--set-secrets` instead, and why? (Hint: there is no wrong answer — it's a
   judgment call. Discuss your reasoning.)

---

## Common errors and how to fix them

### Docker build says "file not found: requirements.txt"

**Cause:** Build context is `./siningai_agent` instead of `.` (repo root).  
**Fix:** In `docker-compose.yml` and wherever you call `docker build`, make sure
`context: .` and point to the Dockerfile explicitly with `dockerfile: siningai_agent/Dockerfile`
or `-f siningai_agent/Dockerfile`.

### Frontend container starts but immediately exits

**Cause:** `depends_on: condition: service_healthy` is waiting, but the backend
HEALTHCHECK never passes because the agent failed to start.  
**Fix:** Run `docker compose logs backend` to see the agent's startup error. Common
causes: missing env vars in `.env`, wrong `MCP_SERVER_URL`, or a Python import error.

### GitHub Actions builds but does not push

**Cause:** The event was a pull request, not a push to `main`. This is intentional.  
**Verify:** Check the `if: github.event_name != 'pull_request'` condition on the login
step. PRs build to prove nothing is broken — they never push.

### GitLab `deploy:preview` says "VERCEL_TOKEN: not found"

**Cause:** The variable was not added in GitLab Settings → CI/CD → Variables, or it was
added as a project variable but the pipeline is running in a fork (masked variables are
not passed to fork MR pipelines by default).  
**Fix:** Check **Settings → CI/CD → Variables**. Ensure "Expand variable reference" is
off if the token contains `$` characters.

### Jenkins pipeline passes on feature branches but fails on `main` with "permission denied"

**Cause:** The Cloud Run deploy stage only runs on `main`, so that is the first time
the GCP service-account credentials are exercised. The credential likely has the wrong
roles or was added under the wrong scope.  
**Fix:** In **Manage Jenkins → Credentials**, verify the credential type is "Secret file"
(not "Secret text") and the JSON key has the three required IAM roles.

### Cloud Run service starts but the agent cannot reach MongoDB

**Cause:** `MCP_SERVER_URL` is wrong or missing. The agent talks to MongoDB exclusively
through the MCP server at that URL — it has no direct database connection.  
**Fix:** In the Jenkins `--set-secrets` line, verify the Secret Manager secret named
`mcp-server-url` exists and contains the correct Cloud Run URL
(`https://…asia-east1.run.app/mcp`).

---

## Exercises

These are meant to be done after you have read all four config files.

**Exercise 1 — Trace an environment variable**  
Pick `SININGAI_MODEL`. Find every file where it appears. Draw a diagram showing how it
flows from `siningai_agent/.env` (local) and from Jenkins `--set-env-vars` (Cloud Run)
into the running Python process.

**Exercise 2 — Add a test step**  
The GitHub Actions workflow builds and pushes but never runs tests. Add a new job called
`test` that runs before `build-and-push`. It should install dependencies and run
`python -m pytest` (even if there are no tests yet — a zero-test run still proves the
import chain works). Make `build-and-push` depend on `test` passing.

**Exercise 3 — Add a staging environment**  
The Jenkinsfile deploys directly to production on `main`. Add a `staging` Cloud Run
service and a `Deploy to Staging` stage that runs on every branch (not just `main`),
deploying with `--no-traffic` so it does not receive live traffic. How would you promote
staging to production?

**Exercise 4 — Understand the port contract**  
The Dockerfile sets `ENV PORT=8080`. The Compose file sets `PORT: "8000"`. The
`vite.config.js` proxy points to `localhost:8000`. Map out what would break if you
changed the Compose `PORT` to `9000` without changing anything else. Then fix all three
files to use 9000 consistently.

**Exercise 5 — Secret vs. config**  
Look at the Jenkinsfile `--set-env-vars` and `--set-secrets` split. Justify, in writing,
why each value is on the side it is on. Then argue the other direction for at least one
value. There is no single right answer — the exercise is the reasoning.

---

## Quick reference

| Task | Command |
|---|---|
| Start the full local stack | `docker compose up --build` |
| Start with local MCP server | `docker compose --profile full up --build` |
| Tear down and remove volumes | `docker compose down -v` |
| View backend logs | `docker compose logs -f backend` |
| Rebuild one service | `docker compose up --build backend` |
| Pull a specific image by SHA tag | `docker pull ghcr.io/<owner>/<repo>/siningai-agent:sha-<hash>` |
| Check the ADK API locally | `curl http://localhost:8000/list-apps` |
| Run the agent without Docker | `cd siningai/ && adk api_server --allow_origins "*"` |

| Concept | Short answer |
|---|---|
| Why is build context `.` not `./siningai_agent`? | `requirements.txt` is at root |
| Why is `VITE_API_URL` a build ARG not an env var? | Vite bakes it in at compile time |
| Why does `mcp` use `--httpHost 0.0.0.0`? | Default binds to 127.0.0.1; other containers can't reach that |
| Why pin action/image versions? | Floating `latest` can silently change and break a demo |
| Config vs. secret in Cloud Run? | Config: visible in `gcloud run services describe`. Secret: never visible. |
