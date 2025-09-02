"""
Dry-run orchestrator:
- Loads system + user prompt templates
- Reads a trimmed posting and your resume
- Fills {{ROLE}}, {{COMPANY}}, {{POSTING}}, {{RESUME}}
- Prints both prompts so you can inspect them before calling the API
"""

import argparse

# IMPORTANT: use absolute imports via the package name "src"
# Run as a module:  python3 -m src.tailor ...
from src.utils.prompts import load_prompts, fill_user_prompt, soft_trim
from src.utils.io import read_file


def build_cli() -> argparse.ArgumentParser:
    """Define command-line arguments."""
    p = argparse.ArgumentParser(
        description="Tailor job application prompts (dry run, no API call)."
    )
    p.add_argument("--role", required=True, help="Job role/title")
    p.add_argument("--company", required=True, help="Company name")
    p.add_argument("--posting", required=True, help="Path to trimmed posting file")
    p.add_argument("--resume", required=True, help="Path to resume file (markdown/text)")
    p.add_argument(
        "--posting-max-chars",
        type=int,
        default=4500,
        help="Soft trim limit for posting text (default: 4500 chars).",
    )
    return p


def main() -> None:
    args = build_cli().parse_args()

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

    # 4) Print both for inspection
    print("\n===== SYSTEM PROMPT =====\n")
    print(system_prompt)
    print("\n===== USER PROMPT =====\n")
    print(user_prompt)
    print("\n(ok) Dry run complete. Review above for correctness.\n")


if __name__ == "__main__":
    main()