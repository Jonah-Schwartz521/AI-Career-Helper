# src/batch.py
"""
Batch runner for AI-Career-Helper.

Reads a CSV of job rows and invokes `run.sh` for each row:
  role,company,posting,resume

Example:
    python3 -m src.batch data/jobs_sample.csv

CSV requirements:
- Header must include: role, company, posting, resume
- Paths can be relative; they are validated before execution.

Exit codes:
- 0 on success
- Non-zero if CSV is missing/invalid or if any job fails (unless --continue-on-error)
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable, List


REQUIRED_COLS = {"role", "company", "posting", "resume"}


@dataclass
class Job:
    role: str
    company: str
    posting: str
    resume: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python3 -m src.batch",
        description="Run AI-Career-Helper for multiple jobs listed in a CSV.",
    )
    p.add_argument(
        "csv_path",
        help="Path to CSV with columns: role,company,posting,resume",
    )
    p.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing remaining rows if one job fails.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would run without executing run.sh.",
    )
    return p.parse_args()


def load_jobs(csv_path: str) -> List[Job]:
    if not os.path.exists(csv_path):
        sys.exit(f"[ERROR] CSV not found: {csv_path}")

    jobs: List[Job] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not REQUIRED_COLS.issubset(reader.fieldnames):
            sys.exit(
                "[ERROR] CSV must have header with columns: "
                + ", ".join(sorted(REQUIRED_COLS))
            )

        for i, row in enumerate(reader, start=2):  # start=2 (header is line 1)
            role = (row.get("role") or "").strip()
            company = (row.get("company") or "").strip()
            posting = (row.get("posting") or "").strip()
            resume = (row.get("resume") or "").strip()

            if not (role and company and posting and resume):
                print(f"[SKIP] Line {i}: Missing required fields -> {row}")
                continue

            jobs.append(
                Job(
                    role=role,
                    company=company,
                    posting=posting,
                    resume=resume,
                )
            )

    if not jobs:
        print("[WARN] No valid rows found in CSV.")
    return jobs


def _pretty_path(p: str) -> str:
    """Return a normalized absolute path (for logging only)."""
    return os.path.abspath(os.path.expanduser(p))


def validate_paths(jobs: Iterable[Job]) -> None:
    """Validate that posting/resume files exist to avoid late failures."""
    ok = True
    for j in jobs:
        if not os.path.exists(j.posting):
            print(f"[ERROR] Posting file not found: {j.posting} ({_pretty_path(j.posting)})")
            ok = False
        if not os.path.exists(j.resume):
            print(f"[ERROR] Resume file not found: {j.resume} ({_pretty_path(j.resume)})")
            ok = False
    if not ok:
        sys.exit(1)


def run_job(job: Job, dry_run: bool = False) -> int:
    cmd = ["bash", "./run.sh", job.role, job.company, job.posting, job.resume]
    print(f"\n=== Running: {job.role} @ {job.company} ===")
    print(f"[CMD] {' '.join(cmd)}")
    if dry_run:
        print("[DRY-RUN] Skipping execution.")
        return 0

    try:
        subprocess.run(cmd, check=True)
        print("[OK] Completed.")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] Job failed with exit code {e.returncode}.")
        return e.returncode


def main() -> None:
    args = parse_args()
    jobs = load_jobs(args.csv_path)
    if not jobs:
        sys.exit(0)

    # Optional preflight path validation
    validate_paths(jobs)

    failures = 0
    for job in jobs:
        rc = run_job(job, dry_run=args.dry_run)
        if rc != 0:
            failures += 1
            if not args.continue_on_error:
                sys.exit(rc)

    if failures:
        print(f"\n[SUMMARY] Completed with {failures} failure(s).")
        sys.exit(1)
    else:
        print("\n[SUMMARY] All jobs completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()