#!/usr/bin/env python3
"""PlayMCP(playmcp.kakao.com) 개발자 콘솔에 원격 MCP 서버를 등록·심사 요청한다.
- 카카오 전용 headless 프로필(~/.local/share/kakao-console-profile, CDP 9333)을 쓴다. 실제 맥 Chrome은 안 쓴다.
- 왜 화면 조작인가: PlayMCP 등록 API는 공개돼 있지 않다(콘솔 화면만 있음, 2026-11-29).
- 멱등: 콘솔에 같은 MCP 이름이 이미 있으면 새로 등록하지 않고 상태만 출력한다.
- draft·submit은 --submit 이 있어야 실제로 누른다(없으면 fill과 같음).
- 처음 쓰는 계정은 PlayMCP 필수 약관 동의·닉네임 기본값으로 가입한다.
python3 playmcp_register.py status [이름]          콘솔 내 MCP 목록·심사 상태(LLM 없음)
  출력: STATUS name=… review=심사 중|반려|게시|… online=… tools=N  + DOING <카드 doing 한 줄>
  반려면 콘솔 상세의 사유 글을 REASON 줄로 출력한다.
python3 playmcp_register.py fill   spec.json        양식을 채우고 '정보 불러오기'까지(저장 안 함)
python3 playmcp_register.py draft  spec.json --submit  채운 뒤 '임시 등록'
python3 playmcp_register.py submit spec.json --submit  채운 뒤 '등록 및 심사 요청'
spec.json: {image, name, ident, description, examples[3], endpoint}
로그아웃이면 카카오 QR 로그인 먼저(예: 2026-12_카카오BeMyAgent/work/kakao/console.py qr — QR은 알림 봇으로 감).
"""
import json, sys, time
import glob, os, socket, subprocess
from playwright.sync_api import sync_playwright
PORT = 9333
PROFILE = os.path.expanduser('~/.local/share/kakao-console-profile')

