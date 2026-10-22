"""네이버 서치어드바이저 등록 — 실제 Chrome 'Profile 1'(네이버 로그인됨)을 chromectl로 조작.
  python3 naver_register.py add     https://site   → 확인 파일명(naverXXXX.html)과 meta 출력. 둘 다 사이트에 넣고 배포.
  python3 naver_register.py verify  https://site   → [소유확인] → 보안문자 그림을 텔레그램으로 보내고 답장(최대 15분) 받아 입력
  python3 naver_register.py sitemap https://site [sitemap.xml]
  python3 naver_register.py rss     https://site [feed.xml]
  python3 naver_register.py crawl   https://site URL [URL ...]  → '웹 페이지 수집' 요청(사이트 하위 URL). URL마다 RESULT 줄
네이버는 경로 붙은 주소를 안 받는다(사이트 단위). 로그아웃이면 chrome-direct/scenarios/naver_login.py --qr --notify.
백그라운드 탭은 Vue 화면이 안 그려지므로 c.shot()으로 탭을 앞으로 띄운 뒤 읽는다."""
import os, re, subprocess, sys, time, urllib.parse, urllib.request, json
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c
TMP = '/tmp/site-launch'; os.makedirs(TMP, exist_ok=True)
cmd, site = sys.argv[1], sys.argv[2].rstrip('/')
# 한글 도메인은 네이버가 한글로 저장한다(xn-- 그대로 찾으면 목록에서 못 찾음)
_u = urllib.parse.urlsplit(site)
if 'xn--' in _u.netloc: site = f"{_u.scheme}://{_u.netloc.encode().decode('idna')}{_u.path}"
q = urllib.parse.quote(site, safe='')

def front(t):
    c.shot(t, f'{TMP}/front.png'); time.sleep(2)

def text(t):
    return c.js_json(t, "return document.body.innerText")

def tg_env():
    env = {}
    for l in open(os.path.expanduser('~/.claude/.env')):
        m = re.match(r'(?:export )?(CONTEST_TG_TOKEN|CONTEST_TG_CHAT_ID)=["\']?([^"\'\n]+)', l)
        if m: env[m[1]] = m[2]
    return env['CONTEST_TG_TOKEN'], env['CONTEST_TG_CHAT_ID']

def captcha(t):
    """보안문자 창이 있으면 텔레그램으로 묻고 입력. 없으면 False."""
    src = c.js_json(t, "const e=document.querySelector('.v-dialog--active .v-image__image');return e?e.style.backgroundImage.slice(5,-2):''")
    if not src: return False
    gif = f'{TMP}/cap.gif'; urllib.request.urlretrieve(src, gif)
    from PIL import Image
    im = Image.open(gif).convert('RGB'); im.resize((im.width * 3, im.height * 3)).save(f'{TMP}/cap.png')
    tok, chat = tg_env()
    sent = json.loads(subprocess.check_output(['curl', '-s', '-F', f'chat_id={chat}', '-F', f'photo=@{TMP}/cap.png', '-F',
        f'caption={site} 네이버 서치어드바이저 보안문자 — 보이는 글자를 답장해 주세요', f'https://api.telegram.org/bot{tok}/sendPhoto']))
    t0 = sent['result']['date']
    print(f'CAPTCHA sent to telegram, waiting reply (or write it to {TMP}/answer.txt)', flush=True)
    for _ in range(180):
        # python urllib은 텔레그램 TLS가 가끔 Connection reset → curl로 읽고 실패하면 다음 회차
        try: ups = json.loads(subprocess.check_output(['curl', '-s', '-m', '15', f'https://api.telegram.org/bot{tok}/getUpdates?offset=-10']))['result']
        except Exception: time.sleep(5); continue
        rep = [u['message']['text'] for u in ups if u.get('message', {}).get('date', 0) > t0 and u['message'].get('text')]
        # 텔레그램 채널 플러그인을 켠 다른 Claude 세션이 답장을 먼저 가져가면 여기로 안 온다 → 채팅으로 받은 답을 이 파일에 쓴다
        af = f'{TMP}/answer.txt'
        if not rep and os.path.exists(af) and os.path.getmtime(af) > t0: rep = [open(af).read().strip()]
        if rep: break
        time.sleep(5)
    else:
        print('RESULT: CAPTCHA_TIMEOUT'); sys.exit(2)
    code = re.sub(r'[^0-9A-Za-z]', '', rep[-1].split()[0]).upper()
    print('captcha answer', code)
    c.js_json(t, f"const i=document.querySelector('.v-dialog--active input');const s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;s.call(i,'{code}');i.dispatchEvent(new Event('input',{{bubbles:true}}));return 1")
    # 확인 뒤 alert가 뜨면 AppleScript JS가 막히므로 setTimeout으로 누르고 빠진다
    c.run_js(t, "setTimeout(()=>{[...document.querySelector('.v-dialog--active').querySelectorAll('button')].find(b=>b.innerText.trim()=='확인').click()},10);'ok'")
    time.sleep(6); return True

