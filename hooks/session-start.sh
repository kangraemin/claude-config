#!/bin/bash
# 세션 시작 기록

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
CWD=$(echo "$INPUT" | jq -r '.cwd')
MODEL=$(echo "$INPUT" | jq -r '.model // "unknown"')
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DATE=$(date +"%Y-%m-%d")

LOG_DIR="$HOME/.claude/worklogs"
LOG_FILE="$LOG_DIR/$DATE.jsonl"
PROJECT=$(basename "$CWD")

echo "{\"ts\":\"$TIMESTAMP\",\"sid\":\"$SESSION_ID\",\"project\":\"$PROJECT\",\"event\":\"session_start\",\"model\":\"$MODEL\"}" >> "$LOG_FILE"

exit 0
