"""Usage: play_dev_status.py [--admob]

Google Play Console 개발자 계정 설정 상태(본인 확인·Android 기기 확인·전화번호 인증)를 읽는다. --admob이면 AdMob 홈의
계정 상태(비활성/검토 중/결제 문제)도 읽는다. 아무것도 누르거나 제출하지 않는다.
Pre: Chrome Profile 1 = remin1994@gmail.com 로그인. 화면 조작인 이유: 개발자 계정 인증 상태는 공개 API가 없다.
Gotcha: Play Console은 Angular라 백그라운드 탭에서 안 그려진다 → c.shot으로 앞으로 띄운 뒤 읽는다.
        개발자 선택 화면(developer-item)은 JS click이 통한다. 본인 확인 '시작하기'는 실제 신분증 사진이 필요해 스크립트 대상 아님.
RESULT: PLAY_READY | PLAY_PENDING:<단계,...> | PLAY_NO_ACCOUNT | UNKNOWN
"""
import os
import re
import tempfile
import time

from _common import c, js, parser, tab

ap = parser("Play Console developer account setup status")
ap.add_argument("--admob", action="store_true")
a = ap.parse_args()
png = os.path.join(tempfile.gettempdir(), "play_dev_status.png")


def read(tid, wait=10):
    c.shot(tid, png)
    time.sleep(wait)
    return js(tid, "return document.body.innerText")


with tab("https://play.google.com/console/u/0/developers", a) as tid:
    txt = read(tid)
    if "개발자 계정 선택" in txt:
        js(tid, "const e=document.querySelector('developer-item'); if(e) e.click(); return 1")
        txt = read(tid, 12)
    m = re.search(r"(개인|조직) 계정\s*계정 ID: (\d+)", txt)
    print("account:", m.group(1) + " " + m.group(2) if m else "?")
    steps = []
    for name in ["본인 확인", "Android 휴대기기에 액세스할 수 있는지 확인", "연락처 전화번호 인증", "웹사이트 인증"]:
        i = txt.find(name)
        if i >= 0:
            st = "조치 필요" if "조치 필요" in txt[i:i + 40] else ("완료" if "완료" in txt[i:i + 40] else "?")
            print(f"- {name}: {st}")
            if st == "조치 필요":
                steps.append(name.split()[0])
    if a.admob:
        c.goto(tid, "https://admob.google.com/v2/home")
        time.sleep(4)
        at = read(tid, 10)
        for k in ["비활성", "검토하고 있습니다", "결제 문제", "광고 게재가 제한됨"]:
            if k in at:
                print("admob:", k)
    if not m and "앱 만들기" not in txt:
        print("RESULT: PLAY_NO_ACCOUNT" if "계정 만들기" in txt else "RESULT: UNKNOWN")
    else:
        print("RESULT: " + ("PLAY_PENDING:" + ",".join(steps) if steps else "PLAY_READY"))
