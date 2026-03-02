#!/bin/bash
# SessionEnd: 수집 파일 정리

INPUT=$(cat)

# --- worklog-for-claude start ---
# jq 없으면 스킵 (Windows Git Bash 등)
command -v jq &>/dev/null || exit 0

SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
COLLECT_FILE="$HOME/.claude/worklogs/.collecting/$SESSION_ID.jsonl"

[ -f "$COLLECT_FILE" ] && rm -f "$COLLECT_FILE"
# --- worklog-for-claude end ---

exit 0
