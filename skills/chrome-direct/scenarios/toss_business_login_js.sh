#!/bin/bash
# 토스 비즈니스(앱인토스 콘솔) 휴대폰 로그인 — Codex 없이 AppleScript+JS로 실제 Chrome 조작.
#   toss_business_login_js.sh send          → 로그인 탭 열기·본인정보·통신사(SKT 알뜰폰)·전체 동의·문자 요청
#   toss_business_login_js.sh code 123456   → 인증번호 입력·계정 선택. 성공 시 LOGGED_IN
#   toss_business_login_js.sh resend        → 인증번호 다시 받기
# 개인정보 값은 build_application.py INFO(5=생년월일, 9=전화)에서 읽고 출력하지 않는다.
# 주의: 주민번호 칸 옆 readonly 입력은 생년월일+성별 숫자를 비춘다 — value를 찍지 말 것.
# React 컴포넌트라 .click()이 안 먹는 곳은 pointer/mouse 이벤트를 모두 쏜다.
set -u
INFO_PY=/Users/ram/programming/vibecoding/공모전/2026-10_제천AI데이터분석/submission/build_application.py
URL='https://apps-in-toss.toss.im/workspace/35273'
js() { osascript - "$1" <<'AS'
on run argv
tell application "Google Chrome"
repeat with w in windows
repeat with t in tabs of w
if URL of t contains "business.toss.im" then return execute t javascript (item 1 of argv)
end repeat
end repeat
end tell
return "NO_TAB"
end run
AS
}
FIRE="const fire=t=>['pointerdown','mousedown','pointerup','mouseup','click'].forEach(k=>t.dispatchEvent(new (k.startsWith('pointer')?PointerEvent:MouseEvent)(k,{bubbles:true})));"
txt() { js "document.body.innerText.slice(0,400)"; }
case "${1:-}" in
  send)
    if [ "$(js 1)" = "NO_TAB" ]; then
      osascript -e "tell application \"Google Chrome\" to tell window 1 to make new tab with properties {URL:\"$URL\"}" >/dev/null; sleep 6
      osascript -e 'tell application "Google Chrome" to get URL of every tab of every window' | grep -q "business.toss.im" || { echo ALREADY_LOGGED_IN; exit 0; }
    fi
    js "${FIRE}const b=[...document.querySelectorAll('button')].find(b=>b.innerText.trim()=='휴대폰번호 로그인');b&&fire(b);'ok'" >/dev/null; sleep 3
    VALS=$(python3 - "$INFO_PY" <<'PY'
import re,sys,json
src=open(sys.argv[1]).read(); info={int(k):v for k,v in re.findall(r'(\d+):\s*"([^"]*)"',src)}
b=re.sub(r'\D','',info[5]); b=b[2:] if len(b)==8 else b
print(json.dumps(['강래민',re.sub(r'\D','',info[9]),None,b,'1']))
PY
)
    js "(()=>{const set=(i,v)=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,v);i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}));};const ins=[...document.querySelectorAll('input')];$VALS.forEach((x,k)=>{if(x!==null)set(ins[k],x)});document.querySelector('button[type=submit]').click();return 'filled'})()" >/dev/null; sleep 4
    js "${FIRE}fire([...document.querySelectorAll('button')].find(b=>/통신사를 선택/.test(b.innerText)));'ok'" >/dev/null; sleep 2
    js "${FIRE}const e=[...document.querySelectorAll('div')].find(e=>e.children.length==0&&e.innerText.trim()=='SKT 알뜰폰');fire(e);'ok'" >/dev/null; sleep 2
    js "${FIRE}const c=[...document.querySelectorAll('[role=button],[role=checkbox],button,label')].filter(e=>/전체 동의/.test(e.innerText||''));c.sort((a,b)=>a.innerText.length-b.innerText.length);fire(c[0]);'ok'" >/dev/null; sleep 1
    js "${FIRE}fire([...document.querySelectorAll('button')].find(b=>b.innerText.trim()=='다음'));'ok'" >/dev/null; sleep 5
    if txt | grep -q "인증번호를 입력"; then echo SMS_SENT; else txt | head -5; echo FAILED; exit 1; fi ;;
  code)
    [[ "${2:-}" =~ ^[0-9]{6}$ ]] || { echo "usage: $0 code <6자리>"; exit 2; }
    js "(()=>{const i=document.querySelector('input');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,'$2');i.dispatchEvent(new Event('input',{bubbles:true}));${FIRE}setTimeout(()=>fire([...document.querySelectorAll('button')].find(b=>b.innerText.trim()=='인증하기')),300);return 'ok'})()" >/dev/null; sleep 7
    js "${FIRE}const e=[...document.querySelectorAll('*')].find(e=>e.children.length==0&&/remin1994@gmail.com/.test(e.innerText||''));e&&fire(e.closest('button,[role=button],li')||e);'ok'" >/dev/null; sleep 6
    if osascript -e 'tell application "Google Chrome" to get URL of every tab of every window' | grep -q "business.toss.im"; then txt | head -5; echo FAILED; exit 1; else echo LOGGED_IN; fi ;;
  resend)
    js "${FIRE}fire([...document.querySelectorAll('button')].find(b=>/다시 받기/.test(b.innerText)));'RESENT'" ;;
  *) echo "usage: $0 send | code <6자리> | resend"; exit 2 ;;
esac
