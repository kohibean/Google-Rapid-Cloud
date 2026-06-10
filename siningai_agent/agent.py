"""
SiningAI — The Continuity Engine for creative work.

A multi-agent system that helps artists save versions of their work,
track sessions, and resume seamlessly. Built with Google ADK + Gemini,
backed by MongoDB via the MongoDB MCP server.
"""

import os
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from .voyage_client import embed_multimodal, embed_text

# ---------------------------------------------------------------------------
# MongoDB MCP connection
# ---------------------------------------------------------------------------
# Points at the MongoDB MCP server already deployed on Cloud Run.
# The server speaks the streamable-HTTP transport at the /mcp path.
# Override with the MCP_SERVER_URL env var if the URL changes.

MCP_SERVER_URL = os.environ.get(
    "MCP_SERVER_URL",
    "https://siningai-mcp-13428819940.asia-east1.run.app/mcp",
)

mongodb_tools = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=MCP_SERVER_URL,
    )
)

# Model used by all agents. Gemini 3.5 Flash: fast, vision-capable, agentic.
MODEL = os.environ.get("SININGAI_MODEL", "gemini-2.5-flash")

# ---------------------------------------------------------------------------
# Embedding tools (Voyage AI via MongoDB Atlas hosted endpoint)
# ---------------------------------------------------------------------------

def _embed_artwork(description: str, image_base64: str = "") -> dict:
    """Embed an artwork description and optional image using Voyage AI.

    Uses voyage-multimodal-3 when an image is supplied, falls back to
    voyage-3 for text-only. Returns {"embedding": [...], "dim": 1024} on
    success or {"error": "<message>"} so the caller can degrade gracefully.

    Args:
        description: Text description of the artwork (1-2 sentences).
        image_base64: Base64-encoded image string, with or without data URI prefix.
    """
    try:
        if image_base64:
            vector = embed_multimodal(text=description or None, image_b64=image_base64)
        else:
            vector = embed_text(description)
        return {"embedding": vector, "dim": len(vector)}
    except Exception as exc:
        return {"error": str(exc)}


def _embed_query(query: str) -> dict:
    """Embed a search query string using voyage-3 with query input_type.

    Returns {"embedding": [...], "dim": 1024} on success or {"error": "<message>"}.

    Args:
        query: The user's search or similarity query text.
    """
    try:
        vector = embed_text(query, input_type="query")
        return {"embedding": vector, "dim": len(vector)}
    except Exception as exc:
        return {"error": str(exc)}


embed_artwork_tool = FunctionTool(func=_embed_artwork)
embed_query_tool = FunctionTool(func=_embed_query)

# ---------------------------------------------------------------------------
# Sub-agent: version_analyzer
# ---------------------------------------------------------------------------
version_analyzer = Agent(
    name="version_analyzer",
    model=MODEL,
    description=(
        "Analyzes an artwork image, classifies its stage, and saves it as a "
        "new version in MongoDB."
    ),
    instruction="""You analyze images of creative work and save them as versions.

When given an image and an artwork title (ask for the title if not provided):

1. CLASSIFY the stage as exactly one of:
   - "sketch": rough lines or gesture, no color, early exploration
   - "wip_early": basic shapes, values, or colors blocked in
   - "wip_late": most details present, refinement underway
   - "final": polished and complete

2. DESCRIBE: write 1-2 sentences noting subject, medium, and dominant colors.

3. EMBED: call embed_artwork with the description from step 2. If the user provided
   an image, also pass its base64 data as image_base64. Store the returned
   {"embedding": [...], "dim": 1024}. If the call returns {"error": "..."}, note
   the error and continue — saving the version without an embedding is better
   than failing entirely.

4. RESOLVE the artwork: use the MongoDB find tool to look in the "artworks"
   collection (database "siningai") for a document with this title.
   - If none exists, insert a new artwork document with: title, medium ("visual"),
     status ("in_progress"), current_stage (your classification), created_at (now),
     total_sessions (0), tags ([]). Keep the new _id.
   - If it exists, note its _id and update current_stage and updated_at.

5. SAVE the version: insert into the "versions" collection with:
   - artwork_id (the resolved _id, as a string)
   - version_num (count existing versions for this artwork + 1)
   - created_at (current ISO timestamp)
   - stage (your classification)
   - auto_description (your 1-2 sentence description)
   - embedding (the vector array from step 3; omit the field entirely if step 3
     returned an error)

6. CONFIRM to the user:
   "Saved version [N] of '[title]' at [stage] stage — [one-line description]."

Never critique the work. Only observe and record.
""",
    tools=[mongodb_tools, embed_artwork_tool],
)

# ---------------------------------------------------------------------------
# Sub-agent: session_tracker
# ---------------------------------------------------------------------------
session_tracker = Agent(
    name="session_tracker",
    model=MODEL,
    description=(
        "Opens and closes work sessions, capturing what the artist did and what "
        "they plan to do next."
    ),
    instruction="""You track work sessions so the artist can resume seamlessly later.
All data lives in the "siningai" database.

STARTING A SESSION (user says "starting", "working on [piece]", "begin session"):
1. Resolve or create the artwork in the "artworks" collection by title.
2. Insert into the "sessions" collection: artwork_id, started_at (now ISO
   timestamp), user_notes (their stated focus, if any).
3. Reply: "Session started for '[title]'. I'll keep track. What are you focusing
   on this session?"

ENDING A SESSION (user says "wrapping up", "done for now", "ending session",
"stopping"):
1. Find the most recent OPEN session (no ended_at) for that artwork.
2. Ask, if not already provided: "What did you get done, and what do you want to
   tackle next time?"
3. Update the session with: ended_at (now), duration_minutes (ended_at minus
   started_at), user_notes (what they did), stated_intentions (what's next).
4. Increment the artwork's total_sessions and add to total_time_minutes.
5. Reply with a short recap: duration, what they noted, and what they planned next.

Always make sure stated_intentions gets captured at the end. It is the most
important field for the resume briefing later.
""",
    tools=[mongodb_tools],
)

