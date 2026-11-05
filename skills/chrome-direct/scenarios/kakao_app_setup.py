#!/usr/bin/env python3
"""python3 kakao_app_setup.py --name 앱이름 --company 회사 --domain https://x.com --category 건강 --package com.x --hash HASH= [--hash HASH2=] [--local-properties path] [--icon a.png] [--no-qr] [--stop]

카카오 디벨로퍼스에 안드로이드용 앱을 만들고 키 해시·패키지를 넣는다. 네이티브 키는 --local-properties 파일에만 쓴다(출력 안 함).
- 이미 있는 앱·패키지·해시는 건드리지 않는다. 다시 돌려도 중복이 생기지 않는다. --hash 하나만 주면 Play 서명 해시 추가에도 쓴다.
- 로그아웃이면 QR을 텔레그램(RAM_NOTI_TG_TOKEN/CHAT_ID)으로 보내고 265초마다 새 QR을 보낸다. 사람은 카톡 스캔만 한다. --no-qr면 RESULT: LOGGED_OUT으로 끝낸다.
사전 조건: playwright와 chromium headless shell. 비밀번호는 쓰지 않는다(QR 전용). 앱 등록 API가 없어 화면 조작이다.
함정:
- 브라우저를 닫으면 세션 쿠키가 사라져 다시 스캔해야 한다. 그래서 전용 프로필로 띄운 브라우저에 CDP로 붙고, 프로세스는 스크립트가 끝나도 남긴다. --stop일 때만 끈다.
- 로그인 판정은 hostname으로 한다. QR 주소의 continue 파라미터에 developers.kakao.com이 들어 있다.
- 해시 칸에서 Enter를 누르면 폼이 제출된다. 칸 옆 버튼은 '지우기'다. 칸 추가는 button[aria-label="입력 필드 추가"]다.
- 시크릿 재발급은 확인 뒤 키 수정 화면의 '저장'까지 눌러야 안전하다.
"""
import argparse, glob, os, re, socket, subprocess, sys, time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

PORT = 9333
CONSOLE = 'https://developers.kakao.com/console/app'
QR = 'https://accounts.kakao.com/qr_login/?continue=https%3A%2F%2Fdevelopers.kakao.com%2Flogin%3Fcontinue%3D%252Fconsole%252Fapp&lang=ko'
PROFILE = os.path.expanduser('~/.local/share/kakao-console-profile')
HASH = 'input[placeholder="Android 키 해시"]'


def up():
    with socket.socket() as s:
        return s.connect_ex(('127.0.0.1', PORT)) == 0


