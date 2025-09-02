# src/utils/postprocess.py
"""
Post-process the raw LLM output into three artifacts:
- bullets.md
- cover_letter.md
- skills_gaps.md

Features
- Robust section splitting using tolerant regexes
- Light quality gates (caps, minimums) without rewriting content style
- Deterministic, timestamped output folder slug
- Run metadata with input hashes for reproducibility
- Pointer file at outputs/run_metadata.json indicating last run directory
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Tuple

from src.utils.io import ensure_dir, sha256_text


# ====== Section parsing ======

# Tolerant matches:
# - Case-insensitive headings
# - Optional spaces
# - Stops at the next "## ..." heading or end of text
SECTION_PATTERNS: Dict[str, re.Pattern[str]] = {
    "bullets": re.compile(r"(?smi)^\s*##\s*Tailored\s+Bullets\s*(.*?)(?=^\s*##\s+|$\Z)"),
    "letter":  re.compile(r"(?smi)^\s*##\s*Cover\s+Letter\s*(.*?)(?=^\s*##\s+|$\Z)"),
    "gaps":    re.compile(
        r"(?smi)^\s*##\s*Skills\s+Gaps(?:\s*&\s*Next\s*Steps)?\s*(.*?)(?=^\s*##\s+|$\Z)"
    ),
}


def split_sections(model_output: str) -> Tuple[str, str, str]:
    """
    Extract the three sections from the LLM output.
    Returns (bullets_md, cover_md, gaps_md). Empty strings if not found.
    """
    def grab(key: str) -> str:
        m = SECTION_PATTERNS[key].search(model_output or "")
        return (m.group(1).strip() if m else "")

    return grab("bullets"), grab("letter"), grab("gaps")


# ====== Quality gates (lightweight) ======

def enforce_bullets_rules(bullets_md: str) -> str:
    """
    Keep only list items, cap at 6 lines and 240 chars per line.
    Ensure at least 3 bullets by inserting a small editor note if needed.
    """
    lines = [ln.strip() for ln in bullets_md.splitlines() if ln.strip().startswith("-")]
    lines = lines[:6]
    if len(lines) < 3:
        lines.append("- [Needs more bullets mapped to must-haves] (editor note)")
    lines = [ln[:240] for ln in lines]
    return "\n".join(lines)


def enforce_letter_rules(letter_md: str, target_min: int = 300, target_max: int = 350) -> str:
    """
    Trim the cover letter softly if it exceeds the target_max word count.
    (We do not pad if it's short—just leave as-is.)
    """
    words = re.findall(r"\S+", letter_md or "")
    if len(words) > target_max:
        letter_md = " ".join(words[:target_max]) + " …"
    return (letter_md or "").strip()


def enforce_gaps_rules(gaps_md: str) -> str:
    """
    Keep first 5 list items. Ensure at least 2 items by adding a small editor note.
    """
    items = [ln.strip() for ln in (gaps_md or "").splitlines() if ln.strip().startswith("-")]
    items = items[:5]
    if len(items) < 2:
        items.append("- [Add up to 2–5 skills gaps here] (editor note)")
    return "\n".join(items)


# ====== Writing artifacts ======

def _slug(text: str) -> str:
    """URL/file-system friendly slug."""
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")


def output_folder(company: str, role: str) -> str:
    """
    Create a deterministic, timestamped outputs folder:
      outputs/<Company>_<Role>_YYYY-mm-dd_HHMMSS
    """
    date = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return os.path.join("outputs", f"{_slug(company)}_{_slug(role)}_{date}")


def write_artifacts(out_dir: str, bullets: str, letter: str, gaps: str, metadata: Dict[str, Any]) -> None:
    """Write the three MD artifacts and the metadata JSON."""
    ensure_dir(out_dir)

    with open(os.path.join(out_dir, "bullets.md"), "w", encoding="utf-8") as f:
        f.write("## Tailored Bullets\n" + (bullets.strip() or "") + "\n")

    with open(os.path.join(out_dir, "cover_letter.md"), "w", encoding="utf-8") as f:
        f.write("## Cover Letter\n" + (letter.strip() or "") + "\n")

    with open(os.path.join(out_dir, "skills_gaps.md"), "w", encoding="utf-8") as f:
        f.write("## Skills Gaps & Next Steps\n" + (gaps.strip() or "") + "\n")

    with open(os.path.join(out_dir, "run_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def postprocess_and_write(
    model_output: str,
    role: str,
    company: str,
    inputs: Dict[str, str],
    usage: Dict[str, Any],
    model_name: str,
) -> str:
    """
    Split the raw LLM output, apply quality gates, write artifacts + metadata,
    and drop a pointer file at outputs/run_metadata.json for quick access.
    Returns the path of the new output directory.
    """
    # 1) Split
    bullets_md, letter_md, gaps_md = split_sections(model_output)

    # 2) Quality gates
    bullets_md = enforce_bullets_rules(bullets_md)
    letter_md = enforce_letter_rules(letter_md)
    gaps_md = enforce_gaps_rules(gaps_md)

    # 3) Destination folder
    out_dir = output_folder(company, role)

    # 4) Metadata (hash inputs for reproducibility/debugging)
    metadata = {
        "role": role,
        "company": company,
        "model": model_name,
        "usage": usage,
        "inputs": {
            "system_hash": sha256_text(inputs.get("system", "")),
            "user_hash": sha256_text(inputs.get("user", "")),
            "resume_hash": sha256_text(inputs.get("resume", "")),
            "posting_hash": sha256_text(inputs.get("posting", "")),
        },
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    # 5) Write artifacts
    write_artifacts(out_dir, bullets_md, letter_md, gaps_md, metadata)

    # 6) Pointer file for "last run" directory (useful for tooling/VS Code tasks)
    ensure_dir("outputs")
    with open("outputs/run_metadata.json", "w", encoding="utf-8") as pf:
        json.dump({"outputs_dir": out_dir}, pf, indent=2)

    return out_dir