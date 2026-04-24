#!/bin/bash
# ralph-x-gate E2E 테스트
PASS=0; FAIL=0

_make_base() { mktemp -d; }
_state() {
  local base="$1" name="$2" active="$3" sid="$4" cur="$5" max="$6"
  local dir="$base/ralph-x-runs/$name"
  mkdir -p "$dir"
  cat > "$dir/session-state.json" <<EOF
{"active":${active},"session_id":"${sid}","run_id":"${name}","run_dir":"ralph-x-runs/${name}","checklist_file":"ralph-x-runs/${name}/checklist.md","current_iteration":${cur},"max_iterations":${max}}
EOF
}
_checklist() { printf "%s" "$2" > "$1/ralph-x-runs/$3/checklist.md"; }
_hook() {
  local base="$1" sid="$2"
  echo "{\"cwd\":\"$base\",\"stop_hook_active\":false,\"session_id\":\"$sid\"}" \
    | bash ~/.claude/hooks/ralph-x-gate.sh
}
_assert_block() {
  local out; out=$(_hook "$1" "$2" 2>&1)
  if echo "$out" | jq -e '.decision == "block"' &>/dev/null; then
    echo "✅ $3"; PASS=$((PASS+1))
  else
    echo "❌ $3 (got: $out)"; FAIL=$((FAIL+1))
  fi
}
_assert_pass() {
  local out; out=$(_hook "$1" "$2" 2>&1)
  if ! echo "$out" | jq -e '.decision == "block"' &>/dev/null 2>&1; then
    echo "✅ $3"; PASS=$((PASS+1))
  else
    echo "❌ $3 (got: $out)"; FAIL=$((FAIL+1))
  fi
}
_assert_field() {
  local base="$1" run="$2" expected="$3" field="$4" label="$5"
  local val; val=$(jq -r ".$field" "$base/ralph-x-runs/$run/session-state.json" 2>/dev/null)
  if [ "$val" = "$expected" ]; then
    echo "✅ $label"; PASS=$((PASS+1))
  else
    echo "❌ $label (expected '$expected', got '$val')"; FAIL=$((FAIL+1))
  fi
}

echo "=== TC-01: active 세션 없음 → 통과 ==="
B=$(mktemp -d); trap "rm -rf $B" EXIT
mkdir -p "$B/ralph-x-runs"
_assert_pass "$B" "any-sid" "TC-01 no active session → pass"
rm -rf "$B"

echo "=== TC-02: 매칭 세션, 미완 checklist → 차단 ==="
B=$(mktemp -d)
_state "$B" "run-a" true "sid-A" 2 10
_checklist "$B" "- [ ] 미완\n- [x] 완료" "run-a"
_assert_block "$B" "sid-A" "TC-02 matching session, incomplete checklist → block"
rm -rf "$B"

echo "=== TC-03: 다른 session_id (격리) → 통과 ==="
B=$(mktemp -d)
_state "$B" "run-a" true "sid-A" 2 10
_checklist "$B" "- [ ] 미완" "run-a"
_assert_pass "$B" "sid-B" "TC-03 different session → pass"
rm -rf "$B"

echo "=== TC-04: checklist 전부 완료 → 통과 + active=false ==="
B=$(mktemp -d)
_state "$B" "run-b" true "sid-A" 3 10
_checklist "$B" "- [x] 완료1\n- [x] 완료2" "run-b"
_assert_pass "$B" "sid-A" "TC-04 all checklist done → pass"
_assert_field "$B" "run-b" "false" "active" "TC-04 active=false after completion"
rm -rf "$B"

echo "=== TC-05: max_iterations 도달 → 통과 + active=false ==="
B=$(mktemp -d)
_state "$B" "run-c" true "sid-A" 10 10
_checklist "$B" "- [ ] 미완" "run-c"
_assert_pass "$B" "sid-A" "TC-05 max iterations reached → pass"
_assert_field "$B" "run-c" "false" "active" "TC-05 active=false after max iter"
rm -rf "$B"

echo "=== TC-06: stop_hook_active=true → 재진입 방지 ==="
B=$(mktemp -d)
_state "$B" "run-d" true "sid-A" 1 10
_checklist "$B" "- [ ] 미완" "run-d"
out=$(echo "{\"cwd\":\"$B\",\"stop_hook_active\":true,\"session_id\":\"sid-A\"}" | bash ~/.claude/hooks/ralph-x-gate.sh 2>&1)
if ! echo "$out" | jq -e '.decision == "block"' &>/dev/null 2>&1; then
  echo "✅ TC-06 stop_hook_active reentry → pass"; PASS=$((PASS+1))
else
  echo "❌ TC-06 (got block)"; FAIL=$((FAIL+1))
fi
rm -rf "$B"

echo "=== TC-07: active=false 세션 → 무시 ==="
B=$(mktemp -d)
_state "$B" "run-e" false "sid-A" 3 10
_checklist "$B" "- [ ] 미완" "run-e"
_assert_pass "$B" "sid-A" "TC-07 active=false session ignored → pass"
rm -rf "$B"

echo "=== TC-08: session-state.json 없는 디렉토리 → graceful ==="
B=$(mktemp -d)
mkdir -p "$B/ralph-x-runs/orphan-run"
_assert_pass "$B" "sid-A" "TC-08 missing state.json → pass"
rm -rf "$B"

echo "=== TC-09: checklist 파일 없음 → 완료 간주 + active=false ==="
B=$(mktemp -d)
_state "$B" "run-f" true "sid-A" 1 10
# checklist.md 없음
_assert_pass "$B" "sid-A" "TC-09 missing checklist → treated as done → pass"
_assert_field "$B" "run-f" "false" "active" "TC-09 active=false when checklist missing"
rm -rf "$B"

echo "=== TC-10: 복수 런 — 본인 세션만 차단, 다른 세션은 통과 ==="
B=$(mktemp -d)
# run-g: sid-X 소유, 미완
_state "$B" "run-g" true "sid-X" 1 5
_checklist "$B" "- [ ] 미완" "run-g"
# sid-X → block
_assert_block "$B" "sid-X" "TC-10a own session (sid-X) → block"
# sid-other (ralph 활성 없음) → pass
_assert_pass "$B" "sid-other" "TC-10b unrelated session → pass"
rm -rf "$B"

echo "=== TC-11: session_id 캡처 → UUID 형식 ==="
SID=$(ls -lt ~/.claude/worklogs/.collecting/*.jsonl 2>/dev/null \
  | awk 'NR==1{print $NF}' | xargs basename | sed 's/\.jsonl//')
if [[ "$SID" =~ ^[0-9a-f-]{36}$ ]]; then
  echo "✅ TC-11 session_id capture → $SID"; PASS=$((PASS+1))
else
  echo "❌ TC-11 session_id invalid: '$SID'"; FAIL=$((FAIL+1))
fi

echo ""
echo "결과: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ]