t = c.new_tab('https://searchadvisor.naver.com/console/board', profile='Profile 1'); time.sleep(6); front(t)
try:
    if cmd == 'add':
        tx = text(t)
        if site in tx: print('already listed')
        else:
            c.fill(t, 'input[type=text]', site); time.sleep(1)
            c.js_json(t, "[...document.querySelectorAll('button')].find(e=>/exit_to_app/.test(e.textContent)).click();return 1"); time.sleep(6)
        c.goto(t, f'https://searchadvisor.naver.com/console/verify?site={q}'); time.sleep(6); front(t)
        tx = text(t)
        f = re.search(r'naver[0-9a-f]{32}\.html', tx); m = re.search(r'<meta name="naver-site-verification"[^>]*>', tx)
        print('FILE', f and f[0]); print('FILE_CONTENT', f and f'naver-site-verification: {f[0]}'); print('META', m and m[0])
    elif cmd == 'verify':
        c.goto(t, f'https://searchadvisor.naver.com/console/verify?site={q}'); time.sleep(6); front(t)
        c.run_js(t, "setTimeout(()=>{[...document.querySelectorAll('button')].find(b=>b.innerText.trim()=='소유확인').click()},10);'ok'"); time.sleep(4)
        captcha(t)
        c.goto(t, 'https://searchadvisor.naver.com/console/board'); time.sleep(6); front(t)
        tx = text(t); i = tx.find(site)
        ok = i >= 0 and '소유확인 진행' not in tx[i:i + 120]
        print('RESULT:', 'OK' if ok else 'FAIL', tx[i:i + 120] if i >= 0 else 'not listed')
    elif cmd in ('sitemap', 'rss'):
        sm = site + '/' + (sys.argv[3] if len(sys.argv) > 3 else 'sitemap.xml' if cmd == 'sitemap' else 'feed.xml')
        c.goto(t, f'https://searchadvisor.naver.com/console/site/request/{cmd}?site={q}'); time.sleep(7); front(t)
        c.fill(t, 'input[type=text]', sm); time.sleep(1)  # 전체 URL이어야 확인 버튼이 켜진다
        c.run_js(t, "setTimeout(()=>{[...document.querySelectorAll('button')].find(b=>b.innerText.trim()=='확인').click()},10);'ok'"); time.sleep(5)
        captcha(t)
        tx = text(t); i = tx.find('제출된 사이트맵' if cmd == 'sitemap' else '제출된 RSS'); print('RESULT:', tx[i:i + 160].replace('\n', ' ') if i >= 0 else tx[:300].replace('\n', ' '))
    elif cmd == 'crawl':
        c.goto(t, f'https://searchadvisor.naver.com/console/site/request/crawl?site={q}'); time.sleep(7); front(t)
        for url in sys.argv[3:]:
            path = urllib.parse.urlsplit(url).path
            c.fill(t, 'input[type=text]', url); time.sleep(1)
            c.run_js(t, "setTimeout(()=>{[...document.querySelectorAll('button')].find(b=>b.innerText.trim()=='확인').click()},10);'ok'"); time.sleep(4)
            if captcha(t): front(t)
            time.sleep(2); tx = text(t)
            i = tx.find('수집 요청 내역')
            ok = path in tx[i:i + 3000] if i >= 0 else False
            print('RESULT', url, '요청됨' if ok else '확인 안 됨: ' + tx[max(i, 0):max(i, 0) + 200].replace('\n', ' '), flush=True)
finally:
    c.close_tab(t)
