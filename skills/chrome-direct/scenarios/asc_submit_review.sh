#!/bin/bash
# ASC iOS 앱 심사 제출 (2026-10-31 '이게 되네' 검증). 인앱 첫 제출 포함.
# 사용: asc_submit_review.sh [앱번호=6829073185]   전제: ASC API 키(~/.claude/.env), Chrome Profile 1에 ASC 로그인, tmux -L gh.
# 순서
#  1) API: 가격(무료) 스케줄 없으면 생성 — 없으면 '심사에 추가'가 "가격 등급을 선택해야 합니다"로 막힌다.
#  2) API: 심사 메모·릴리스 방식 MANUAL(AFTER_APPROVAL 대신) 설정.
#  3) API: reviewSubmission 초안 생성 + 앱 버전 item 추가.
#  4) Chrome: 첫 소모품은 API가 STATE_ERROR.FIRST_CONSUMABLE_MUST_BE_SUBMITTED_ON_VERSION으로 거절 → 각 인앱 페이지
#     /apps/<앱>/distribution/iaps/<id> 의 '심사에 추가'(팝오버) → 'iOS 제출 초안' 선택을 전부 반복. 버전 페이지에는 인앱 섹션이 없다.
#  5) API: reviewSubmission submitted=true → WAITING_FOR_REVIEW.
#  거절(해결되지 않은 문제) 뒤 인앱을 더 넣어 재제출할 때(2026-11-07 눈썰미 검증):
#    - 인앱 '심사에 추가' 팝오버는 거절된 제출을 고를 수 없고 'iOS 제출 초안'만 보인다. API reviewSubmissionItems에는 인앱 관계가 없다.
#    - API로 거절 제출의 항목 삭제·취소는 409. 화면 제출 상세의 '제출 취소' → 대화상자 '확인'으로 취소(CANCELING→COMPLETE, 수십 초).
#    - 그다음 이 스크립트를 다시 돌리면 버전을 초안에 넣고 인앱 전부를 '심사에 추가'한 뒤 제출한다. 회신 글은 옛 제출에 남는다.
#    - REVIEW_NOTES를 안 주면 Forge Survivor 기본 메모로 덮어쓴다 — 다른 앱은 반드시 REVIEW_NOTES를 넘기거나 prep 단계를 건너뛴다.
APP=${1:-6829073185}
set -a; source ~/.claude/.env; set +a
export APP
PY=$(mktemp -d)/s.py
cat > $PY <<'PYEOF'
import sys, os, json
sys.path.insert(0, os.path.expanduser('~/.config/forge-survivor'))
from asc_api import call
APP = os.environ["APP"]; step = sys.argv[1]
V = call("GET", f"/v1/apps/{APP}/appStoreVersions")["data"][0]["id"]
if step == "prep":
    pp = call("GET", f"/v1/apps/{APP}/appPricePoints?filter[territory]=KOR&limit=1&fields[appPricePoints]=customerPrice")["data"][0]["id"]
    try:
        call("POST", "/v1/appPriceSchedules", {"data": {"type": "appPriceSchedules", "relationships": {"app": {"data": {"type": "apps", "id": APP}}, "baseTerritory": {"data": {"type": "territories", "id": "KOR"}}, "manualPrices": {"data": [{"type": "appPrices", "id": "${p1}"}]}}}, "included": [{"type": "appPrices", "id": "${p1}", "attributes": {"startDate": None}, "relationships": {"appPricePoint": {"data": {"type": "appPricePoints", "id": pp}}}}]})
    except SystemExit: pass
    d = call("GET", f"/v1/appStoreVersions/{V}/appStoreReviewDetail")["data"]["id"]
    notes = os.environ.get("REVIEW_NOTES") or ("Forge Survivor is a single-player action roguelite: forge weapons and survive waves of monsters. No login or demo account needed. Rewarded video ads (AdMob) are optional and grant in-game rewards. In-app purchases are in the lobby Shop tab; purchases can be restored from Settings. The in-app purchases are submitted together with this first version.")
    call("PATCH", f"/v1/appStoreReviewDetails/{d}", {"data": {"type": "appStoreReviewDetails", "id": d, "attributes": {"notes": notes}}})
    call("PATCH", f"/v1/appStoreVersions/{V}", {"data": {"type": "appStoreVersions", "id": V, "attributes": {"releaseType": "MANUAL"}}})
    subs = [s for s in call("GET", f"/v1/apps/{APP}/reviewSubmissions")["data"] if s["attributes"]["state"] == "READY_FOR_REVIEW"]
    if subs: S = subs[0]["id"]
    else: S = call("POST", "/v1/reviewSubmissions", {"data": {"type": "reviewSubmissions", "attributes": {"platform": "IOS"}, "relationships": {"app": {"data": {"type": "apps", "id": APP}}}}})["data"]["id"]
    try: call("POST", "/v1/reviewSubmissionItems", {"data": {"type": "reviewSubmissionItems", "relationships": {"reviewSubmission": {"data": {"type": "reviewSubmissions", "id": S}}, "appStoreVersion": {"data": {"type": "appStoreVersions", "id": V}}}}})
    except SystemExit: pass
    print("prep ok", S)
