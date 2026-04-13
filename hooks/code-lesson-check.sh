#!/bin/bash
# Post-commit hook: 커밋 10회마다 code-lesson 트리거
# Stop hook으로 등록되어 Claude 응답 후 실행됨

command -v jq &>/dev/null || exit 0
command -v git &>/dev/null || exit 0

INPUT=$(cat)

# 재진입 방지
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
[ "$STOP_HOOK_ACTIVE" = "true" ] && exit 0

# 현재 디렉토리가 git repo인지 확인
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

# 세션별 커밋 카운터
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
COUNTER_FILE="$HOME/.claude/hooks/.code-lesson-counter-$SESSION_ID"
LAST_COMMIT_FILE="$HOME/.claude/hooks/.code-lesson-last-commit-$SESSION_ID"

# 현재 커밋 SHA
CURRENT_SHA=$(git rev-parse HEAD 2>/dev/null)
[ -z "$CURRENT_SHA" ] && exit 0

# 마지막으로 체크한 커밋과 동일하면 skip (커밋이 안 일어남)
LAST_SHA=$(cat "$LAST_COMMIT_FILE" 2>/dev/null || echo "")
[ "$CURRENT_SHA" = "$LAST_SHA" ] && exit 0

# 커밋이 바뀜 → 카운터 증가
echo "$CURRENT_SHA" > "$LAST_COMMIT_FILE"

if [ ! -f "$COUNTER_FILE" ]; then
  echo "1" > "$COUNTER_FILE"
  exit 0
fi

COUNT=$(cat "$COUNTER_FILE")
COUNT=$((COUNT + 1))

if [ "$COUNT" -ge 10 ]; then
  echo "0" > "$COUNTER_FILE"
  jq -n '{
    "decision": "block",
    "reason": "커밋 10회 도달! 이번 세션에서 변경된 코드 중 유저가 배울 만한 기술 포인트가 있는지 확인해봐. 있으면 /code-lesson 실행해서 정리해줘. 없으면 그냥 넘어가."
  }'
else
  echo "$COUNT" > "$COUNTER_FILE"
  exit 0
fi
