#!/bin/bash
# Claude 응답 턴 종료 시 기록

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
CWD=$(echo "$INPUT" | jq -r '.cwd')
LAST_MSG=$(echo "$INPUT" | jq -r '.last_assistant_message // ""' | head -c 200)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DATE=$(date +"%Y-%m-%d")

LOG_DIR="$HOME/.claude/worklogs"
LOG_FILE="$LOG_DIR/$DATE.jsonl"
PROJECT=$(basename "$CWD")

echo "{\"ts\":\"$TIMESTAMP\",\"sid\":\"$SESSION_ID\",\"project\":\"$PROJECT\",\"event\":\"turn_end\",\"summary\":$(echo "$LAST_MSG" | jq -Rs .)}" >> "$LOG_FILE"

exit 0
