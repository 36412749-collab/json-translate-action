#!/usr/bin/env bash
set -euo pipefail

API_KEY="${ROUTARA_API_KEY:?api-key input is required}"
TARGET_LANG="${TARGET_LANG:?target-lang input is required}"
API_BASE="${API_BASE:-https://api.routara.ai}"
FILE_GLOB="${FILE_GLOB:-**/*.json}"
ACCEPT_LANG="${ACCEPT_LANG:-en}"
FAIL_ON_VALIDATION="${FAIL_ON_VALIDATION:-false}"
ASYNC_MODE="${ASYNC_MODE:-auto}"
MAX_FILES_PER_REQUEST="${MAX_FILES_PER_REQUEST:-5}"
POLL_SECONDS="${POLL_SECONDS:-5}"
POLL_TIMEOUT_SECONDS="${POLL_TIMEOUT_SECONDS:-1800}"

export API_KEY TARGET_LANG API_BASE ACCEPT_LANG FAIL_ON_VALIDATION
export MAX_FILES_PER_REQUEST POLL_SECONDS POLL_TIMEOUT_SECONDS

shopt -s globstar nullglob
mapfile -t FILES < <(compgen -G "$FILE_GLOB" || true)

REAL_FILES=()
for f in "${FILES[@]}"; do
  [ -f "$f" ] && REAL_FILES+=("$f")
done

if [ "${#REAL_FILES[@]}" -eq 0 ]; then
  echo "::error::No files matched glob: $FILE_GLOB"
  exit 1
fi

export FILE_LIST_JSON
FILE_LIST_JSON=$(printf '%s\0' "${REAL_FILES[@]}" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().split("\0")[:-1]))')

echo "Found ${#REAL_FILES[@]} JSON file(s) → target $TARGET_LANG"

use_async="$ASYNC_MODE"
if [ "$use_async" = "auto" ]; then
  if [ "${#REAL_FILES[@]}" -gt "$MAX_FILES_PER_REQUEST" ]; then
    use_async="true"
  else
    use_async="false"
  fi
fi

if [ "$use_async" = "true" ]; then
  echo "Mode: async batch (large job — avoids gateway timeout)"
  python3 "$GITHUB_ACTION_PATH/scripts/translate_async.py"
else
  echo "Mode: sync batch"
  python3 "$GITHUB_ACTION_PATH/scripts/translate_sync.py"
fi
