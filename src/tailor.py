# src/tailor.py
"""
Tailor a job application to a specific posting.

Pipeline
--------
1) Load system & user prompt templates.
2) Read the trimmed posting and the resume.
3) Fill placeholders: {{ROLE}}, {{COMPANY}}, {{POSTING}}, {{RESUME}}.
4) (Optionally) print prompts for inspection.
5) Call the LLM.
6) Save raw model output for debugging and post-process into:
   - bullets.md
   - cover_letter.md
   - skills_gaps.md
   - run_metadata.json
7) Write a small pointer file: outputs/run_metadata.json (last run directory).

Usage
-----
Run as a module:

    python3 -m src.tailor \
        --role "AI/ML Intern" \
        --company "CCI" \
        --posting data/postings/2025-08-27_CCI_AI-ML-Intern.txt \
        --resume data/resume.md

Flags
-----
--posting-max-chars  Soft-trim limit for posting text (default: 4500).
--no-print           Do not print the prompts to stdout.
--raw-path           Where to save the raw model output (default: outputs/RAW_last.md).
--open               Open the output folder after generation (macOS: 'open', Linux: 'xdg-open').

Exit Codes
----------
0 on success
Non-zero on validation/LLM failure
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from typing import Tuple

# IMPORTANT: absolute imports via the package name "src"
from src.utils.llm import run_llm
from src.utils.postprocess import postprocess_and_write
from src.utils.prompts import load_prompts, fill_user_prompt, soft_trim
from src.utils.io import read_file, ensure_dir


def build_cli() -> argparse.ArgumentParser:
    """Define and parse command-line arguments."""
    p = argparse.ArgumentParser(
        prog="python3 -m src.tailor",
        description="Tailor job application prompts and post-process into artifacts.",
    )
    p.add_argument("--role", required=True, help="Job role/title (e.g., 'AI/ML Intern').")
    p.add_argument("--company", required=True, help="Company name (e.g., 'CCI').")
    p.add_argument("--posting", required=True, help="Path to trimmed posting file.")
    p.add_argument("--resume", required=True, help="Path to resume file (markdown/text).")
    p.add_argument(
        "--posting-max-chars",
        type=int,
        default=4500,
        help="Soft trim limit for posting text (default: 4500 chars).",
    )
    p.add_argument(
        "--no-print",
        action="store_true",
        help="Do not print the system/user prompts to stdout.",
    )
    p.add_argument(
        "--raw-path",
        default="outputs/RAW_last.md",
        help="Where to save the raw model output (default: outputs/RAW_last.md).",
    )
    p.add_argument(
        "--open",
        dest="open_folder",
        action="store_true",
        help="Open the generated output folder after completion.",
    )
    return p


def _require_file(path: str, label: str) -> None:
    """Fail fast if a required input file is missing."""
    if not os.path.exists(path):
        sys.exit(f"[ERROR] {label} not found: {path}")


def _print_prompts(system_prompt: str, user_prompt: str) -> None:
    print("\n===== SYSTEM PROMPT =====\n")
    print(system_prompt)
    print("\n===== USER PROMPT =====\n")
    print(user_prompt)


def _open_folder(path: str) -> None:
    """Best-effort open of the folder on macOS/Linux. No-op on Windows."""
    try:
        if platform.system() == "Darwin":
            subprocess.run(["open", path], check=False)
        elif platform.system() == "Linux":
            subprocess.run(["xdg-open", path], check=False)
        # On Windows or other systems, skip.
    except Exception:
        pass


def main() -> None:
    args = build_cli().parse_args()

    # Validate required files
    _require_file(args.posting, "Posting")
    _require_file(args.resume, "Resume")

    # 1) Load templates
    system_prompt, user_template = load_prompts(
        "prompts/system_job_tailor.md", "prompts/user_job_tailor.md"
    )

    # 2) Load inputs
    posting_text = read_file(args.posting)
    posting_text = soft_trim(posting_text, max_chars=args.posting_max_chars)
    resume_text = read_file(args.resume)

    # 3) Fill the user template placeholders
    user_prompt = fill_user_prompt(
        template=user_template,
        role=args.role,
        company=args.company,
        posting=posting_text,
        resume=resume_text,
    )

    # 4) (Optional) print both for inspection
    if not args.no_print:
        _print_prompts(system_prompt, user_prompt)

    # 5) Call the model
    print("\n...calling model...\n")
    try:
        # Expected return: {'text': str, 'usage': dict, 'model': str}
        result = run_llm(system_prompt, user_prompt)
    except Exception as e:
        print("[ERROR] LLM call failed:", e)
        print("Tip: Ensure OPENAI_API_KEY is set and billing/usage is active.")
        sys.exit(2)

    model_output = result["text"]
    usage = result.get("usage", {})
    model_name = result.get("model", "unknown")

    print("===== RAW MODEL OUTPUT =====\n")
    print(model_output)
    print("\nUsage:", usage, "| Model:", model_name)

    # Ensure outputs dir exists
    ensure_dir("outputs")

    # Save the raw output for debugging
    try:
        ensure_dir(os.path.dirname(args.raw_path) or ".")
        with open(args.raw_path, "w", encoding="utf-8") as f:
            f.write(model_output)
    except Exception as e:
        print(f"[WARN] Could not write raw output to {args.raw_path}: {e}")

    # 6) Post-process into artifacts
    out_dir = postprocess_and_write(
        model_output,
        role=args.role,
        company=args.company,
        inputs={
            "system": system_prompt,
            "user": user_prompt,
            "resume": resume_text,
            "posting": posting_text,
        },
        usage=usage,
        model_name=model_name,
    )

    # Write a small pointer for the "latest" run (handy for scripts/UX)
    try:
        pointer = {
            "outputs_dir": out_dir,
            "role": args.role,
            "company": args.company,
            "model": model_name,
            "raw_path": os.path.abspath(args.raw_path),
        }
        with open("outputs/run_metadata.json", "w", encoding="utf-8") as pf:
            json.dump(pointer, pf, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARN] Could not write outputs/run_metadata.json: {e}")

    print(
        f"\nArtifacts written to: {out_dir}\n"
        f"  - bullets.md\n  - cover_letter.md\n"
        f"  - skills_gaps.md\n  - run_metadata.json\n"
    )

    if args.open_folder:
        _open_folder(out_dir)


if __name__ == "__main__":
    main()