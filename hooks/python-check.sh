#!/usr/bin/env bash
# python-check.sh — PostToolUse hook (Edit|Write matcher)
# Validates Python syntax and runs ruff linting after .py file edits
# Exit 0 = allow (with warnings), Exit 2 = block with message

set -euo pipefail

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
ti = d.get('tool_input', {})
print(ti.get('file_path', ''))
" 2>/dev/null || echo "")

# Only check Python files
if [[ -z "$FILE_PATH" || ! -f "$FILE_PATH" ]]; then
  exit 0
fi

if [[ "$FILE_PATH" != *.py ]]; then
  exit 0
fi

ISSUES=()

# --- Syntax check via py_compile ---
SYNTAX_ERR=$(python3 -m py_compile "$FILE_PATH" 2>&1) || {
  ISSUES+=("Syntax error: $SYNTAX_ERR")
}

# --- Ruff lint (if available) ---
if command -v ruff &>/dev/null; then
  RUFF_OUT=$(ruff check --quiet --output-format=concise "$FILE_PATH" 2>&1 || true)
  if [[ -n "$RUFF_OUT" ]]; then
    while IFS= read -r line; do
      ISSUES+=("ruff: $line")
    done <<< "$RUFF_OUT"
  fi
fi

# --- Report ---
if [[ ${#ISSUES[@]} -gt 0 ]]; then
  echo "⚠️  PYTHON CHECK: Issues found in ${FILE_PATH##*/}:" >&2
  for issue in "${ISSUES[@]}"; do
    echo "  - $issue" >&2
  done
  echo "" >&2
fi

exit 0