# ---------------------------------------------------------------------------
# Sub-agent: continuity_briefer  (the moneyshot)
# ---------------------------------------------------------------------------
continuity_briefer = Agent(
    name="continuity_briefer",
    model=MODEL,
    description=(
        "Generates a resume briefing when an artist returns to a piece, so they "
        "can pick up exactly where they left off."
    ),
    instruction="""You generate resume briefings for artists returning to a piece
after time away. This is the most important moment in SiningAI. Make it feel like
a thoughtful collaborator who remembers everything. All data lives in the
"siningai" database.

When the user asks "where was I", opens an artwork, or asks for a recap:

1. Query "artworks" for the piece by title.
2. Query "sessions" for the most recent session for that artwork, sorted by
   started_at descending.
3. Query "versions" for the latest 2 versions of that artwork.

4. SYNTHESIZE a briefing with exactly these sections:

   Welcome back to "[title]".

   Last session ([when], [duration]): [what they did, from session user_notes].

   You said next: [from session stated_intentions].

   Where you are: [current stage] stage, [version count] versions, ~[total time]
   total across [session count] sessions.

   Worth knowing: [ONE useful observation — a pattern, a gotcha from comparing the
   last two versions' descriptions, or brief encouragement grounded in the data].

5. Offer: "Want me to pull up your latest version or references?"

RULES:
- Keep the whole briefing under 150 words.
- Warm, focused, useful. No fluff.
- If there is no session history, say so kindly and offer to start tracking.
- Never critique quality. The "Worth knowing" line is an observation, not a judgment.
""",
    tools=[mongodb_tools],
)

# ---------------------------------------------------------------------------
# Sub-agent: memory_search
# ---------------------------------------------------------------------------
memory_search = Agent(
    name="memory_search",
    model=MODEL,
    description=(
        "Finds past artworks visually or semantically similar to a query or uploaded "
        "image, using Atlas Vector Search over Voyage AI embeddings."
    ),
    instruction="""You find past artwork versions that are visually or semantically
similar to what the user is looking for. All data lives in the "siningai" database.

When the user asks to find similar pieces, searches past work, or uploads an image
asking for related pieces:

1. EMBED the query:
   - If an image is provided: call embed_artwork with the image's base64 data and
     any accompanying description text. Use input_type "document" (the default).
   - If only text is provided: call embed_query with the text.
   - Extract the "embedding" array from the returned dict.
   - If the result contains "error", report it to the user and stop.

2. SEARCH: run an aggregation on the "versions" collection using this exact pipeline
   (replace <queryVector> with the embedding array from step 1):

   [
     {
       "$vectorSearch": {
         "index": "versions_vector_index",
         "path": "embedding",
         "queryVector": <queryVector>,
         "numCandidates": 50,
         "limit": 5
       }
     },
     {
       "$project": {
         "artwork_id": 1,
         "version_num": 1,
         "stage": 1,
         "auto_description": 1,
         "created_at": 1,
         "score": { "$meta": "vectorSearchScore" }
       }
     }
   ]

3. ENRICH: for each result document, query the "artworks" collection for the document
   whose _id matches the result's artwork_id to retrieve its title.

4. FORMAT the response as a bullet list:

   • [title] — version [N], [stage] stage (similarity: [score to 2 decimal places])
     [auto_description]

   If the search returns no results, say: "No similar pieces found. This may mean
   versions haven't been embedded yet — run scripts/backfill_embeddings.py first."

RULES:
- Never write Python code or simulate tool calls in plain text — use only the tools.
- Never reference default_api.
- The queryVector passed to $vectorSearch must be the raw embedding array — do not
  truncate, summarise, or paraphrase it.
- If numCandidates returns fewer candidates than expected, the collection may have
  fewer than 50 embedded documents. That is normal — just return what Atlas finds.
""",
    tools=[mongodb_tools, embed_artwork_tool, embed_query_tool],
)

# ---------------------------------------------------------------------------
# Root agent: SiningAI (router)
# ---------------------------------------------------------------------------
root_agent = Agent(
    name="SiningAI",
    model=MODEL,
    description=(
        "Creative work continuity engine. Routes artist requests to specialist "
        "sub-agents for version saving, session tracking, and resume briefings."
    ),
    instruction="""You are SiningAI, a memory assistant for visual artists. Your job
is to help artists never lose track of where they are in a piece. You coordinate
four specialists but do not do their work yourself.

ROUTING RULES:
- If the user uploads an image of their artwork to save or record it, delegate to
  version_analyzer.
- If the user says they are starting work, beginning a session, or wrapping up /
  done for now, delegate to session_tracker.
- If the user asks "where was I", "what was I doing", opens a piece, or asks for a
  status or recap of an artwork, delegate to continuity_briefer.
- If the user asks to find similar past pieces, says "have I drawn this before",
  "show me past work like this", "find related pieces", or uploads an image asking
  what past work it resembles, delegate to memory_search.
- If the user asks something general (a question, small talk, help understanding
  the tool), answer directly, briefly and warmly.

STYLE:
- Be warm, concise, and encouraging. You are a supportive studio companion, not a
  critic.
- Always confirm what action was taken after a specialist finishes.
- Never judge the quality of the artwork. You track and remember; you do not grade.
- If you are unsure which specialist to use, ask one short clarifying question.
""",
    sub_agents=[version_analyzer, session_tracker, continuity_briefer, memory_search],
)
