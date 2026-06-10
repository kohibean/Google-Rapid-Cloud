"""
voyage_client.py — thin wrapper around MongoDB's hosted Voyage AI embeddings endpoint.

Endpoint : https://ai.mongodb.com/v1/embeddings
Auth     : Bearer <VOYAGE_API_KEY>
Models   : voyage-3 (text, 1024 dims)
           voyage-multimodal-3 (text + image, 1024 dims)

Create an API key in Atlas → AI Models → Model API Keys and set VOYAGE_API_KEY in .env.
"""

import base64
import os
import re

import requests

_ENDPOINT = "https://ai.mongodb.com/v1/embeddings"


def _api_key() -> str:
    key = os.environ.get("VOYAGE_API_KEY", "")
    if not key:
        raise RuntimeError(
            "VOYAGE_API_KEY is not set. "
            "Create one in Atlas → AI Models → Model API Keys and add it to siningai_agent/.env."
        )
    return key


def _post(payload: dict) -> list[float]:
    resp = requests.post(
        _ENDPOINT,
        headers={"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def embed_text(text: str, input_type: str = "document") -> list[float]:
    """Embed a text string with voyage-3 (1024 dims).

    Args:
        text: The string to embed.
        input_type: "document" for indexing, "query" for similarity search.
    """
    return _post({
        "model": "voyage-3",
        "input": [text],
        "input_type": input_type,
    })


def embed_multimodal(
    text: str | None = None,
    image_b64: str | None = None,
    image_url: str | None = None,
    input_type: str = "document",
) -> list[float]:
    """Embed text and/or image with voyage-multimodal-3 (1024 dims).

    At least one of text, image_b64, or image_url must be provided.
    Any data URI prefix (data:image/...;base64,) is stripped from image_b64.

    Args:
        text: Optional text description to include in the embedding.
        image_b64: Optional base64-encoded image (raw or with data URI prefix).
        image_url: Optional URL to a publicly accessible image.
        input_type: "document" for indexing, "query" for similarity search.
    """
    content: list[dict] = []

    if text:
        content.append({"type": "text", "text": text})

    if image_b64:
        # Strip optional "data:image/png;base64," style prefix
        image_b64 = re.sub(r"^data:[^;]+;base64,", "", image_b64)
        content.append({"type": "image_base64", "image_base64": image_b64})

    if image_url:
        content.append({"type": "image_url", "image_url": image_url})

    if not content:
        raise ValueError("At least one of text, image_b64, or image_url must be provided.")

    return _post({
        "model": "voyage-multimodal-3",
        "inputs": [{"content": content}],
        "input_type": input_type,
    })


def embed_file(path: str, text: str | None = None) -> list[float]:
    """Read an image file from disk and embed it with voyage-multimodal-3.

    Args:
        path: Absolute or relative path to the image file.
        text: Optional text description to include alongside the image.
    """
    with open(path, "rb") as fh:
        image_b64 = base64.b64encode(fh.read()).decode("utf-8")
    return embed_multimodal(text=text, image_b64=image_b64)