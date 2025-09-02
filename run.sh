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