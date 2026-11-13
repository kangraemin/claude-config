"""LINE Creators Market 송금 정보에 PayPal 계정을 연결한다.
사용: line_paypal_connect.py [--creator jYmx33PVwLeD4n3m] [--profile 'Profile 1'] [--submit]

- creator.line.me/my/<id>/seller/update_account → 'Connect with PayPal' → PayPal 로그인(PAYPAL_PW, ~/.claude/sns.env) → Agree and Connect.
- 이미 Full name·PayPal 이메일이 채워져 있으면 아무것도 안 하고 RESULT: ALREADY.
- --submit 없으면 연결 버튼 직전까지만 보고 끝(dry-run).
- 왜 화면 조작인가: LINE·PayPal 모두 공개 API가 없다. PayPal은 합성 입력을 무시해 rclick·rtype(실제 입력)을 쓴다.
- 함정(2026-11-13):
  - PayPal 이메일이 미확인이면 연결 화면이 막힌다 → 확인 메일 링크로 로그인부터.
  - 로그인 뒤 패스키 권유 화면 + macOS '패스키를 추가하겠습니까?' 창 → 취소, 저장 위치 창도 취소, 그다음 #optIn_skip JS click.
  - 오래 열어 둔 동의 화면에서 Agree를 누르면 LINE이 'Bad Request' → update_account에서 다시 시작.
  - 연결되면 LINE이 바로 저장한다(Save 버튼은 disabled로 남는다).
  - 송금은 엔화(JPY) 수령 가능해야 한다. 개인 계정은 별도 차단 설정 없음.
검증: 2026-11-13 손으로 같은 순서 연결 성공(KANG RAEMIN / remin1994@gmail.com), 스크립트는 ALREADY 경로 실행.
"""
import argparse, os, sys, time
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

ap = argparse.ArgumentParser()
ap.add_argument('--creator', default='jYmx33PVwLeD4n3m')
ap.add_argument('--profile', default='Profile 1')
ap.add_argument('--submit', action='store_true')
a = ap.parse_args()


def load_pw():
    for line in open(os.path.expanduser('~/.claude/sns.env')):
        if line.startswith('PAYPAL_PW='):
            os.environ['PAYPAL_PW'] = line.split('=', 1)[1].strip()
            return
    raise SystemExit('PAYPAL_PW 없음')


def tag_click(t, js_find, name):
    if not c.js_json(t, f"var e=(function(){{return {js_find}}})();if(!e)return false;e.removeAttribute('target');e.scrollIntoView({{block:'center'}});e.setAttribute('data-x','{name}');return true"):
        return False
    c.shot(t, '/tmp/line_pp.png')
    c.rclick(t, sel=f'[data-x={name}]')
    return True


def body(t):
    return c.js_json(t, 'return document.body.innerText') or ''


def connected(h):
    i = h.find('Full name')
    seg = h[i:i + 120] if i >= 0 else ''
    return '@' in seg and 'has not been registered' not in h


BTN = "[...document.querySelectorAll('button')].find(b=>b.innerText.trim()=='%s')"
t = c.new_tab(f'https://creator.line.me/my/{a.creator}/seller/update_account', profile=a.profile)
status = 'FAIL'
try:
    time.sleep(7)
    h = body(t)
    if connected(h):
        i = h.find('Full name'); print(h[i:i + 90].replace('\n', ' '))
        status = 'ALREADY'
    elif not a.submit:
        status = 'DRY_RUN 미연결'
    else:
        load_pw()
        tag_click(t, "[...document.querySelectorAll('a')].find(a=>a.href.includes('paypal.com/connect'))", 'ppc')
        time.sleep(10)
        for _ in range(4):
            h = body(t)
            if 'creator.line.me' in (c.js_json(t, 'return location.href') or ''):
                break
            if c.js_json(t, "return !!document.querySelector('input[type=password]')"):
                import subprocess
                tag_click(t, "document.querySelector('input[type=password]')", 'pw'); time.sleep(0.4)
                subprocess.run(['cliclick', 'kd:cmd', 't:a', 'ku:cmd', 'kp:delete'])
                c.rtype(env='PAYPAL_PW'); time.sleep(0.8)
                tag_click(t, BTN % 'Log In', 'lg')
            elif 'Agree and Connect' in h:
                tag_click(t, BTN % 'Agree and Connect', 'agc')
            elif 'Continue' in h:
                tag_click(t, BTN % 'Continue', 'cnt')
            time.sleep(10)
        c.js_json(t, f"location.href='https://creator.line.me/my/{a.creator}/seller/update_account';return 1"); time.sleep(7)
        status = 'OK' if connected(body(t)) else 'FAIL 연결 확인 안 됨'
finally:
    try: c.close_tab(t)
    except Exception: pass
    print('RESULT:', status)
