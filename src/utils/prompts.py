# src/utils/prompts.py
"""
Prompt utilities for AI-Career-Helper.

- load_prompts: read system + user prompt templates from disk
- fill_user_prompt: replace {{ROLE}}, {{COMPANY}}, {{POSTING}}, {{RESUME}}
- soft_trim: gently limit long posting text without breaking words/lines too hard
"""

from __future__ import annotations

from typing import Tuple

from .io import read_file

# Placeholders expected to appear in the user template
PLACEHOLDERS = ("{{ROLE}}", "{{COMPANY}}", "{{POSTING}}", "{{RESUME}}")


def load_prompts(system_path: str, user_path: str) -> Tuple[str, str]:
    """
    Load system and user prompt templates from disk.
    Returns:
        (system_prompt, user_template)
    Raises:
        FileNotFoundError: if either file is missing.
        UnicodeDecodeError: if files are not UTF-8 decodable.
    """
    system_prompt = read_file(system_path).strip()
    user_template = read_file(user_path).strip()
    return system_prompt, user_template


def _validate_placeholders_present(template: str) -> None:
    """
    Ensure the template contains the placeholders we expect.
    This catches accidentally loading the wrong file.
    """
    missing = [ph for ph in PLACEHOLDERS if ph not in template]
    if missing:
        raise ValueError(
            "User prompt template is missing required placeholder(s): "
            + ", ".join(missing)
        )


def fill_user_prompt(
    template: str,
    role: str,
    company: str,
    posting: str,
    resume: str,
) -> str:
    """
    Replace placeholders in the user prompt with actual values.
    Raises:
        ValueError: if placeholders are missing or remain unreplaced.
    """
    _validate_placeholders_present(template)

    filled = (
        template
        .replace("{{ROLE}}", role)
        .replace("{{COMPANY}}", company)
        .replace("{{POSTING}}", posting.strip())
        .replace("{{RESUME}}", resume.strip())
    )

    # Final guard: no placeholders should remain
    remaining = [ph for ph in PLACEHOLDERS if ph in filled]
    if remaining:
        raise ValueError(
            "Unreplaced placeholder(s) remain in user prompt: " + ", ".join(remaining)
        )
    return filled


def soft_trim(text: str, max_chars: int = 5000) -> str:
    """
    Soft-trim overly long text to a safe character budget.
    Tries to cut at the last newline before the limit for cleaner edges.

    Args:
        text: input text (e.g., a long posting)
        max_chars: max characters to retain (default 5000)
    """
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text

    # Prefer cutting at a newline to avoid mid-sentence truncation
    cut = text.rfind("\n", 0, max_chars)
    if cut == -1:
        cut = max_chars
    return text[:cut].rstrip() + "\n...[trimmed]..."