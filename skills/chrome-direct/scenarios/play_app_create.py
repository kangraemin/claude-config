"""Usage: play_app_create.py --name "오늘의 눈썰미" [--dev 8396615316670096970] [--submit]

Play Console 새 앱 만들기(이름·기본언어 ko-KR·앱/무료·선언 체크박스). 멱등: 같은 이름 앱이 목록에 있으면 EXISTS.
--submit 없으면 dry-run(계정 확인 상태와 만들기 가능 여부만 보고).
Pre: Profile 1 = remin1994 로그인. 화면 조작인 이유: Play Console 앱 생성은 공개 API 없음.
Gotcha: Angular라 c.shot으로 앞에 띄운 뒤 읽는다. 앱 목록의 '앱 만들기' 버튼은 disabled가 아니어도 본인 확인
        미완료면 클릭이 무반응이고 "새 앱을 만들려면 계정 확인을 완료하세요."(lock) 문구가 뜬다. /app/create URL은 home으로 리다이렉트.
        (2026-10-23 개인 계정 kangraemin: 본인 확인·Android 기기 확인·전화번호 인증 모두 '조치 필요' → 막힘)
RESULT: EXISTS | BLOCKED_VERIFICATION | CREATED | DRY_RUN_READY | UNKNOWN
(만들기 이후 스토어 등록정보·앱 콘텐츠 입력 단계는 계정 확인이 끝난 뒤 이 스크립트에 이어 붙일 것 - 현재 미검증)
"""
import os
import sys
import tempfile
import time

from _common import c, js, parser, tab

ap = parser("Play Console create app", submit=True)
ap.add_argument("--name", required=True)
ap.add_argument("--dev", default="8396615316670096970")
a = ap.parse_args()
png = os.path.join(tempfile.gettempdir(), "play_app_create.png")

with tab(f"https://play.google.com/console/u/0/developers/{a.dev}/app-list", a) as tid:
    c.shot(tid, png)
    time.sleep(10)
    c.shot(tid, png)
    txt = js(tid, "return document.body.innerText")
    if a.name in txt:
        print("RESULT: EXISTS")
        sys.exit(0)
    if "새 앱을 만들려면 계정 확인을 완료하세요" in txt:
        print("RESULT: BLOCKED_VERIFICATION")
        sys.exit(2)
    if not a.submit:
        print("RESULT: DRY_RUN_READY")
        sys.exit(0)
    js(tid, "const b=[...document.querySelectorAll('button')].find(b=>/앱 만들기/.test(b.innerText));if(b)b.click();return 1")
    time.sleep(4)
    c.shot(tid, png)
    t2 = js(tid, "return document.body.innerText")
    if "앱 이름" not in t2:
        print("RESULT: UNKNOWN")
        sys.exit(1)
    # 폼 채우기(앱 이름·언어·앱/게임·무료/유료·선언 체크)는 계정 확인 후 실제 화면을 보고 채울 것
    print("RESULT: UNKNOWN (form reached, fill steps not implemented)")
    sys.exit(1)
