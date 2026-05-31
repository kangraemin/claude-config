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
    _bouncer_wf=$(jq -r '.workflow_phase // "done"' "$_bouncer_state" 2>/dev/null)
    case "$_bouncer_wf" in
      development|verification)
        _BOUNCER_SKIP_DIRTY=true ;;
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

# ralph-x in-session 루프 active이면 skip (루프 진행 우선)
CWD=$(echo "$INPUT" | jq -r '.cwd // ""')
if [ -n "$CWD" ]; then
  for sf in "$CWD"/ralph-x-runs/*/session-state.json; do
    [ -f "$sf" ] || continue
    if [ "$(jq -r '.active // false' "$sf")" = "true" ]; then
      exit 0
    fi
  done
fi

# 20번에 1번만 실행 (세션별 독립)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // ""')
COUNTER_FILE="$HOME/.claude/hooks/.library-check-counter-$SESSION_ID"
MARKER_FILE="$HOME/.claude/hooks/.library-check-marker-$SESSION_ID"
COUNT=0
[ -f "$COUNTER_FILE" ] && COUNT=$(cat "$COUNTER_FILE")
COUNT=$((COUNT + 1))
echo "$COUNT" > "$COUNTER_FILE"
# 20의 배수일 때만 동작 (첫 호출은 skip)
[ $((COUNT % 20)) -ne 0 ] && exit 0

# transcript 없거나 접근 불가 → skip
{ [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; } && exit 0

# 지난 리뷰 이후 새 대화만 추출 (증분, user/assistant 텍스트만)
MARKER=0
[ -f "$MARKER_FILE" ] && MARKER=$(cat "$MARKER_FILE")
TOTAL=$(wc -l < "$TRANSCRIPT" | tr -d ' ')
EXCERPT_FILE="$HOME/.claude/hooks/.library-review-excerpt-$SESSION_ID-$TOTAL.txt"
# 잔여 발췌 파일 제거 — 존재 여부가 이번 실행 결과만 반영하도록
rm -f "$EXCERPT_FILE"

python3 - "$TRANSCRIPT" "$MARKER" "$TOTAL" "$EXCERPT_FILE" <<'PYEOF'
import json, sys
path, marker, total, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
parts = []
for l in lines[marker:total]:
    try: o = json.loads(l)
    except: continue
    if o.get('type') not in ('user', 'assistant'): continue
    c = o.get('message', {}).get('content', '')
    texts = []
    if isinstance(c, list):
        texts = [b['text'] for b in c if isinstance(b, dict) and b.get('type') == 'text']
    elif isinstance(c, str):
        texts = [c]
    body = '\n'.join(x for x in texts if x.strip())
    if body.strip():
        parts.append(f"## {o['type'].upper()}\n{body}")
joined = '\n\n'.join(parts)
if joined.strip():
    open(out, 'w', encoding='utf-8').write(joined)
PYEOF

# 마커는 항상 현재 위치로 업데이트 (중복 리뷰 방지)
echo "$TOTAL" > "$MARKER_FILE"

# 추출 내용 없으면 block 없이 종료
[ ! -f "$EXCERPT_FILE" ] && exit 0

jq -n --arg path "$EXCERPT_FILE" '{
  "decision": "block",
  "reason": ("다음만 수행하고 다른 행동은 하지 마라:\n\nrun_in_background=true로 Agent(general-purpose) 1개를 띄운다. subagent 프롬프트:\n---\n파일 \($path) 를 Read 해라. 최근 대화 발췌(user/assistant 텍스트)다. 이걸 '"'"'이번 세션 대화'"'"'로 간주하고 session-review 기준을 적용해라:\n1. 에러/삽질로 알게 된 API/라이브러리 동작\n2. 사용자가 접근법을 교정한 것\n3. 실패한 접근법과 이유\n4. 자명하지 않은 설계 결정\n저장 가치가 있으면 ~/claude-library 규칙대로 파일 작성 + commit/push. 없으면 아무것도 하지 마라. 끝나면 \($path) 를 rm 해라.\n---\nbackground Agent를 띄운 직후 추가 설명 없이 응답을 끝내라. 체크리스트를 인라인으로 직접 수행하지 마라.")
}'
