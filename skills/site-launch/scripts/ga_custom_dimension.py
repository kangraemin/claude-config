"""GA4 맞춤 측정기준 등록 — 실제 Chrome(Profile 1, 계정 관리자)으로 GA 관리 > 맞춤 정의 조작.
서비스 계정은 뷰어라 API로 못 만든다(읽기만). 새 탭을 따로 열고, 탭 속성 ID(hash)가 대상과 같은지 확인한 뒤 저장한다.
  python3 ga_custom_dimension.py <속성ID> [--dry-run]    (App Platform=EVENT, App Platform User=USER, 둘 다 app_platform)
이미 있으면 건너뜀(API로 확인). 마지막 줄 RESULT: ..."""
import os, sys, time
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _sa import sess
pid = sys.argv[1]; ACC = '136249894'
WANT = [('App Platform', 'EVENT', '이벤트'), ('App Platform User', 'USER', '사용자')]
s = sess('https://www.googleapis.com/auth/analytics.readonly')
def pname():
    return s.get(f'https://analyticsadmin.googleapis.com/v1beta/properties/{pid}').json()['displayName']
PN = pname()
def have():
    r = s.get(f'https://analyticsadmin.googleapis.com/v1beta/properties/{pid}/customDimensions').json().get('customDimensions', [])
    return {(d['scope'], d['parameterName']) for d in r}
todo = [w for w in WANT if (w[1], 'app_platform') not in have()]
if not todo: print('RESULT: OK already'); sys.exit(0)
t = c.new_tab(f'https://analytics.google.com/analytics/web/?authuser=0#/a{ACC}p{pid}/admin/customdefinitions/hub', profile='Profile 1')
J = c.run_js
try:
    c.google_relogin(t); c.shot(t, '/private/tmp/claude-502/ga-front.png')
    for _ in range(30):
        if '맞춤 측정기준 만들기' in (J(t, 'document.body.innerText') or ''): break
        time.sleep(1)
    for name, scope, ko in todo:
        hdr = J(t, "document.body.innerText.slice(0,200)") or ''
        if f'p{pid}/' not in (J(t, 'location.hash') or '') + '/' or PN not in hdr: raise RuntimeError('탭이 다른 속성으로 바뀜(GA가 마지막 사용 속성으로 튕김): ' + hdr[:80].replace('\n', ' '))
        J(t, "[...document.querySelectorAll('button')].filter(b=>b.innerText.trim()=='맞춤 측정기준 만들기').forEach(b=>b.click())")
        for _ in range(10):
            if J(t, "document.querySelector('.cdk-overlay-container input')?'y':''"): break
            time.sleep(1)
        O = '.cdk-overlay-container '
        c.fill(t, O + 'input', name)
        if scope == 'USER':  # 범위 셀렉트: 이벤트 -> 사용자
            J(t, "document.querySelector('.cdk-overlay-container mat-select').click()"); time.sleep(1)
            J(t, "[...document.querySelectorAll('.cdk-overlay-container mat-option,[role=option]')].find(o=>o.innerText.trim().startsWith('사용자')).click()"); time.sleep(1)
        ins = J(t, "[...document.querySelectorAll('.cdk-overlay-container input')].map(e=>e.id).join()").split(',')
        c.fill(t, O + '#' + ins[-1], 'app_platform'); time.sleep(1)
        if '--dry-run' in sys.argv: print('DRY', name, J(t, "[...document.querySelectorAll('.cdk-overlay-container input')].map(e=>e.value).join('|')")); continue
        # 저장 버튼엔 type 속성이 없어 [type=submit]으로 못 찾는다(상권.kr 11/7) — 글자로 찾는다
        print('save', J(t, "(()=>{const b=[...document.querySelectorAll('.cdk-overlay-container button')].find(x=>x.innerText.trim()=='저장');if(!b)return 'nobtn';if(b.disabled)return 'disabled';b.click();return 'clicked'})()"))
        for _ in range(15):
            time.sleep(1)
            if (scope, 'app_platform') in have(): break
finally:
    c.close_tab(t)
print('RESULT:', 'OK' if all((w[1], 'app_platform') in have() for w in WANT) else 'FAIL', sorted(have()))
