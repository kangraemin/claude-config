"""다음(Daum) 웹마스터도구 등록 — 실제 Chrome 'Profile 1'을 chromectl로 조작(카카오 로그인 불필요).
  python3 daum_register.py pin    https://site         → PIN 발급(없으면 만들어 ~/.claude/.env DAUM_PIN_<HOST>에 저장) → robots.txt에 넣을 줄 출력
  python3 daum_register.py verify https://site [sitemap.xml] [URL ...] → PIN 인증 → 사이트맵 Seed 등록 → URL별 문서 수집 요청
사전 조건: verify 전에 pin이 출력한 '#DaumWebMasterTool:…' 줄을 사이트 루트 robots.txt 하단에 넣고 배포.
하위 경로 사이트(user.github.io/repo)는 루트 robots.txt를 못 고치면 등록 불가.
화면 조작인 이유: 공개 API가 없다. 이용동의 체크박스는 누르면 /agree로 이동했다가 sessionStorage로 돌아오는 구조라
label.choice_agree에 'checked' 클래스를 직접 붙이고 .btn_register를 누른다(2026-10-23 oguriworks.com 성공)."""
import os, re, secrets, string, sys, time
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

ENV = os.path.expanduser('~/.claude/.env')
W = 'https://webmaster.daum.net'
cmd, site = sys.argv[1], sys.argv[2].rstrip('/')
host = re.sub(r'^https?://', '', site).split('/')[0]
KEY = 'DAUM_PIN_' + re.sub(r'[^A-Z0-9]', '_', host.upper())


def pin_value(create):
    for l in open(ENV):
        if l.startswith(KEY + '='):
            return l.split('=', 1)[1].strip()
    if not create:
        sys.exit(f'RESULT: NO_PIN {KEY} 없음 — 먼저 pin')
    a = string.ascii_lowercase + string.digits
    p = 'o' + ''.join(secrets.choice(a) for _ in range(9)) + '7'
    with open(ENV, 'a') as f:
        f.write(f'\n{KEY}={p}\n')
    return p


def body(t):
    return c.js_json(t, 'return document.body.innerText')


t = c.new_tab(W + '/join', profile='Profile 1')
try:
    time.sleep(5)
    if cmd == 'pin':
        pin = pin_value(True)
        c.fill(t, '#authSiteUrl', site); c.fill(t, '#authPinCode', pin); c.fill(t, '#authPinCheck', pin)
        c.js_json(t, "document.querySelector('.layer_agree')?.classList.add('hide'); document.querySelector('.choice_agree').classList.add('checked'); setTimeout(()=>document.querySelector('.btn_register').click(),10); return 1")
        time.sleep(6)
        m = re.search(r'#DaumWebMasterTool:\S+', body(t))
        if not m:
            print(body(t)[:500]); sys.exit('RESULT: FAIL PIN 발급 화면 아님')
        print(m.group(0))
        print('RESULT: PIN_ISSUED robots.txt 하단에 위 줄을 넣고 배포한 뒤 verify')
    elif cmd == 'verify':
        pin = pin_value(False)
        c.goto(t, W + '/'); time.sleep(5)
        # 이미 인증된 세션이면 루트가 대시보드로 간다. 다른 사이트 대시보드면 '서비스 이용 종료'로 나간 뒤 다시 인증
        if '/dashboard' in c.js_json(t, 'return location.href') and host not in body(t):
            c.press(t, text='서비스 이용 종료'); time.sleep(4); c.goto(t, W + '/'); time.sleep(5)
        if '/dashboard' not in c.js_json(t, 'return location.href'):
            c.fill(t, 'input[type=text]', site); c.fill(t, 'input[type=password]', pin)
            c.js_json(t, "const b=[...document.querySelectorAll('button,a')].find(e=>e.innerText.trim()==='인증하기');setTimeout(()=>b.click(),10);return 1")
            time.sleep(7)
        if '/dashboard' not in c.js_json(t, 'return location.href'):
            print(body(t)[:500]); sys.exit('RESULT: FAIL 인증 안 됨(robots.txt 줄 배포 확인)')
        print('VERIFIED', site)
        rest = sys.argv[3:]
        sm = rest[0] if rest and rest[0].endswith('.xml') else None
        urls = rest[1:] if sm else rest
        jobs = ([('collectSiteSeedUrl', sm if sm.startswith('http') else f'{site}/{sm}', 2)] if sm else []) + [('collectReqUrl', u, 0) for u in urls]
        for inp, u, idx in jobs:
            c.goto(t, W + '/tool/collect'); time.sleep(4)
            c.fill(t, '#' + inp, u)
            c.js_json(t, f"const b=[...document.querySelectorAll('button')].filter(e=>e.innerText.trim()==='수집요청')[{idx}];setTimeout(()=>b.click(),10);return 1")
            time.sleep(5)
            print('RESULT', u, '요청됨' if '수집요청이 완료' in body(t) else '확인 안 됨')
        print(f'RESULT: OK {site} 인증 + 요청 {len(jobs)}건')
finally:
    c.close_tab(t)
