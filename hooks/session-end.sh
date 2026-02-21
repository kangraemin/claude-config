#!/bin/bash
# SessionEnd: 수집 파일 정리 (워크로그는 auto-commit.sh에서 생성)

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
COLLECT_FILE="$HOME/.claude/worklogs/.collecting/$SESSION_ID.jsonl"

# auto-commit에서 이미 정리했으면 스킵
[ -f "$COLLECT_FILE" ] && rm -f "$COLLECT_FILE"

exit 0
