#!/bin/bash
# ASC 앱 개인정보(영양 표시) 입력·게시 — 공개 API가 없어 Chrome JS 조작 (2026-10-31 '이게 되네' 검증).
# 사용: asc_privacy.sh [앱번호=6829073185]   데이터 수집 없는 앱: NO_DATA=1 asc_privacy.sh <앱번호> ('아니요, 수집하지 않음' → 저장 → 게시)
#   전제: Chrome Profile 1에 ASC 로그인. 이미 게시돼 있으면 '시작하기'가 없어 건너뛴다.
# 선언: 기기ID·사용자ID·게임플레이 콘텐츠·제품 상호작용·광고 데이터·충돌/실적/기타 진단 (Firebase+AdMob+서버 저장 기준). 기기ID·광고 데이터는 추적(ATT).
APP=${1:-6829073185}
CC=$HOME/.claude/skills/chrome-direct/chromectl.py
T=${T:-$(mktemp -d)}
J() { printf '%s' "$2" > $T/j.js; tmux -L gh new-session -d -s aa$$ "python3 -c \"
import sys;sys.argv=['x','js',open('$T/j.js').read(),'--match','$1'];exec(open('$CC').read())\" > $T/o 2>&1; tmux -L gh wait-for -S aad$$"; tmux -L gh wait-for aad$$; cat $T/o; }
NT() { tmux -L gh new-session -d -s an$$ "python3 $CC newtab '$1' --profile 'Profile 1' > $T/n 2>&1; tmux -L gh wait-for -S and$$"; tmux -L gh wait-for and$$; tail -1 $T/n; }
MCF='const MC=b=>["pointerdown","mousedown","pointerup","mouseup","click"].forEach(n=>b.dispatchEvent(new MouseEvent(n,{bubbles:true,button:0})));'
# clk <text> : 대화상자(없으면 문서)에서 정확히 일치하는 버튼 클릭
clk() { J $A "(()=>{$MCF const r=document.querySelector('[role=dialog]')||document;const b=[...r.querySelectorAll('button')].find(x=>x.textContent.trim()==='$1'&&!x.disabled);if(!b)return 'nobtn';MC(b);return 'ok'})()"; }
dlg() { J $A '(()=>{const d=document.querySelector("[role=dialog]");return d?d.innerText:"(no dialog) "+document.body.innerText.slice(0,2500)})()'; }
clkt() { J $A "(()=>{$MCF const r=document.querySelector('[role=dialog]')||document;const e=[...r.querySelectorAll('*')].filter(x=>x.children.length===0&&x.textContent.trim()==='$1').pop();if(!e)return 'none';MC(e);return 'ok'})()"; }
chk() { # 라벨들(|구분) 체크
  J $A "(()=>{const d=document.querySelector('[role=dialog]');const o=[];for(const w of '$1'.split('|')){const e=[...d.querySelectorAll('*')].find(x=>x.children.length===0&&x.textContent.trim()===w);let t=e;while(t&&!t.querySelector('input[type=checkbox],input[type=radio]'))t=t.parentElement;const i=t&&t.querySelector('input');if(i&&!i.checked)i.click();o.push(w+':'+(i&&i.checked))}return o.join(' ')})()"; }
rad() { J $A "(()=>{const r=document.querySelectorAll('[role=dialog] input[type=radio]');r[$1].click();return r[$1].checked})()"; }
dtype() { # name purposes linkedIdx trackIdx
  clkt "$1 설정" >/dev/null; sleep 2; chk "$2" >/dev/null; clk 다음 >/dev/null; sleep 2; rad $3 >/dev/null; clk 다음 >/dev/null; sleep 2
  for i in 1 2 3 4; do
    S=$(J $A "(()=>{const d=document.querySelector('[role=dialog]');if(!d)return 'closed';const t=d.innerText;const r=d.querySelectorAll('input[type=radio]');if(r.length==2&&/사용합니까/.test(t)){r[$4].click();return 'track'}return 'next'})()")
    case "$S" in closed) break;; track) sleep 1; clk 저장 >/dev/null; sleep 3; break;; *) clk 다음 >/dev/null; sleep 2;; esac
  done
  echo "$1 done: $(J $A "(()=>document.querySelector('[role=dialog]')?'STILL OPEN':'ok')()")"
}
A=$(NT "https://appstoreconnect.apple.com/apps/$APP/distribution/privacy" | tail -1); A=${A#id:}; A=id:$A; sleep 14
if ! J $A '(()=>[...document.querySelectorAll("button")].some(b=>b.textContent.trim()==="시작하기")?"start":"no")()' | grep -q start; then echo "이미 시작됨/게시됨"; exit 0; fi
clk 시작하기; sleep 3
if [ -n "${NO_DATA:-}" ]; then
  J $A "(()=>{const d=document.querySelector('[role=dialog]');const r=d.querySelectorAll('input[type=radio]');r[r.length-1].click();return r.length})()"; sleep 1; clk 저장; sleep 4
  clk 게시; sleep 3; clk 게시; sleep 5
  J $A '(()=>document.body.innerText.match(/[^\n]*(게시함|수집되지 않음)[^\n]*/)?.[0]||"CHECK")()'; exit 0
fi
J $A "(()=>{const d=document.querySelector('[role=dialog]');d.querySelectorAll('input[type=radio]')[0].click();return 1})()" >/dev/null; sleep 1; clk 저장; sleep 2; clk 다음; sleep 3
J $A "(()=>{const d=document.querySelector('[role=dialog]');for(const w of ['사용자 ID','기기 ID','제품 상호 작용','광고 데이터','충돌 데이터','실적 데이터','기타 진단 데이터','게임 플레이 콘텐츠']){const e=[...d.querySelectorAll('*')].find(x=>x.children.length===0&&x.textContent.trim()===w);let t=e;while(t&&!t.querySelector('input[type=checkbox]'))t=t.parentElement;const i=t&&t.querySelector('input[type=checkbox]');if(i&&!i.checked)i.click()}return 1})()" >/dev/null
clk 저장; sleep 4; clk 승인; sleep 4
dtype '게임 플레이 콘텐츠' '앱 기능' 0 1
dtype '사용자 ID' '분석|앱 기능' 0 1
dtype '기기 ID' '타사 광고|분석|앱 기능' 0 0
dtype '제품 상호 작용' '분석' 0 1
dtype '광고 데이터' '타사 광고' 0 0
dtype '충돌 데이터' '분석|앱 기능' 1 1
dtype '실적 데이터' '분석|앱 기능' 1 1
dtype '기타 진단 데이터' '분석|앱 기능' 1 1
clk 게시; sleep 3; clk 게시; sleep 5
J $A '(()=>document.body.innerText.match(/[^\n]*게시함/)?.[0]||"CHECK")()'
