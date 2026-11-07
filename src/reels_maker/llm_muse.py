"""LLM Muse client for the Reels Maker.

This module provides a tiny wrapper around the LLM Muse API. It expects two
environment variables to be set:

* ``LLM_MUSE_API_KEY`` – the bearer token for authentication.
* ``LLM_MUSE_ENDPOINT`` – the full URL of the generate endpoint. If omitted
  it defaults to ``https://api.llm.muse.ai/v1/generate``.

The function :func:`generate` sends a JSON body with a single ``prompt`` key
and returns the text content returned by the API.  The implementation is
minimal and intentionally does not depend on any external HTTP client.
"""

from __future__ import annotations

import json
import os
import urllib.request
from urllib.error import HTTPError

__all__ = ["generate"]

API_KEY_ENV = "LLM_MUSE_API_KEY"
ENDPOINT_ENV = "LLM_MUSE_ENDPOINT"
DEFAULT_ENDPOINT = "https://api.llm.muse.ai/v1/generate"


def generate(prompt: str, *, endpoint: str | None = None, api_key: str | None = None) -> str:
    """Send *prompt* to LLM Muse and return the generated text.

    Parameters
    ----------
    prompt:
        The text prompt to send to the LLM.
    endpoint:
        Optional explicit endpoint URL.  Falls back to the environment
        variable ``LLM_MUSE_ENDPOINT`` or :data:`DEFAULT_ENDPOINT`.
    api_key:
        Optional explicit bearer token.  Falls back to the environment
        variable ``LLM_MUSE_API_KEY``.

    Returns
    -------
    str
        The generated text.
    """
    endpoint = endpoint or os.getenv(ENDPOINT_ENV, DEFAULT_ENDPOINT)
    api_key = api_key or os.getenv(API_KEY_ENV)
    if not api_key:
        raise ValueError("LLM_MUSE_API_KEY not set in environment")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = json.dumps({"prompt": prompt}).encode("utf-8")
    request = urllib.request.Request(endpoint, data=payload, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            data = json.loads(body.decode("utf-8"))
            # API may return the text under different keys – use the most
            # common ones.
            return data.get("response") or data.get("text") or ""
    except HTTPError as exc:
        raise RuntimeError(f"LLM Muse request failed: {exc.code} {exc.reason}") from exc
    except Exception as exc:
        raise RuntimeError("Unexpected error while contacting LLM Muse") from exc
