#!/usr/bin/env bash
# quality-gate.sh — PostToolUse hook (Edit|Write matcher)
# Checks code quality heuristics after file edits: file size, function length
# Exit 0 = allow (with warnings), Exit 2 = block with message

set -euo pipefail

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
ti = d.get('tool_input', {})
# Edit tool uses 'file_path'; Write tool uses 'file_path'
print(ti.get('file_path', ''))
" 2>/dev/null || echo "")

# Only check if we have a file path and the file exists
if [[ -z "$FILE_PATH" || ! -f "$FILE_PATH" ]]; then
  exit 0
fi

WARNINGS=()

# --- File size check ---
LINE_COUNT=$(wc -l < "$FILE_PATH" 2>/dev/null || echo 0)
if (( LINE_COUNT > 800 )); then
  WARNINGS+=("File is ${LINE_COUNT} lines (max recommended: 800). Consider splitting into smaller modules.")
elif (( LINE_COUNT > 400 )); then
  WARNINGS+=("File is ${LINE_COUNT} lines (ideal range: 200-400). May benefit from modularization.")
fi

# --- Python-specific checks ---
if [[ "$FILE_PATH" == *.py ]]; then
  # Count functions/methods — heuristic: lines starting with 'def '
  FUNC_COUNT=$(grep -c '^\s*def ' "$FILE_PATH" 2>/dev/null || echo 0)

  # Check for functions longer than 50 lines (heuristic)
  LONG_FUNCS=$(python3 - "$FILE_PATH" 2>/dev/null <<'PYEOF'
import sys, ast

try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        source = f.read()
    tree = ast.parse(source)
    long_funcs = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = node.end_lineno if hasattr(node, 'end_lineno') else start
            length = end - start + 1
            if length > 50:
                long_funcs.append(f"{node.name}() at line {start} ({length} lines)")
    for f in long_funcs:
        print(f)
except Exception:
    pass
PYEOF
  )

  if [[ -n "$LONG_FUNCS" ]]; then
    while IFS= read -r func; do
      WARNINGS+=("Function too long (>50 lines): $func")
    done <<< "$LONG_FUNCS"
  fi

  # Check for deep nesting (>4 levels) — heuristic via indentation
  DEEP_NEST=$(python3 - "$FILE_PATH" 2>/dev/null <<'PYEOF'
import sys

try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = len(line) - len(stripped)
        # 4 spaces per level → >4 levels = >16 spaces
        if indent > 16:
            print(f"Line {i}: indent depth {indent // 4} levels")
            if i > 5:  # limit output
                print("(and more...)")
                break
except Exception:
    pass
PYEOF
  )

  if [[ -n "$DEEP_NEST" ]]; then
    WARNINGS+=("Deep nesting detected (>4 levels) — consider extracting logic:")
    while IFS= read -r nest; do
      WARNINGS+=("  $nest")
    done <<< "$DEEP_NEST"
  fi

  # Check for hardcoded absolute paths
  if grep -qE "(['\"])(/home/|/Users/|/root/|C:\\\\)" "$FILE_PATH" 2>/dev/null; then
    WARNINGS+=("Possible hardcoded absolute path detected. Use pathlib or environment variables instead.")
  fi
fi

# --- Report ---
if [[ ${#WARNINGS[@]} -gt 0 ]]; then
  echo "⚠️  QUALITY GATE: Issues found in ${FILE_PATH##*/}:" >&2
  for w in "${WARNINGS[@]}"; do
    echo "  - $w" >&2
  done
  echo "" >&2
fi

exit 0