elif step == "ids":
    print("\n".join(x["id"] for x in call("GET", f"/v1/apps/{APP}/inAppPurchasesV2?limit=200")["data"]))
elif step == "submit":
    S = [s for s in call("GET", f"/v1/apps/{APP}/reviewSubmissions")["data"] if s["attributes"]["state"] == "READY_FOR_REVIEW"][0]["id"]
    r = call("PATCH", f"/v1/reviewSubmissions/{S}", {"data": {"type": "reviewSubmissions", "id": S, "attributes": {"submitted": True}}})
    print(r["data"]["attributes"]["state"])
PYEOF
CC=$HOME/.claude/skills/chrome-direct/chromectl.py
T=$(mktemp -d)
J() { printf '%s' "$2" > $T/j.js; tmux -L gh new-session -d -s aa$$ "python3 -c \"
import sys;sys.argv=['x','js',open('$T/j.js').read(),'--match','$1'];exec(open('$CC').read())\" > $T/o 2>&1; tmux -L gh wait-for -S aad$$"; tmux -L gh wait-for aad$$; cat $T/o; }
NT() { tmux -L gh new-session -d -s an$$ "python3 $CC newtab '$1' --profile 'Profile 1' > $T/n 2>&1; tmux -L gh wait-for -S and$$"; tmux -L gh wait-for and$$; tail -1 $T/n; }
python3 $PY prep || exit 1
A=$(NT "https://appstoreconnect.apple.com/apps/$APP/distribution/iaps"); A=id:${A#id:}; sleep 12
ADD='(()=>{const MC=b=>["pointerdown","mousedown","pointerup","mouseup","click"].forEach(n=>b.dispatchEvent(new MouseEvent(n,{bubbles:true,button:0})));const b=[...document.querySelectorAll("button")].find(x=>x.textContent.trim()==="심사에 추가"&&!x.disabled);if(!b)return "nobtn";MC(b);return "clicked"})()'
PICK='(()=>{const MC=b=>["pointerdown","mousedown","pointerup","mouseup","click"].forEach(n=>b.dispatchEvent(new MouseEvent(n,{bubbles:true,button:0})));const b=[...document.querySelectorAll("button")].find(x=>x.textContent.trim()==="심사에 추가");const p=document.getElementById(b.getAttribute("aria-describedby"));const e=[...p.querySelectorAll("button,a,[role=menuitem],li,div")].filter(x=>/^iOS 제출 초안/.test(x.innerText.trim())).pop();if(!e)return "nopick";MC(e);return "picked"})()'
for id in $(python3 $PY ids); do
  J $A "location.href='/apps/$APP/distribution/iaps/$id';1" >/dev/null; sleep 7
  J $A "$ADD" >/dev/null; sleep 1.5
  echo "$id $(J $A "$PICK")"; sleep 1.5
done
python3 $PY submit
