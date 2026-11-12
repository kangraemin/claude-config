"""클라우드 루틴 환경 네트워크 허용 목록에 도메인을 더한다.
사용: claude_env_allow_domain.py mukmap.kr [*.mukmap.kr ...] [--env Default] [--submit]

- claude.ai 설정 → Claude Code → 클라우드 환경 → <env> 편집 → 네트워크 액세스 → 허용된 도메인.
- 이미 다 들어 있으면 아무것도 안 바꾸고 RESULT: ALREADY.
- --submit 없으면 칸만 채워 보고 취소(dry-run).
- 왜 화면 조작인가: 환경 네트워크 설정은 RemoteTrigger API에 없다(environment_id만 받음).
- 함정: 이 화면은 합성 click을 무시한다 → rclick(실제 마우스). 팝오버 메뉴는 JS가 돌면 닫힌다.
검증: 2026-11-12 Default에 mukmap.kr·*.mukmap.kr 손으로 같은 순서로 저장('환경 업데이트됨'), 스크립트는 ALREADY 경로로 실행.
"""
import argparse, os, sys, time
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

ap = argparse.ArgumentParser()
ap.add_argument('domains', nargs='+')
ap.add_argument('--env', default='Default')
ap.add_argument('--profile', default='Profile 1')
ap.add_argument('--submit', action='store_true')
a = ap.parse_args()

DLG = "var d=[...document.querySelectorAll('[role=dialog]')].pop();"


def tag(selector_js, name):
    """selector_js: 요소 하나를 돌려주는 JS 식 또는 return 문. 찾으면 data-x=name을 붙인다."""
    body = selector_js if 'return' in selector_js else 'return ' + selector_js
    return c.js_json(t, f"var e=(function(){{{body}}})(); if(!e) return false; e.setAttribute('data-x','{name}'); return true;")


def wait(cond_js, sec=20):
    end = time.time() + sec
    while time.time() < end:
        if c.js_json(t, cond_js):
            return True
        time.sleep(1)
    return False


t = c.new_tab('https://claude.ai/new#settings/claude-code', profile=a.profile)
status = 'FAIL'
try:
    if not wait("return document.body.innerText.includes('클라우드 환경')", 30):
        raise SystemExit('클라우드 환경 칸이 안 보임(로그인 확인)')
    if not tag(f"document.querySelector('[aria-label=\"{a.env}에 대한 작업\"]')", 'envmenu'):
        raise SystemExit(f'환경 {a.env} 없음')
    c.rclick(t, sel='[data-x=envmenu]'); time.sleep(1.5)
    tag("[...document.querySelectorAll('[role=menuitem]')].find(m=>m.innerText.trim()=='편집')", 'edit')
    c.rclick(t, sel='[data-x=edit]'); time.sleep(2)
    if not tag(DLG + "return d && [...d.querySelectorAll('button')].find(b=>b.innerText.trim().startsWith('네트워크 액세스'))", 'net'):
        raise SystemExit('편집 창에 네트워크 액세스 버튼 없음')
    c.rclick(t, sel='[data-x=net]'); time.sleep(1.5)
    cur = c.js_json(t, DLG + "var x=d&&d.querySelector('textarea'); return x?x.value:null")
    if cur is None:
        raise SystemExit('허용된 도메인 칸 없음(접근 수준이 제한됨이 아닐 수 있음)')
    have = [l.strip() for l in cur.splitlines() if l.strip()]
    add = [d for d in a.domains if d not in have]
    print('현재:', have)
    if not add:
        status = 'ALREADY'
    else:
        new = '\n'.join(have + add)
        c.js_json(t, DLG + "var x=d.querySelector('textarea');"
                  "Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(x," + c.q(new) + ");"
                  "x.dispatchEvent(new Event('input',{bubbles:true}));return true")
        print('추가:', add)
        if a.submit:
            tag(DLG + "return [...d.querySelectorAll('button')].find(b=>b.innerText.trim()=='변경사항 저장')", 'save')
            c.rclick(t, sel='[data-x=save]')
            status = 'OK' if wait("return document.body.innerText.includes('환경 업데이트됨')", 15) else 'FAIL 저장 확인 안 됨'
        else:
            status = 'DRY_RUN'
finally:
    try:
        c.close_tab(t)
    except Exception:
        pass
    print('RESULT:', status)
