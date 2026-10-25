"""Claude 콘솔 결제(platform.claude.com/settings/billing)에서 크레딧 잔액·프로모션 크레딧·만료일·월 지출 한도를 뽑는다.
사용: anthropic_billing.py [--profile "Profile 3"]   (Profile 3 = 회사 ram@gccompany.co.kr, Profile 1 = 개인)
로그아웃이면 RESULT: LOGIN_REQUIRED. 로그인은 '/login'에서 'Google로 계속하기'를 rclick(JS click은 '로그인 중 오류')한다.
"""
import sys, time
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from _common import js, parser, tab
a = parser("anthropic_billing").parse_args()
with tab("https://platform.claude.com/settings/billing", a) as tid:
    time.sleep(12)
    t = js(tid, "return location.pathname + '\\n' + document.body.innerText")
    if "Google로 계속하기" in t:
        print("RESULT: LOGIN_REQUIRED"); sys.exit(2)
    i = t.find("크레딧 잔액")
    print(t[i:i + 700])
    j = t.find("지출 한도")
    print(t[j:j + 200])
    print("RESULT: OK")
