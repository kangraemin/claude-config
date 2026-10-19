"""GA4 속성 + 웹 스트림 만들기 — GA 웹 화면을 실제 Chrome 'Profile 1'(remin1994, 계정 관리자)로 조작.
서비스 계정은 뷰어라 API로 속성 생성 불가(403), gcloud ADC는 analytics 스코프가 '차단된 앱'이라 불가 → 화면 조작이 유일한 경로.
  python3 ga_property.py "<속성 이름>" https://site [--dry-run]
마지막 줄: MEASUREMENT_ID G-XXXX (서비스 계정 API로 읽음). 이미 같은 이름 속성이 있으면 만들지 않고 ID만 출력."""
import os, sys, time
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c
from _sa import sess, GA_ACCOUNT
name, site = sys.argv[1], sys.argv[2].rstrip('/')
dry = '--dry-run' in sys.argv
s = sess('https://www.googleapis.com/auth/analytics.edit'); B = 'https://analyticsadmin.googleapis.com/v1beta'

def find():
    for a in s.get(B + '/accountSummaries').json()['accountSummaries']:
        for p in a.get('propertySummaries', []):
            if p['displayName'] == name:
                st = s.get(B + '/' + p['property'] + '/dataStreams').json().get('dataStreams', [])
                return p['property'], [x.get('webStreamData', {}).get('measurementId') for x in st]
    return None, []

prop, ids = find()
if prop and ids:
    print('exists', prop); print('MEASUREMENT_ID', ids[0]); sys.exit(0)
acc = GA_ACCOUNT.split('/')[1]
# 속성 ID 없는 #/a<acc>/admin/... 주소는 안 그려진다 → 아무 기존 속성 ID를 붙인다
anyp = [p for a in s.get(B + '/accountSummaries').json()['accountSummaries'] if a['account'] == GA_ACCOUNT for p in a['propertySummaries']][0]['property'].split('/')[1]
t = c.new_tab(f'https://analytics.google.com/analytics/web/?authuser=0#/a{acc}p{anyp}/admin/property/create', profile='Profile 1')
c.google_relogin(t)  # 로그아웃돼 있으면 패스키 시트까지 눌러 다시 로그인
c.shot(t, '/tmp/ga-front.png')  # 탭을 앞으로(백그라운드면 Angular가 안 그려짐)
J = c.js_json
def overlay_pick(word):
    return J(t, f"const o=[...document.querySelectorAll('.cdk-overlay-container [role=option], .cdk-overlay-container mat-option, .cdk-overlay-container button')].find(o=>o.innerText.trim().startsWith('{word}'));if(!o)return 'NF';o.scrollIntoView();o.click();return 'ok'")
def wait(word, n=20):
    for _ in range(n):
        if word in J(t, "return document.body.innerText"): return True
        time.sleep(1)
    raise RuntimeError('timeout waiting ' + word)
def btn(label):
    J(t, f"[...document.querySelectorAll('button')].filter(b=>b.innerText.trim()=='{label}').pop().click();return 1")
try:
    wait('속성 이름', 40)
    # 1. 속성 이름·국가(대한민국 → 시간대 자동)·통화
    c.fill(t, 'input[type=text]', name); time.sleep(1)
    J(t, "document.querySelector('ga-country-selector searchable-select button').click();return 1"); time.sleep(1.5)
    print('country', overlay_pick('대한민국')); time.sleep(2)
    J(t, "document.querySelector('currency-selector searchable-select button').click();return 1"); time.sleep(1.5)
    print('currency', overlay_pick('대한민국 원')); time.sleep(1)
    btn('다음'); wait('업종 선택')
    # 2. 업종·규모
    c.press(t, text='업종 선택'); time.sleep(1.5)
    print('industry', overlay_pick(os.environ.get('GA_INDUSTRY', '도서 및 문학')))
    c.press(t, text='작음 - 직원 1~10명'); time.sleep(1)
    btn('다음'); wait('비즈니스 목표 선택')
    # 3. 목표: 트래픽 파악 + 참여·유지율 (mat-checkbox는 내부 input을 눌러야 체크됨)
    J(t, "const i=[...document.querySelectorAll('input.mdc-checkbox__native-control')].filter(x=>/트래픽 파악|참여 발생/.test(x.getAttribute('aria-label')||''));i.forEach(x=>x.checked||x.click());return i.length")
    if dry:
        print('RESULT: DRY_RUN (만들기 직전에서 멈춤)'); sys.exit(0)
    btn('만들기'); wait('플랫폼을 선택하세요', 30)
    # 4. 웹 스트림
    c.press(t, text='웹'); wait('스트림 이름')
    c.fill(t, "input[aria-label='웹사이트 URL']", site.split('://')[-1]); time.sleep(0.5)
    c.fill(t, "input[placeholder='내 웹사이트']", name + ' web'); time.sleep(1)
    btn('만들고 계속하기'); time.sleep(10)
finally:
    c.close_tab(t)
prop, ids = find()
print('property', prop); print('MEASUREMENT_ID', ids[0] if ids else 'NONE')