def page(pw):
    with socket.socket() as so:
        up = so.connect_ex(('127.0.0.1', PORT)) == 0
    if not up:
        b = sorted(glob.glob(os.path.expanduser('~/Library/Caches/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell')))[-1]
        subprocess.Popen([b, f'--remote-debugging-port={PORT}', f'--user-data-dir={PROFILE}', '--window-size=1280,1000', '--lang=ko-KR', 'about:blank'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        time.sleep(5)
    return pw.chromium.connect_over_cdp(f'http://127.0.0.1:{PORT}').contexts[0].pages[0]
CONSOLE = 'https://playmcp.kakao.com/console'
SHOT = '/private/tmp/playmcp-register.png'

def open_console(p):
    p.goto(CONSOLE, wait_until='networkidle', timeout=60000); time.sleep(2)
    if '/signup' in p.url:  # 첫 방문: 필수 약관 동의 + 닉네임 기본값
        p.locator('#agree1').check(force=True); time.sleep(.5)
        p.get_by_role('button', name='시작하기').click(); time.sleep(4)
        p.goto(CONSOLE, wait_until='networkidle', timeout=60000); time.sleep(2)
    if 'playmcp.kakao.com/console' not in p.url:
        sys.exit('RESULT: LOGGED_OUT ' + p.url)

def pick(p, current, option):
    p.locator('button', has_text=current).filter(has_text='옵션 더보기').first.click(); time.sleep(.5)
    p.locator('button', has_text=option).last.click(); time.sleep(.5)

def fill(p, s):
    p.get_by_text('새로운 MCP 서버 등록').first.click(); time.sleep(3)
    p.set_input_files('#btnUpload', s['image']); time.sleep(2)
    p.get_by_placeholder('이름을 입력하세요').fill(s['name'])
    p.get_by_placeholder('MCP를 나타낼 수 있는 식별자로 입력하세요.').fill(s['ident'])
    p.get_by_role('button', name='유효성 확인').click(); time.sleep(2)
    p.locator('#description').fill(s['description'])
    ex = p.get_by_placeholder('대화 예시를 입력하세요')
    for i, e in enumerate(s['examples'][:3]): ex.nth(i).fill(e)
    p.get_by_placeholder('MCP Endpoint를 입력하세요 (https:// 또는 http:// 가능)').fill(s['endpoint'])
    p.get_by_role('button', name='정보 불러오기').click(); time.sleep(6)

REVIEW_WORDS = ('심사 중', '심사중', '반려', '승인', '게시', '공개', '임시 등록', '심사 요청', '비공개')

def parse_status(p, main, want=None):
    """콘솔 목록 글에서 MCP 이름 뒤 상태 칸을 읽는다(화면 글 기준, 2026-11-29 모양)."""
    L = [l.strip() for l in main.splitlines() if l.strip()]
    i0 = L.index('새로운 MCP 서버 등록') + 1 if '새로운 MCP 서버 등록' in L else 0
    rows, i = [], i0
    while i < len(L):
        name = L[i]
        if want and want not in name: i += 1; continue
        nxt = L[i + 1] if i + 1 < len(L) else ''
        if any(w in nxt for w in REVIEW_WORDS):
            r = {'name': name, 'review': nxt}
            blk = L[i:i + 25]
            for k, key in (('MCP 상태', 'online'), ('Tools', 'tools'), ('Tool call', 'calls')):
                if k in blk: r[key] = blk[blk.index(k) + 1]
            rows.append(r); i += 2; continue
        i += 1
    for k in ('등록된 MCP', '임시 등록된 MCP'):
        for l in L:
            if l.startswith(k + ' '): print('COUNT', l)
    if not rows:
        print('RESULT: STATUS_UNKNOWN (목록 모양이 바뀜 — SHOT 확인)'); p.screenshot(path=SHOT, full_page=True); print('SHOT', SHOT); return
    ts = time.strftime('%m/%d %H:%M')
    for r in rows:
        print('STATUS', ' '.join(f'{k}={v}' for k, v in r.items()))
        if '반려' in r['review']:
            try:
                p.get_by_text(r['name']).first.click(); time.sleep(3)
                t = p.inner_text('main')
                j = t.find('반려')
                print('REASON', ' '.join(t[j:j + 600].split()))
            except Exception as e:
                print('REASON 읽기 실패', e)
        print('DOING', f"PlayMCP {r['review']} — {r.get('online', '?')} · 도구 {r.get('tools', '?')}개 ({ts} 콘솔)")
    print('RESULT: STATUS ' + rows[0]['review'])

def report(p):
    t = p.inner_text('body')
    i = max(t.rfind('새로운 MCP 서버 등록'), 0)
    print(t[i:i + 6000])
    p.screenshot(path=SHOT, full_page=True); print('SHOT', SHOT)

if __name__ == '__main__':
    cmd = sys.argv[1]
    with sync_playwright() as pw:
        p = page(pw); p.set_default_timeout(20000)
        open_console(p)
        main = p.inner_text('main')
        if cmd == 'status':
            print(main[:3000]); parse_status(p, main, sys.argv[2] if len(sys.argv) > 2 else None); sys.exit()
        s = json.load(open(sys.argv[2], encoding='utf-8'))
        if cmd != 'fill' and s['name'] in main:
            print(main[:2000]); print('RESULT: ALREADY_REGISTERED'); sys.exit()
        fill(p, s)
        if cmd == 'fill' or '--submit' not in sys.argv:
            report(p); print('RESULT: FILLED (저장 안 함)'); sys.exit()
        btn = {'draft': '임시 등록', 'submit': '등록 및 심사 요청'}[cmd]
        p.get_by_role('button', name=btn).click(); time.sleep(3)
        for b in ('확인', '요청', '등록'):
            d = p.locator('[role=dialog] button, .layer_popup button', has_text=b)
            if d.count(): d.last.click(); time.sleep(3); break
        report(p)
        p.goto(CONSOLE, wait_until='networkidle', timeout=60000); time.sleep(2)
        print('---- 콘솔'); m = p.inner_text('main'); print(m[:2000])
        print('RESULT: ' + ('SUBMITTED' if '심사 중' in m else 'CHECK_SCREEN'))
