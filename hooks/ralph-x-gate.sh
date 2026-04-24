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
  if [ -z "$STORED_SESSION" ] || [ "$STORED_SESSION" != "$CURRENT_SESSION" ]; then
    continue
  fi

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
