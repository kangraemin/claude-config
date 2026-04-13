#!/bin/bash
# --- ai-bouncer start ---
# ai-bouncer NORMAL 모드 팀 작업 중이면 미커밋 체크 스킵
# stdin을 먼저 읽고, 절대경로로 체크 후, 원본 스크립트에 stdin 재주입
_bouncer_stdin=$(cat)
_bouncer_cwd=$(echo "$_bouncer_stdin" | jq -r '.cwd' 2>/dev/null)
if [ -n "$_bouncer_cwd" ] && { [ -f "$_bouncer_cwd/.claude/ai-bouncer/config.json" ] || [ -f "$HOME/.claude/ai-bouncer/config.json" ]; }; then
  for _bouncer_active in "$_bouncer_cwd"/.ai-bouncer-tasks/*/*/.active "$_bouncer_cwd"/.ai-bouncer-tasks/*/.active; do
    [ -f "$_bouncer_active" ] || continue
    _bouncer_state="$(dirname "$_bouncer_active")/state.json"
    [ -f "$_bouncer_state" ] || continue
    _bouncer_mode=$(jq -r '.mode // "simple"' "$_bouncer_state" 2>/dev/null)
    [ "$_bouncer_mode" != "normal" ] && continue
    _bouncer_wf=$(jq -r '.workflow_phase // "done"' "$_bouncer_state" 2>/dev/null)
    case "$_bouncer_wf" in
      development|verification)
        exit 0 ;;
    esac
  done
fi
exec <<< "$_bouncer_stdin"
# --- ai-bouncer end ---

# Stop hook: 방금 응답에서 library 저장 대상 있는지 체크

command -v jq &>/dev/null || exit 0

INPUT=$(cat)

# 재진입 방지
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
[ "$STOP_HOOK_ACTIVE" = "true" ] && exit 0

# 20번에 1번만 실행 (세션별 독립)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
COUNTER_FILE="$HOME/.claude/hooks/.library-check-counter-$SESSION_ID"
COUNT=0
[ -f "$COUNTER_FILE" ] && COUNT=$(cat "$COUNTER_FILE")
COUNT=$((COUNT + 1))
echo "$COUNT" > "$COUNTER_FILE"
# 20의 배수일 때만 block (첫 호출은 skip)
[ $((COUNT % 20)) -ne 0 ] && exit 0

jq -n '{
  "decision": "block",
  "reason": "아래 체크리스트를 하나씩 확인해라. 하나라도 yes면 /session-review 실행. 전부 no면 아무 말 없이 넘어가.\n\n1. 에러/삽질로 알게 된 API/라이브러리 동작이 있었나? (문서에 없던 것, 다음에 또 삽질할 것)\n2. 사용자가 내 접근법을 교정했나? (\"그게 아니야\", \"그렇게 하지 마\")\n3. 시도했다가 실패한 접근법이 있었나? (왜 실패했는지 다음에 알아야 하는 것)\n4. 설계 결정을 내렸고 그 이유가 자명하지 않은가?\n5. 포맷/구조 변경으로 다른 컴포넌트가 깨진 적 있었나?\n\n주의: \"아마 없을 것 같다\"로 넘기지 말고 실제로 대화를 돌아봐라."
}'
