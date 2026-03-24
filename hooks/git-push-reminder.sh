#!/usr/bin/env bash
# git-push-reminder.sh — PreToolUse hook (Bash matcher)
# Intercepts git push commands and reminds to review compliance artifacts
# Exit 0 = allow (with warning), Exit 2 = block with message

set -euo pipefail

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

# Only act on git push commands
if echo "$COMMAND" | grep -qE '^\s*git\s+push' 2>/dev/null; then
  echo "⚠️  GIT PUSH REMINDER: You are about to push to remote." >&2
  echo "" >&2
  echo "  Before pushing, verify:" >&2
  echo "  - [ ] No hardcoded secrets or API keys in staged files" >&2
  echo "  - [ ] Compliance artifacts (SBOM, GPL/LGPL reports) are accurate" >&2
  echo "  - [ ] Test suite passes (python3 -m pytest or equivalent)" >&2
  echo "  - [ ] Commit messages follow: feat/fix/refactor/docs/test/chore format" >&2
  echo "  - [ ] No proprietary Lenovo internal data in committed files" >&2
  echo "" >&2
  echo "  Proceeding with push..." >&2
fi

exit 0
