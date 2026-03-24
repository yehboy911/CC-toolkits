#!/usr/bin/env bash
# security-monitor.sh — PreToolUse hook
# Scans tool input for hardcoded secrets, dangerous commands, and license-sensitive patterns
# Exit 0 = allow, Exit 2 = block with message

set -euo pipefail

# Read hook input from stdin
INPUT=$(cat)

# Extract tool name and relevant fields
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")
TOOL_INPUT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('tool_input','')))" 2>/dev/null || echo "{}")

# Patterns to flag as suspicious
SECRET_PATTERNS=(
  'sk-[A-Za-z0-9]{32,}'           # OpenAI/Anthropic API keys
  'AKIA[0-9A-Z]{16}'              # AWS access key
  'ghp_[A-Za-z0-9]{36}'          # GitHub personal access token
  'xoxb-[0-9]+-[A-Za-z0-9]+'    # Slack bot token
  'password\s*=\s*["\x27][^"\x27]+["\x27]'  # Hardcoded password assignment
  'secret\s*=\s*["\x27][^"\x27]+["\x27]'    # Hardcoded secret assignment
  'api_key\s*=\s*["\x27][^"\x27]+["\x27]'   # Hardcoded API key assignment
  'token\s*=\s*["\x27][A-Za-z0-9/+]{20,}["\x27]'  # Hardcoded token value
)

# Dangerous shell command patterns (for Bash tool)
DANGEROUS_PATTERNS=(
  'rm\s+-rf\s+/'        # Recursive delete from root
  'dd\s+if=.*of=/dev/'  # Direct disk write
  ':(){:|:&};:'         # Fork bomb
  'chmod\s+-R\s+777'    # World-writable recursive
)

# License-sensitive patterns (compliance domain)
LICENSE_PATTERNS=(
  'GPL.*licensed'
  'LGPL.*licensed'
  'proprietary.*code'
  'commercial.*license'
)

FOUND_ISSUES=()

# Check for secrets in tool input
INPUT_STR=$(echo "$TOOL_INPUT" | tr -d '\n')
for pattern in "${SECRET_PATTERNS[@]}"; do
  if echo "$INPUT_STR" | grep -qiE "$pattern" 2>/dev/null; then
    FOUND_ISSUES+=("Possible hardcoded secret matching: $pattern")
  fi
done

# Check for dangerous commands if this is a Bash tool call
if [[ "$TOOL_NAME" == "Bash" ]]; then
  COMMAND=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")
  for pattern in "${DANGEROUS_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern" 2>/dev/null; then
      FOUND_ISSUES+=("Dangerous command pattern detected: $pattern")
    fi
  done
fi

# Report findings
if [[ ${#FOUND_ISSUES[@]} -gt 0 ]]; then
  echo "⚠️  SECURITY MONITOR: Potential issues detected:" >&2
  for issue in "${FOUND_ISSUES[@]}"; do
    echo "  - $issue" >&2
  done
  echo "Review before proceeding. (This is a warning, not a block.)" >&2
fi

exit 0
