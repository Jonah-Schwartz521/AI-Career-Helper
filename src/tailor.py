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
from src.utils.llm import run_llm
from src.utils.postprocess import postprocess_and_write
from src.utils.prompts import load_prompts, fill_user_prompt, soft_trim
from src.utils.io import read_file, ensure_dir


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

    # 5) Call the model
    print("\n...calling model...\n")
    try:
        result = run_llm(system_prompt, user_prompt)  # {'text','usage','model'}
    except Exception as e:
        print("LLM call failed:", e)
        print("Tip: ensure billing/usage is active, or keep using the dry-run until resolved.")
        return

    model_output = result["text"]
    usage = result["usage"]
    model_name = result["model"]

    print("===== RAW MODEL OUTPUT =====\n")
    print(model_output)
    print("\nUsage:", usage, "| Model:", model_name)

    # Save the raw output for debugging
    ensure_dir("outputs")
    with open("outputs/RAW_last.md", "w", encoding="utf-8") as f:
        f.write(model_output)

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
    print(
        f"\nArtifacts written to: {out_dir}\n"
        f"  - bullets.md\n  - cover_letter.md\n  - skills_gaps.md\n  - run_metadata.json\n"
    )


if __name__ == "__main__":
    main()