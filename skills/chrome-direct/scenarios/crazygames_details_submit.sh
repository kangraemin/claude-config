#!/bin/bash
# CrazyGames 개발자 포털 3단계(Details) 채우기 → 4단계 제출 (2026-10-31 '이게 되네'로 검증).
# 사용: crazygames_details_submit.sh <game_id> --cat Action --tags "Horde Survival,RPG,Monster,Pixel,Top-Down" \
#        --desc d.txt --controls c.txt --tools "Claude,ChatGPT,Other" [--other "Suno (music)"] \
#        --covers "land1920x1080.png port800x1200.png sq800x800.png" --videos "land1920x1080.mp4 port1080x1620.mp4" [--submit]
# 전제: Chrome에 CrazyGames 개발자 로그인 탭, 1·2단계(Upload·QA)는 끝남, 지금 화면이 Details.
# 알게 된 것:
#   - Category·Tags·Tools는 MUI Select(메뉴 모달). 콤보박스에 mousedown → [role=option] click → '#menu- .MuiBackdrop-root' click 으로 닫는다.
#     메뉴가 열린 채로 실제 클릭을 하면 엉뚱한 태그가 토글된다(Horde Survival이 빠지고 Survival이 들어갔던 일).
#   - Description·Controls는 Quill(.ql-editor). innerHTML에 <p>줄</p>을 넣으면 반영된다.
#   - 영상: 세로는 2:3(1080x1620)만 받는다. 1080x1920은 'Incorrect video dimensions'. 20초 이하.
#   - Save·체크박스·Submit은 JS click이 안 먹는다 → getBoundingClientRect + 창 위치(screenX, 툴바 높이)로 cliclick.
set -e
GID=$1; shift
CAT=; TAGS=; DESC=; CTRL=; TOOLS=; OTHER=; COVERS=; VIDEOS=; SUBMIT=0; M=developer.crazygames.com
while [ $# -gt 0 ]; do case $1 in --cat) CAT=$2; shift;; --tags) TAGS=$2; shift;; --desc) DESC=$2; shift;; --controls) CTRL=$2; shift;;
  --tools) TOOLS=$2; shift;; --other) OTHER=$2; shift;; --covers) COVERS=$2; shift;; --videos) VIDEOS=$2; shift;; --submit) SUBMIT=1;; --match) M=$2; shift;; esac; shift; done
CC="python3 $HOME/.claude/skills/chrome-direct/chromectl.py"
J() { $CC js "$1" --match $M; }
# 실제 클릭: 화면 안 요소를 JS로 찾아 화면 좌표로 cliclick
RC() { local xy; xy=$(J "(()=>{const e=($1);if(!e)return '';e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return Math.round(window.screenX+r.x+r.width/2)+','+Math.round(window.screenY+window.outerHeight-window.innerHeight+r.y+r.height/2)})()");
  [ -n "$xy" ] && osascript -e 'tell application "Google Chrome" to activate' && sleep 0.5 && cliclick "c:$xy"; }  # 한 번만(체크박스는 두 번 누르면 꺼진다)
# MUI Select 다중 선택: n번째 콤보박스를 열고 목록을 원하는 값과 맞춘다
SEL() { local idx=$1 want=$2; J "(()=>{const s=document.querySelectorAll('[role=combobox]')[$idx];s.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,button:0}));return 1})()" >/dev/null; sleep 1
  J "(()=>{const w=$(python3 -c "import json,sys;print(json.dumps(sys.argv[1].split(',')))" "$want");[...document.querySelectorAll('[role=option]')].forEach(o=>{const on=o.getAttribute('aria-selected')==='true';if(w.includes(o.textContent.trim())!==on)o.click()});document.querySelector('.MuiPopover-root .MuiBackdrop-root')?.click();return document.querySelectorAll('[role=combobox]')[$idx].innerText.replace(/\n/g,',')})()"; sleep 1; }
[ -n "$CAT" ] && SEL 0 "$CAT"
[ -n "$TAGS" ] && SEL 1 "$TAGS"
for pair in "0:$DESC" "1:$CTRL"; do i=${pair%%:*}; f=${pair#*:}; [ -z "$f" ] && continue
  J "(()=>{const t=$(python3 -c "import json,sys;print(json.dumps(open(sys.argv[1]).read().strip()))" "$f");document.querySelectorAll('.ql-editor')[$i].innerHTML=t.split('\n').map(l=>'<p>'+l.replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</p>').join('');return 'ok'})()"; done
[ -n "$TOOLS" ] && SEL 2 "$TOOLS"
if [ -n "$OTHER" ]; then J "(()=>{const i=document.querySelector('input[placeholder^=\"Which other tools\"]');if(!i)return 'none';Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,$(python3 -c "import json,sys;print(json.dumps(sys.argv[1]))" "$OTHER"));i.dispatchEvent(new Event('input',{bubbles:true}));return 'ok'})()"; fi
i=0; for f in $COVERS; do $CC upload "$f" --match $M --sel 'input[type=file]' --value $i; i=$((i+1)); sleep 3; done
for f in $VIDEOS; do $CC upload "$f" --match $M --sel 'input[type=file]' --value $i; i=$((i+1)); sleep 15; done
RC "[...document.querySelectorAll('button')].find(x=>/Save and continue/.test(x.textContent))"; sleep 6
J "(()=>[...document.querySelectorAll('h1,h2,h3,h4')].map(x=>x.innerText).join(','))()"
if [ $SUBMIT = 1 ]; then
  for k in 0 1; do RC "[...document.querySelectorAll('input[type=checkbox]')].filter(x=>!x.checked)[0]"; sleep 0.5; done
  RC "[...document.querySelectorAll('button')].find(x=>/Submit for approval/.test(x.textContent))"; sleep 6
  J "(()=>/Waiting for review/.test(document.body.innerText)?'RESULT: SUBMITTED':'RESULT: CHECK '+location.href)()"
fi
