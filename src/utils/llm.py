from __future__ import annotations

import os
import time
import socket
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI
from openai import APIConnectionError, APIStatusError, RateLimitError

# Load .env so local runs pick up OPENAI_API_KEY/OPENAI_BASE_URL without exports
load_dotenv()

# ---- Defaults (mirrors the earlier working version) ----
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_TIMEOUT_S = 60           # per-request timeout
DEFAULT_RETRIES = 2              # total attempts = 1 + retries


def get_client(timeout_s: int = DEFAULT_TIMEOUT_S) -> OpenAI:
    """Construct an OpenAI client from env vars with an attached timeout.

    Required env:
      - OPENAI_API_KEY
    Optional env:
      - OPENAI_BASE_URL (for Azure/proxy-compatible gateways)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to your .env or shell env.")

    base_url = os.getenv("OPENAI_BASE_URL")
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    # attach default timeout for this client instance
    try:
        client = client.with_options(timeout=timeout_s)
    except Exception:
        # older SDKs may not support with_options; fall back to raw client
        pass
    return client


def _extract_usage(resp: Any) -> Dict[str, Optional[int]]:
    """Normalize SDK usage object into a plain dict (handles SDK differences)."""
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
    """Send (system, user) messages to the chat completion API with retries.

    Returns a dict: {"text": str, "usage": dict, "model": str}
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

            text = (resp.choices[0].message.content or "").strip() if getattr(resp, "choices", None) else ""
            return {
                "text": text,
                "usage": _extract_usage(resp),
                "model": getattr(resp, "model", model) or model,
            }

        except (APIConnectionError, APIStatusError, RateLimitError) as e:
            # transient-ish; retry with simple exponential backoff
            last_err = e
            attempt += 1
            if attempt > retries:
                break
            time.sleep(backoff)
            backoff *= 2.0
        except Exception as e:
            # non-transient; surface immediately
            raise

    # If we got here, all attempts failed
    name = type(last_err).__name__ if last_err else "UnknownError"
    msg = str(last_err) if last_err else "no exception payload"
    raise RuntimeError(f"OpenAI call failed after {retries + 1} attempt(s): {name}: {msg}")


if __name__ == "__main__":
    print("llm module ready")