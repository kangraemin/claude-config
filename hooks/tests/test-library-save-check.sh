#!/bin/bash
# e2e: library-save-check.sh 증분+백그라운드 위임 동작 검증
HOOK="$HOME/.claude/hooks/library-save-check.sh"
SID="test-$$"
CF="$HOME/.claude/hooks/.library-check-counter-$SID"
MF="$HOME/.claude/hooks/.library-check-marker-$SID"
TJ=$(mktemp /tmp/test-transcript-XXXX.jsonl)
cleanup(){ rm -f "$CF" "$MF" "$TJ" "$HOME/.claude/hooks/.library-review-excerpt-$SID-"*.txt; }
trap cleanup EXIT
fail(){ echo "❌ $1"; exit 1; }

# transcript: user/assistant 텍스트 2줄 + tool 노이즈 1줄
printf '%s\n' \
  '{"type":"user","message":{"content":"이거 에러나는데 왜 그래"}}' \
  '{"type":"assistant","message":{"content":[{"type":"text","text":"transcript_path는 현재 세션만 가리킨다"}]}}' \
  '{"type":"user","message":{"content":[{"type":"tool_result","content":"노이즈 출력"}]}}' \
  > "$TJ"
IN=$(jq -n --arg sid "$SID" --arg tj "$TJ" '{session_id:$sid,transcript_path:$tj,stop_hook_active:false,cwd:"/tmp/nonexistent-xyz"}')

# TC1: 20의 배수 아님 → 무출력 exit 0
echo 5 > "$CF"
OUT=$(echo "$IN" | bash "$HOOK")
[ -z "$OUT" ] && [ "$(cat "$CF")" = "6" ] && echo "✅ TC1 non-multiple skip" || fail "TC1"

# TC2: 20번째 + 내용 있음 → block + excerpt 파일 + 마커 갱신
echo 19 > "$CF"; rm -f "$MF"
OUT=$(echo "$IN" | bash "$HOOK")
DEC=$(echo "$OUT" | jq -r '.decision')
EXP=$(echo "$OUT" | jq -r '.reason' | grep -o '/[^ ]*library-review-excerpt[^ ]*\.txt' | head -1)
[ "$DEC" = "block" ] || fail "TC2 decision=$DEC"
{ [ -f "$EXP" ] && grep -q "ASSISTANT" "$EXP" && grep -q "transcript_path" "$EXP"; } || fail "TC2 excerpt missing/empty"
grep -q "노이즈" "$EXP" && fail "TC2 tool noise leaked"
TOT=$(wc -l < "$TJ" | tr -d ' ')
[ "$(cat "$MF")" = "$TOT" ] || fail "TC2 marker not updated"
echo "✅ TC2 block + text-only excerpt + marker"

# TC3: 20번째인데 마커=전체(빈 구간) → block 없음, 마커 갱신
echo 19 > "$CF"; echo "$TOT" > "$MF"
OUT=$(echo "$IN" | bash "$HOOK")
[ -z "$OUT" ] || fail "TC3 should not block (empty range)"
echo "✅ TC3 empty range skip"

# TC4: 재진입 가드 (stop_hook_active=true) → 즉시 exit 0, 카운터 불변
echo 19 > "$CF"
IN2=$(echo "$IN" | jq '.stop_hook_active=true')
OUT=$(echo "$IN2" | bash "$HOOK")
{ [ -z "$OUT" ] && [ "$(cat "$CF")" = "19" ]; } && echo "✅ TC4 reentry guard" || fail "TC4"

echo "ALL PASS"