def start_browser():
    if up():
        return
    os.makedirs(PROFILE, mode=0o700, exist_ok=True)
    os.chmod(PROFILE, 0o700)
    bins = glob.glob(os.path.expanduser('~/Library/Caches/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell'))
    if not bins:
        sys.exit('RESULT: NO_BROWSER (playwright install chromium)')
    subprocess.Popen([sorted(bins)[-1], f'--remote-debugging-port={PORT}', f'--user-data-dir={PROFILE}', '--window-size=1280,1000', 'about:blank'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(40):
        if up():
            return
        time.sleep(.5)
    sys.exit('RESULT: BROWSER_FAILED')


def tg_photo(path, caption):
    e = {}
    for l in open(os.path.expanduser('~/.claude/.env')):
        l = l.strip().removeprefix('export ')
        if '=' in l and not l.startswith('#'):
            k, v = l.split('=', 1); e[k] = v.strip('"\'')
    subprocess.run(['curl', '-s', '-o', '/dev/null', '-F', f"chat_id={e['RAM_NOTI_TG_CHAT_ID']}", '-F', f'photo=@{path}', '-F', f'caption={caption}',
                    f"https://api.telegram.org/bot{e['RAM_NOTI_TG_TOKEN']}/sendPhoto"], check=True)


def ensure_login(p, allow_qr):
    p.goto(CONSOLE, wait_until='networkidle', timeout=60000); time.sleep(2)
    if urlparse(p.url).hostname == 'developers.kakao.com' and '/console' in p.url:
        return
    if not allow_qr:
        print('RESULT: LOGGED_OUT'); sys.exit(3)
    png = '/tmp/kakao_console_qr.png'
    p.goto(QR, wait_until='networkidle', timeout=60000); time.sleep(2)
    try:
        p.get_by_text('로그인 상태 유지').first.click(timeout=4000)
    except Exception:
        pass
    p.screenshot(path=png); tg_photo(png, '카카오 콘솔 로그인 QR'); print('QR sent', flush=True)
    t0 = last = time.time()
    while time.time() - t0 < 1500:
        if urlparse(p.url).hostname == 'developers.kakao.com':
            os.remove(png); time.sleep(3); return
        if time.time() - last > 265:
            p.reload(wait_until='networkidle'); time.sleep(2); p.screenshot(path=png); tg_photo(png, '카카오 콘솔 로그인 QR (새 코드)'); last = time.time()
        p.wait_for_timeout(2000)
    print('RESULT: QR_TIMEOUT'); sys.exit(2)


def find_app(p, name):
    p.goto(CONSOLE, wait_until='networkidle', timeout=60000); time.sleep(1)
    t = p.inner_text('body'); i = t.find(name)
    return re.findall(r'ID (\d+)', t[:i + 1])[-1] if i >= 0 else None


def create_app(p, a):
    p.get_by_text('앱 생성', exact=True).first.click(); time.sleep(2)
    p.fill('input[name=name]', a.name); p.fill('input[name=company]', a.company); p.fill('input[name=representative_domain]', a.domain)
    p.locator('button', has_text='앱 카테고리 정보').first.click(); time.sleep(1)
    p.locator('[role=option],li').filter(has_text=a.category).first.click(); time.sleep(1)
    lab = p.locator('label', has_text='서비스 이용이 제한되는').first; lab.scroll_into_view_if_needed(); lab.click(); time.sleep(1)
    p.locator('button', has_text='저장').last.click(); time.sleep(4)


def open_native(p, aid):
    p.goto(f'{CONSOLE}/{aid}/config/platform-key', wait_until='networkidle', timeout=60000); time.sleep(2)
    p.get_by_text('Default Native AppKey', exact=True).click(); time.sleep(3)


def set_platform(p, aid, a):
    open_native(p, aid); changed = False
    if p.input_value('input[name=package_name]') != a.package:
        p.fill('input[name=package_name]', a.package); changed = True
    for h in a.hash:
        cur = [x.input_value() for x in p.locator(HASH).all()]
        if h in cur:
            continue
        if not [x for x in cur if not x]:
            p.locator('button[aria-label="입력 필드 추가"]').first.click(); time.sleep(1)
        [x for x in p.locator(HASH).all() if not x.input_value()][0].fill(h); time.sleep(.5); changed = True
    if changed:
        p.locator('button', has_text='저장').last.click(); time.sleep(3); open_native(p, aid)
    cur = [x.input_value() for x in p.locator(HASH).all()]
    ok = p.input_value('input[name=package_name]') == a.package and all(h in cur for h in a.hash)
    print('platform', 'changed' if changed else 'already set', 'hashes', len(cur))
    return ok


def save_native_key(p, aid, path):
    p.goto(f'{CONSOLE}/{aid}/config/platform-key', wait_until='networkidle', timeout=60000); time.sleep(2)
    m = p.evaluate("()=>document.querySelector('main').innerText")
    k = re.search(r'네이티브 앱 키[\s\S]*?([0-9a-f]{32})', m).group(1)
    s = open(path).read() if os.path.exists(path) else ''
    if 'KAKAO_NATIVE_APP_KEY=' in s:
        same = f'KAKAO_NATIVE_APP_KEY={k}' in s
        print('local key', 'matches console' if same else 'DIFFERS from console'); return same
    open(path, 'a').write(('' if not s or s.endswith('\n') else '\n') + f'KAKAO_NATIVE_APP_KEY={k}\n'); print('local key saved'); return True


def set_icon(p, aid, icon):
    p.goto(f'{CONSOLE}/{aid}/config', wait_until='networkidle', timeout=60000); time.sleep(2)
    p.locator('main button', has_text='수정').first.click(); time.sleep(2)
    p.locator('input[type=file]').first.set_input_files(icon); time.sleep(3)
    p.locator('button:visible', has_text='저장').last.click(); time.sleep(4); print('icon uploaded')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', required=True); ap.add_argument('--company'); ap.add_argument('--domain'); ap.add_argument('--category', default='건강')
    ap.add_argument('--package', required=True); ap.add_argument('--hash', action='append', default=[])
    ap.add_argument('--local-properties'); ap.add_argument('--icon'); ap.add_argument('--no-qr', action='store_true'); ap.add_argument('--stop', action='store_true')
    a = ap.parse_args()
    start_browser()
    try:
        with sync_playwright() as pw:
            p = pw.chromium.connect_over_cdp(f'http://127.0.0.1:{PORT}').contexts[0].pages[0]; p.set_default_timeout(15000)
            ensure_login(p, not a.no_qr)
            aid = find_app(p, a.name)
            if aid:
                print('app exists', aid)
            else:
                if not (a.company and a.domain):
                    print('RESULT: NEED_COMPANY_DOMAIN'); sys.exit(1)
                create_app(p, a); aid = find_app(p, a.name)
                if not aid:
                    print('RESULT: CREATE_FAILED'); sys.exit(1)
                print('app created', aid)
            ok = set_platform(p, aid, a)
            if a.local_properties:
                ok = save_native_key(p, aid, a.local_properties) and ok
            if a.icon:
                set_icon(p, aid, a.icon)
            print('RESULT:', 'OK' if ok else 'VERIFY_FAILED')
            sys.exit(0 if ok else 1)
    finally:
        if a.stop:
            subprocess.run(['pkill', '-f', f'remote-debugging-port={PORT}'])


if __name__ == '__main__':
    main()
