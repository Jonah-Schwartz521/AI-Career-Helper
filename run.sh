#!/usr/bin/env bash
set -euo pipefail

echo "DEBUG: run.sh started"

ROLE=${1:?Provide role}
COMPANY=${2:?Provide company}
POSTING=${3:?Provide path to trimmed posting}
RESUME=${4:?Provide resume path}

source .venv/bin/activate

echo "Running for: $ROLE @ $COMPANY"
echo "DEBUG: about to run python3 -m src.tailor ..."

python3 -m src.tailor \
  --role "$ROLE" \
  --company "$COMPANY" \
  --posting "$POSTING" \
  --resume "$RESUME"

# Capture last output dir from metadata
LAST_DIR=$(jq -r '.outputs_dir // empty' outputs/run_metadata.json 2>/dev/null || true)

# Fallback: newest folder in outputs/
if [ -z "$LAST_DIR" ]; then
  LAST_DIR=$(ls -dt outputs/*_* | head -n 1)
fi

echo "Opening: $LAST_DIR"
code "$LAST_DIR/bullets.md" "$LAST_DIR/cover_letter.md" "$LAST_DIR/skills_gaps.md" || true