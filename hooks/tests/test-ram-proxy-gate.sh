#!/bin/bash
# ram-proxy-gate.py 회귀 테스트: 가짜 transcript + 임시 git 레포로 세 가지 검사를 확인한다.
set -u
HOOK="$HOME/.claude/hooks/ram-proxy-gate.py"
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
PASS=0; FAIL=0

# transcript 작성: $1=파일 $2=마지막 assistant 텍스트 $3=tool_use JSON 배열
mk() {
  python3 - "$1" "$2" "$3" <<'EOF'
import json,sys
f,text,uses=sys.argv[1],sys.argv[2],json.loads(sys.argv[3])
rows=[{"type":"user","message":{"content":"해줘"}}]
for u in uses:
    rows.append({"type":"assistant","message":{"content":[{"type":"tool_use","name":u[0],"input":u[1]}]}})
    rows.append({"type":"user","message":{"content":[{"type":"tool_result","content":"ok"}]}})
rows.append({"type":"assistant","message":{"content":[{"type":"text","text":text}]}})
open(f,"w").write("\n".join(json.dumps(r,ensure_ascii=False) for r in rows))
EOF
}

# $1=이름 $2=기대(block|pass) $3=grep 키워드 $4=transcript $5=cwd $6=stop_hook_active
run() {
  out=$(printf '{"transcript_path":"%s","cwd":"%s","stop_hook_active":%s}' "$4" "$5" "${6:-false}" | python3 "$HOOK")
  if [ "$2" = "block" ]; then
    if echo "$out" | grep -q '"block"' && echo "$out" | grep -q "$3"; then PASS=$((PASS+1)); echo "ok   $1"; else FAIL=$((FAIL+1)); echo "FAIL $1: $out"; fi
  else
    if [ -z "$out" ]; then PASS=$((PASS+1)); echo "ok   $1"; else FAIL=$((FAIL+1)); echo "FAIL $1: $out"; fi
  fi
}

# --- 묻고 멈춤
mk "$T/a1" "정리했어요. 이대로 진행할까요?" '[]';                         run "ask: 진행할까요" block "묻고 멈췄다" "$T/a1" "$T"
mk "$T/a2" "시안 확인해 주시면 바로 만들게요." '[]';                       run "ask: 확인해 주시면" block "묻고 멈췄다" "$T/a2" "$T"
mk "$T/a3" "문자로 온 인증번호만 알려주세요. 바로 넣을게요?" '[]';        run "ask: 인증번호 예외" pass "" "$T/a3" "$T"
mk "$T/a4" "로그인됐어요. 뭘 할까요?" '[]';                               run "ask: 할 일 없음 예외" pass "" "$T/a4" "$T"
mk "$T/a5" "다 끝났어요. 결과는 위와 같아요." '[]';                        run "ask: 질문 아님" pass "" "$T/a5" "$T"
run "stop_hook_active면 통과" pass "" "$T/a1" "$T" true

# --- 검증 없는 완료
mk "$T/v1" "버그 고쳤어요." '[["Edit",{"file_path":"/x/app.py"}]]';                                    run "verify: 실행 없음" block "실행해 보지" "$T/v1" "$T"
mk "$T/v2" "버그 고쳤어요." '[["Edit",{"file_path":"/x/app.py"}],["Bash",{"command":"pytest -q"}]]';   run "verify: pytest 후" pass "" "$T/v2" "$T"
mk "$T/v3" "문서 수정했어요." '[["Edit",{"file_path":"/x/README.md"}]]';                              run "verify: 문서만" pass "" "$T/v3" "$T"
mk "$T/v4" "버그 고쳤어요." '[["Bash",{"command":"pytest"}],["Edit",{"file_path":"/x/app.ts"}]]';      run "verify: 검증이 수정보다 먼저" block "실행해 보지" "$T/v4" "$T"

# --- push 누락
git init -q --bare "$T/remote.git"
git clone -q "$T/remote.git" "$T/repo" 2>/dev/null
( cd "$T/repo" && git commit -q --allow-empty -m init && git push -q -u origin HEAD 2>/dev/null && git commit -q --allow-empty -m second )
mk "$T/p1" "커밋했어요." '[["Bash",{"command":"git commit -m x"}]]';  run "push: ahead 1" block "push 안 됐다" "$T/p1" "$T/repo"
( cd "$T/repo" && git push -q 2>/dev/null )
run "push: push 후 통과" pass "" "$T/p1" "$T/repo"
mk "$T/p2" "확인했어요." '[["Bash",{"command":"git status"}]]';
( cd "$T/repo" && git commit -q --allow-empty -m third )
run "push: 이번 턴 커밋 없음" pass "" "$T/p2" "$T/repo"
( cd "$T/repo" && git checkout -q -b feat && git commit -q --allow-empty -m f )
run "push: upstream 없음" block "push -u origin feat" "$T/p1" "$T/repo"

RAM_PROXY_GATE=off bash -c "printf '{\"transcript_path\":\"$T/a1\",\"cwd\":\"$T\"}' | python3 $HOOK" | grep -q block && { FAIL=$((FAIL+1)); echo "FAIL off 스위치"; } || { PASS=$((PASS+1)); echo "ok   off 스위치"; }

echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
