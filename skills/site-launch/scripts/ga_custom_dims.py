"""GA4 맞춤 측정기준 등록 — GA 화면을 Chrome 'Profile 1'로 조작(서비스 계정은 뷰어라 API 불가).
  python3 ga_custom_dims.py <속성ID> [이름:범위:매개변수 ...]
기본값: 앱 플랫폼:event:app_platform  앱 플랫폼(사용자):user:app_platform  빌드:event:build
이미 있는 측정기준(매개변수 기준)은 건너뛴다. 마지막 줄 RESULT: ..."""
import os, sys, time
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
sys.path.insert(0, os.path.dirname(__file__))
import chromectl as c
from _sa import sess, GA_ACCOUNT
prop = sys.argv[1]
specs = [a.split(':') for a in sys.argv[2:]] or [['앱 플랫폼','event','app_platform'],['앱 플랫폼(사용자)','user','app_platform'],['빌드','event','build']]
s = sess('https://www.googleapis.com/auth/analytics.readonly')
def existing():
    r = s.get(f'https://analyticsadmin.googleapis.com/v1beta/properties/{prop}/customDimensions').json().get('customDimensions', [])
    return {(d['parameterName'], d['scope']) for d in r}
acc = GA_ACCOUNT.split('/')[1]
t = c.new_tab(f'https://analytics.google.com/analytics/web/?authuser=0#/a{acc}p{prop}/admin/customdefinitions/hub', profile='Profile 1')
J = c.js_json
try:
    c.google_relogin(t); c.shot(t, '/private/tmp/ga-front.png')
    for _ in range(30):
        if '맞춤 측정기준 만들기' in J(t, "return document.body.innerText"): break
        time.sleep(1)
    for name, scope, param in specs:
        sc = 'EVENT' if scope == 'event' else 'USER'
        if (param, sc) in existing(): print('exists', name); continue
        J(t, "[...document.querySelectorAll('button')].find(b=>b.innerText.trim()=='맞춤 측정기준 만들기').click();return 1"); time.sleep(2.5)
        J(t, "const v=[...document.querySelectorAll('input[type=text]')].filter(e=>e.offsetParent);v[0].id='cd_name';return v.length")
        c.fill(t, '#cd_name', name)
        J(t, "document.querySelectorAll('mat-select')[document.querySelectorAll('mat-select').length-1].click();return 1"); time.sleep(1.5)
        print('scope', J(t, f"const o=[...document.querySelectorAll('mat-option,[role=option]')].find(o=>o.innerText.trim()=='{'이벤트' if scope=='event' else '사용자'}');if(!o)return 'NF';o.click();return 'ok'")); time.sleep(1)
        c.fill(t, "input[aria-label='이벤트 매개변수 선택'], input[aria-label='사용자 속성 선택']", param); time.sleep(1.5)
        print('param', J(t, f"const o=[...document.querySelectorAll('mat-option,[role=option]')].find(o=>o.innerText.includes('{param}'));if(o){{o.click();return 'picked'}}return 'free'")); time.sleep(1)
        J(t, "[...document.querySelectorAll('button')].filter(b=>b.innerText.trim()=='저장').pop().click();return 1"); time.sleep(4)
finally:
    c.close_tab(t)
have = existing()
ok = all((p, 'EVENT' if sc == 'event' else 'USER') in have for _, sc, p in specs)
print('RESULT:', 'OK' if ok else 'FAIL', sorted(have))
