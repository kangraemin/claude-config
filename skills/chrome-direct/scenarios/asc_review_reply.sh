#!/bin/bash
# ASC '앱 심사에 회신' 글 + 첨부 파일 보내기 (2026-11-03 '이게 되네' 검증: 영상 5MB 첨부 성공)
# 사용: asc_review_reply.sh <app_id> <submission_id> <message.txt> [첨부파일]
# 전제: Chrome Profile 1이 ASC에 로그인(안 됐으면 이메일칸 클릭 → 드롭다운 '패스키 · Apple Passwords' → Mac 시트 '계속'),
#       tmux -L gh 서버(자동화 권한)가 떠 있음.
# 방법: 파일 창을 쓰지 않는다(다른 세션이 화면을 가로채면 경로가 엉뚱한 창에 들어감).
#       파일을 base64 조각(400KB)으로 페이지에 넣고 DataTransfer로 input[type=file]에 꽂는다.
#       주의: 새로 연 회신 창에서만 붙는다. 한 번 실패한 창에서는 files가 0으로 돌아오니 새로고침 뒤 다시 연다.
#       첨부 '처리 중...'이 끝나 파일 이름이 보인 뒤 '회신'을 누른다.
#       회신 뒤 '앱 심사에 다시 제출'은 Information Needed면 비활성(API도 STATE_ERROR) — Apple 답을 기다린다.
set -e
APP=$1; SUB=$2; MSG=$3; FILE=$4
CC=$HOME/.claude/skills/chrome-direct/chromectl.py
T=$(mktemp -d)
C() { n=c$RANDOM; printf '%q ' python3 $CC "$@" > $T/$n.cmd
  tmux -L gh new-session -d -s $n "bash $T/$n.cmd > $T/$n.out 2>&1; tmux -L gh wait-for -S $n"; tmux -L gh wait-for $n; cat $T/$n.out; }
A=$(C newtab "https://appstoreconnect.apple.com/apps/$APP/distribution/reviewsubmissions/details/$SUB" --profile "Profile 1" | tail -1); M=id:${A#id:}
sleep 14
case "$(C js 'location.href' --match $M)" in *login*) echo "RESULT: BLOCKED ASC 로그인 필요(패스키)"; exit 2;; esac
CLICK='const MC=b=>["pointerdown","mousedown","pointerup","mouseup","click"].forEach(n=>b.dispatchEvent(new MouseEvent(n,{bubbles:true,button:0})));'
C js "(()=>{$CLICK const b=[...document.querySelectorAll('a,button')].find(x=>['앱 심사에 회신','초안 계속 작성'].includes(x.textContent.trim()));if(!b)return 'nob';MC(b);return 1})()" --match $M; sleep 4
J=$(python3 -c "import json,sys;print(json.dumps(open(sys.argv[1]).read()))" "$MSG")
C js "(()=>{const t=document.querySelector('textarea[name=messageBody]');const s=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;s.call(t,$J);t.dispatchEvent(new Event('input',{bubbles:true}));return t.value.length})()" --match $M
if [ -n "$FILE" ]; then
  NAME=$(basename "$FILE"); MIME=$(file -b --mime-type "$FILE")
  base64 -i "$FILE" | tr -d '\n' > $T/v.b64; (cd $T && split -b 400000 v.b64 ch_)
  C js 'window.__v=[];1' --match $M >/dev/null
  for f in $T/ch_*; do printf 'window.__v.push("%s");1' "$(cat $f)" > $T/p.js; C js "$(cat $T/p.js)" --match $M >/dev/null; done
  C js "(()=>{const s=atob(window.__v.join(''));const u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);const f=new File([u],'$NAME',{type:'$MIME'});const inp=document.querySelector('input[type=file]');const dt=new DataTransfer();dt.items.add(f);inp.files=dt.files;inp.dispatchEvent(new Event('input',{bubbles:true}));inp.dispatchEvent(new Event('change',{bubbles:true}));return 1})()" --match $M
  for i in $(seq 1 30); do sleep 3; C js 'document.body.innerText' --match $M | grep -q "$NAME" && break; done
  C js 'document.body.innerText' --match $M | grep -q "$NAME" || { echo "RESULT: FAIL 첨부 안 붙음(새로고침 후 재시도)"; exit 1; }
fi
# 회신 칸은 4,000자 한도. 넘으면 '회신' 버튼이 꺼진 채라 눌러도 아무 일 없다(2026-11-10 5,963자 → 거짓 SENT).
LEN=$(python3 -c "import sys;print(len(open(sys.argv[1]).read()))" "$MSG")
[ "$LEN" -gt 4000 ] && { echo "RESULT: FAIL 글자 수 $LEN > 4000"; exit 1; }
C js "(()=>{$CLICK const b=[...document.querySelectorAll('[role=dialog] button')].filter(b=>b.textContent.trim()==='회신').pop();if(b.disabled)return 'OFF';MC(b);return 1})()" --match $M | grep -q OFF && { echo "RESULT: FAIL 회신 버튼 꺼짐"; exit 1; }
sleep 10
HEAD=$(python3 -c "import json,sys;print(json.dumps(open(sys.argv[1]).read().strip()[:40]))" "$MSG")
C js "document.body.innerText.includes($HEAD)?'POSTED':'NOTPOSTED'" --match $M | tail -1 | grep -q '^POSTED' || { echo "RESULT: FAIL 페이지에 회신이 안 보임"; exit 1; }
C js "(()=>{const s=document.body.innerText;return /오류가 발생/.test(s)?'ERR':(s.includes('메시지 첨부 파일')||!'$FILE')?'SENT':'CHECK'})()" --match $M | tail -1 | sed 's/^/RESULT: /'

# 패스키 로그인 메모 (2026-11-06):
# - BLOCKED(로그인)이면: chromectl shot --match <로그인 탭>으로 앞에 띄운 뒤
#   cliclick c:1077,675 ('패스키로 로그인', iframe이라 press --text 안 됨) → 맥 시트 '계속' c:1157,632.
#   좌표는 1400폭 캡처 x1.3714, 전체화면 캡처는 메뉴바만큼 y가 ~22px 다르다.
# - 첫 실행이 'FAIL 첨부 안 붙음'이면 한 번 더 실행(새 탭에서 SENT 나옴).
# - 확인은 반드시 새 탭(newtab → --match id:<id>)에서: 옛 탭은 회신 전 화면이 남아 있다.
