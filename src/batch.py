import csv, sys, os, subprocess

def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 -m src.batch <path/to/jobs.csv>")

    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        sys.exit(f"CSV not found: {csv_path}")

    total = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"role", "company", "posting", "resume"}
        if not required.issubset(reader.fieldnames or []):
            sys.exit(f"CSV must have columns: {', '.join(required)}")

        for row in reader:
            role = row["role"].strip()
            company = row["company"].strip()
            posting = row["posting"].strip()
            resume = row["resume"].strip()
            if not (role and company and posting and resume):
                print(f"[SKIP] Missing fields in row: {row}")
                continue

            print(f"\n=== Running: {role} @ {company} ===")
            subprocess.run(
                ["bash", "./run.sh", role, company, posting, resume],
                check=True
            )
            total += 1

    print(f"\nDone. {total} job(s) processed.")

if __name__ == "__main__":
    main()