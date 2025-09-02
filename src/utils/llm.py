# src/utils/llm.py
"""
Lightweight OpenAI wrapper used by the Tailor pipeline.

Features
- Loads API key from environment (optionally via .env using python-dotenv)
- Optional OPENAI_BASE_URL support (Azure / proxies)
- Single entry point: run_llm(system_prompt, user_prompt, ...)
- Timeout + simple retry with exponential backoff
- Returns {text, usage, model} for downstream logging/metadata
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI

# Load .env if present so local runs don't require manual `export`
load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_TIMEOUT_S = 60
DEFAULT_RETRIES = 2  # total attempts = 1 + retries


def get_client(timeout_s: int = DEFAULT_TIMEOUT_S) -> OpenAI:
    """
    Construct an OpenAI client using env vars.

    Required:
        - OPENAI_API_KEY

    Optional:
        - OPENAI_BASE_URL  (e.g., Azure/OpenAI-compatible gateways)

    Returns:
        OpenAI client with a per-request timeout.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Add it to your shell env or a .env file."
        )

    base_url = os.getenv("OPENAI_BASE_URL")  # optional
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    # Attach default timeout for this client instance
    return client.with_options(timeout=timeout_s)


def _extract_usage(resp: Any) -> Dict[str, Optional[int]]:
    """Normalize usage object into a plain dict (handles SDK differences gracefully)."""
    usage = getattr(resp, "usage", None)
    if not usage:
        return {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def run_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    *,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: Optional[int] = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    retries: int = DEFAULT_RETRIES,
) -> Dict[str, Any]:
    """
    Send (system, user) messages to the chat completion API.

    Args:
        system_prompt: System instruction text.
        user_prompt:   User content text.
        model:         Model name (default: gpt-4o-mini).
        temperature:   Sampling temperature.
        max_tokens:    Optional cap on completion tokens.
        timeout_s:     Per-request timeout (seconds).
        retries:       Number of retry attempts on transient errors.

    Returns:
        Dict with keys:
          - 'text':   str, model message content ('' if none)
          - 'usage':  dict, token usage
          - 'model':  str, model actually used
    """
    client = get_client(timeout_s=timeout_s)

    attempt = 0
    backoff = 1.0
    last_err: Optional[BaseException] = None

    while attempt <= retries:
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            text = (resp.choices[0].message.content or "") if resp.choices else ""
            return {
                "text": text,
                "usage": _extract_usage(resp),
                "model": getattr(resp, "model", model) or model,
            }

        except Exception as e:
            last_err = e
            attempt += 1
            if attempt > retries:
                break
            time.sleep(backoff)
            backoff *= 2.0  # simple exponential backoff

    # If it reaches here, all attempts failed
    raise RuntimeError(f"OpenAI call failed after {retries + 1} attempt(s): {type(last_err).__name__}: {last_err}")