#!/usr/bin/env bash
# session-summary.sh — Stop lifecycle hook
# Appends a timestamped session entry to the audit log at ~/Downloads/claude-sessions.log
# Exit 0 = always allow

LOG_FILE="$HOME/Downloads/claude-sessions.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S %Z')
CWD=$(pwd 2>/dev/null || echo "unknown")

# Ensure log file exists
touch "$LOG_FILE" 2>/dev/null || true

{
  echo "────────────────────────────────────────────────────────────────"
  echo "SESSION END: $TIMESTAMP"
  echo "  Working dir : $CWD"
  echo "  Log         : $LOG_FILE"
  echo "────────────────────────────────────────────────────────────────"
} >> "$LOG_FILE" 2>/dev/null || true

exit 0
