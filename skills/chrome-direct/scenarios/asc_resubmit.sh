#!/bin/bash
# ASC 반려(해결되지 않은 문제) 제출을 다시 심사에 넣는다. LLM 호출 없음 (CLAUDE_P_MAX=0)
# 사용: asc_resubmit.sh <app_id> <submission_id>
# 순서(2026-11-10 스레드언팔 5.6 재제출로 검증):
#   새 빌드를 버전에 붙인 뒤에는 API PATCH reviewSubmissions submitted=true 가
#   "Version is not ready to be submitted yet" 409로 계속 막힌다.
#   버전 페이지(distribution/ios/version/inflight)의 '심사 업데이트'를 누르면 항목이 '심사 준비됨'이 되고,
#   그 뒤 제출 페이지의 '앱 심사에 다시 제출'이 켜진다.
# 전제: Chrome Profile 1이 ASC에 로그인, tmux -L gh 서버.
set -e
APP=$1; SUB=$2
CC=$HOME/.claude/skills/chrome-direct/chromectl.py
T=$(mktemp -d)
C() { n=c$RANDOM; printf '%q ' python3 $CC "$@" > $T/$n.cmd
  tmux -L gh new-session -d -s $n "bash $T/$n.cmd > $T/$n.out 2>&1; tmux -L gh wait-for -S $n"; tmux -L gh wait-for $n; cat $T/$n.out; }
CLICK='const MC=b=>["pointerdown","mousedown","pointerup","mouseup","click"].forEach(n=>b.dispatchEvent(new MouseEvent(n,{bubbles:true,button:0})));'
A=$(C newtab "https://appstoreconnect.apple.com/apps/$APP/distribution/ios/version/inflight" --profile "Profile 1" | tail -1); M=id:${A#id:}
sleep 15
case "$(C js 'location.href' --match $M)" in *login*) echo "RESULT: BLOCKED ASC 로그인 필요(패스키)"; exit 2;; esac
C js "(()=>{$CLICK const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='심사 업데이트');if(!b)return 'nob';MC(b);return 1})()" --match $M
sleep 8
C js "location.href='https://appstoreconnect.apple.com/apps/$APP/distribution/reviewsubmissions/details/$SUB';1" --match $M >/dev/null; sleep 14
R=$(C js "(()=>{$CLICK const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='앱 심사에 다시 제출');if(!b)return 'nob';if(b.disabled)return 'off';MC(b);return 'ok'})()" --match $M | tail -1)
sleep 8
S=$(C js "document.body.innerText.includes('심사 대기 중')" --match $M | tail -1)
C close --match $M >/dev/null 2>&1 || true
[ "$S" = "true" ] && echo "RESULT: SUBMITTED 심사 대기 중" || { echo "RESULT: FAILED button=$R"; exit 1; }
