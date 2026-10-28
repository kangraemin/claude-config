"""애드센스에 사이트 추가 → 소유권 확인 → 검토 요청 — 실제 Chrome 'Profile 1'(remin1994, 애드센스 계정 pub-4785237655148075)을 조작.
  python3 adsense_add.py https://site [--dry-run]
먼저 사이트 모든 페이지 head에 애드센스 코드, 루트에 ads.txt를 배포해 둔다(아래 PRE 검사가 확인).
이미 목록에 있으면 추가하지 않고 남은 단계(확인·검토 요청)만 진행하거나 상태만 출력. 로그아웃돼 있으면 google_relogin이 다시 로그인한다.
마지막 줄: RESULT <상태>"""
import os, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

PUB = 'pub-4785237655148075'
site = sys.argv[1].rstrip('/')
dry = '--dry-run' in sys.argv
host = urllib.parse.urlsplit(site if '://' in site else 'https://' + site).hostname.encode('idna').decode()  # IDN은 punycode로 등록

# PRE: 코드·ads.txt가 실제로 배포됐는지(없으면 확인 단계에서 실패하니 먼저 막는다)
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=20).read().decode('utf-8', 'replace')
try:
    has_code = f'ca-{PUB}' in get(f'https://{host}/')
    has_ads = PUB in get(f'https://{host}/ads.txt')
except Exception as e:
    has_code = has_ads = False; print('PRE fetch error', e)
print('PRE adsense code', has_code, '| ads.txt', has_ads)
if not has_code:
    print(f'RESULT: NO_CODE — head에 <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-{PUB}" crossorigin="anonymous"></script> 배포 후 다시'); sys.exit(1)

J = c.js_json
t = c.new_tab(f'https://adsense.google.com/adsense/u/0/{PUB}/sites/list', profile='Profile 1'); time.sleep(8)
def text(): return J(t, 'return document.body.innerText')
def wait(word, n=30):
    for _ in range(n):
        if word in text(): return True
        time.sleep(1)
    raise RuntimeError('timeout waiting ' + word)
def btn(label, cls=None):
    sel = f"document.querySelector('{cls}')" if cls else f"[...document.querySelectorAll('button,material-button')].filter(b=>b.innerText.trim().endsWith('{label}')&&b.offsetParent).pop()"
    return J(t, f"const b={sel};if(!b)return 'NF';b.click();return 'ok'")
try:
    if not c.google_relogin(t):
        print('RESULT: LOGIN_FAILED'); sys.exit(2)
    c.shot(t, '/tmp/adsense-front.png')  # 탭을 앞으로(백그라운드면 Angular가 안 그려짐)
    wait('새 사이트')
    if host not in text():
        if dry:
            print('RESULT: DRY_RUN (추가 직전에서 멈춤)'); sys.exit(0)
        btn('새 사이트'); wait('사이트 추가', 15)
        c.fill(t, 'input[aria-label="웹 사이트"]', host); time.sleep(1.5)
        btn('저장'); time.sleep(8)
    c.goto(t, f'https://adsense.google.com/adsense/u/0/{PUB}/sites/detail/url={host}'); time.sleep(8); c.shot(t, '/tmp/adsense-front.png')
    tx = text()
    if '코드를 삽입했습니다' in tx and '리뷰가 요청됨' not in tx:
        if dry:
            print('RESULT: DRY_RUN (소유권 확인 직전)'); sys.exit(0)
        # 체크박스 → '확인'은 화면에 3개(안내 팝업 등)라 .verify-button을 집는다
        J(t, "const cb=[...document.querySelectorAll('material-checkbox,mat-checkbox,[role=checkbox]')].find(e=>/코드를 삽입했습니다/.test(e.parentElement?.innerText||e.innerText||''));cb&&cb.getAttribute('aria-checked')!='true'&&cb.click();return 1"); time.sleep(1)
        btn('확인', '.verify-button'); wait('사이트가 확인되었습니다', 40)
        btn('다음'); time.sleep(3)
    if '정책 위반이 발견되었습니다' in text():
        # 심사 거절 상태(예: 가치가 별로 없는 콘텐츠, 글마감 10/28). 콘텐츠를 고치기 전에 다시 내지 않는다
        tx = text(); r = next((l for l in ('가치가 별로 없는 콘텐츠', '사이트 다운 또는 사용 불가', '정책 위반') if l in tx), '정책 위반')
        print('RESULT: REJECTED', r); sys.exit(3)
    if '검토 요청' in text() and '리뷰가 요청됨' not in text():
        if dry:
            print('RESULT: DRY_RUN (검토 요청 직전)'); sys.exit(0)
        btn('검토 요청'); wait('리뷰가 요청됨', 30)
    tx = text(); i = tx.find(host, tx.find('작업'))  # 목록 표의 그 사이트 행
    print('RESULT:', ' / '.join(tx[i:i + 200].split('\n')[:4]) if i >= 0 else tx[:200])
finally:
    c.close_tab(t)
