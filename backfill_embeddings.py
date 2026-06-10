#!/usr/bin/env python3
"""
backfill_embeddings.py — one-off script that adds Voyage AI embeddings to any
version documents in siningai.versions that were saved before embedding was added.

Usage (run from the repo root):
    python scripts/backfill_embeddings.py

Required env vars (loaded from siningai_agent/.env):
    VOYAGE_API_KEY  — Atlas AI Models key
    MONGODB_URI     — Atlas connection string (add to .env, see .env.example)

Safe to re-run: documents that already have an "embedding" field are skipped.

Exit codes:
    0 — all documents embedded successfully (or nothing to do)
    1 — fatal startup error (missing env var, connection failed)
    2 — completed with one or more per-document failures
"""

import sys
import os
from pathlib import Path

# Load .env before importing anything that reads env vars
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "siningai_agent" / ".env")

# Add repo root to path so the relative import in voyage_client works standalone
sys.path.insert(0, str(Path(__file__).parent.parent))

from siningai_agent.voyage_client import embed_text  # noqa: E402 (after sys.path patch)

try:
    import pymongo
except ImportError:
    print("ERROR: pymongo is not installed. Run: pip install pymongo>=4.6.0", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    mongo_uri = os.environ.get("MONGODB_URI", "")
    if not mongo_uri:
        print(
            "ERROR: MONGODB_URI is not set.\n"
            "Add it to siningai_agent/.env — see siningai_agent/.env.example.",
            file=sys.stderr,
        )
        return 1

    try:
        client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5_000)
        client.admin.command("ping")
    except Exception as exc:
        print(f"ERROR: Could not connect to MongoDB: {exc}", file=sys.stderr)
        return 1

    versions = client["siningai"]["versions"]

    to_embed = list(
        versions.find(
            {"embedding": {"$exists": False}},
            {"_id": 1, "auto_description": 1, "stage": 1},
        )
    )

    total = len(to_embed)
    if total == 0:
        print("Nothing to do — all version documents already have embeddings.")
        return 0

    print(f"Found {total} version(s) without embeddings. Starting backfill...")
    print()

    failed = 0
    for i, doc in enumerate(to_embed, 1):
        description = (doc.get("auto_description") or "").strip()
        if not description:
            description = f"{doc.get('stage', 'unknown')} stage artwork"

        try:
            embedding = embed_text(description, input_type="document")
            versions.update_one(
                {"_id": doc["_id"]},
                {"$set": {"embedding": embedding}},
            )
            print(f"[{i}/{total}] OK    {doc['_id']}")
        except Exception as exc:
            print(f"[{i}/{total}] FAIL  {doc['_id']}: {exc}", file=sys.stderr)
            failed += 1

    print()
    print("=" * 40)
    print(f"Embedded: {total - failed}/{total}")
    if failed:
        print(f"Failed  : {failed}  (re-run to retry — already-embedded docs are skipped)")
        return 2
    print("All done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
