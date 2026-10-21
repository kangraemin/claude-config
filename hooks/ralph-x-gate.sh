#!/bin/bash

# Stop hook gate: in-session ralph 루프가 미완이면 종료 차단

command -v jq &>/dev/null || exit 0

INPUT=$(cat)

STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
[ "$STOP_HOOK_ACTIVE" = "true" ] && exit 0

CWD=$(echo "$INPUT" | jq -r '.cwd')
[ -z "$CWD" ] && exit 0

CURRENT_SESSION=$(echo "$INPUT" | jq -r '.session_id // ""')

for state_file in "$CWD"/ralph-x-runs/*/session-state.json; do
  [ -f "$state_file" ] || continue

  ACTIVE=$(jq -r '.active // false' "$state_file")
  [ "$ACTIVE" != "true" ] && continue

  STORED_SESSION=$(jq -r '.session_id // ""' "$state_file")
  # ralph-x 가 session_id 에 None·"in-session-xxx" 같은 임의 값을 써서 22개 중 14개가 영영 매칭되지 않았다(2026-10-22 감사: 차단 0회).
  # UUID 가 아니고 최근 2시간 안에 갱신된 state 면 이 세션 것으로 가져와 실제 id 를 적어 둔다.
  UUID_RE='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  if ! [[ "$STORED_SESSION" =~ $UUID_RE ]] && [[ "$CURRENT_SESSION" =~ $UUID_RE ]]; then
    AGE=$(( $(date +%s) - $(stat -f %m "$state_file") ))
    [ "$AGE" -gt 7200 ] && continue
    TMP=$(mktemp)
    jq --arg s "$CURRENT_SESSION" '.session_id = $s' "$state_file" > "$TMP" && mv "$TMP" "$state_file"
    STORED_SESSION="$CURRENT_SESSION"
  fi
  [ "$STORED_SESSION" != "$CURRENT_SESSION" ] && continue

  MAX_ITER=$(jq -r '.max_iterations // 0' "$state_file")
  CURRENT_ITER=$(jq -r '.current_iteration // 0' "$state_file")
  CHECKLIST_FILE="$CWD/$(jq -r '.checklist_file' "$state_file")"
  RUN_ID=$(jq -r '.run_id' "$state_file")

  if [ "$MAX_ITER" -gt 0 ] && [ "$CURRENT_ITER" -ge "$MAX_ITER" ]; then
    TMP=$(mktemp)
    jq '.active = false' "$state_file" > "$TMP" && mv "$TMP" "$state_file"
    continue
  fi

  if [ ! -f "$CHECKLIST_FILE" ] || ! grep -q '^\- \[ \]' "$CHECKLIST_FILE" 2>/dev/null; then
    TMP=$(mktemp)
    jq '.active = false' "$state_file" > "$TMP" && mv "$TMP" "$state_file"
    continue
  fi

  jq -n \
    --arg iter "$CURRENT_ITER" \
    --arg max "$MAX_ITER" \
    --arg rid "$RUN_ID" \
    '{
      "decision": "block",
      "reason": ("Ralph 루프[\($rid)] 미완료 — 반복 \($iter)/\($max), 체크리스트 미완 항목 있음.\n루프를 계속 진행하세요.")
    }'
  exit 0
done

exit 0
