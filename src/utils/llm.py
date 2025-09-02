"""
Minimal OpenAI wrapper:
- Reads OPENAI_API_KEY from env (or .env via python-dotenv)
- Calls the model with (system, user) messages
- Returns text + usage + model for logging
"""
import os
from typing import Dict, Any

from dotenv import load_dotenv
from openai import OpenAI

# Load .env (so local runs work without exporting the key)
load_dotenv()

def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Add it to your .env or export it in your shell."
        )
    return OpenAI(api_key=api_key)

DEFAULT_MODEL = "gpt-4o-mini"  # fast/cheap; swap to your preferred model

def run_llm(system_prompt: str, user_prompt: str, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    Send (system, user) messages to the model.
    Returns dict: { 'text': str, 'usage': {...}, 'model': model_name }
    """
    client = get_client()

    resp = client.chat.completions.create(
        model=model,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    text = resp.choices[0].message.content or ""
    usage = {
        "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
        "completion_tokens": getattr(resp.usage, "completion_tokens", None),
        "total_tokens": getattr(resp.usage, "total_tokens", None),
    }
    return {"text": text, "usage": usage, "model": model}