"""앱인토스 콘솔 워크스페이스 멤버 목록·초대·삭제.

사용: python3 ait_member.py list
      python3 ait_member.py invite <email> [--role 관리자|구성원] [--submit]
      python3 ait_member.py remove <email> [--submit]
- 콘솔 /workspace/<ws>/member 화면 조작(MCP에 멤버 초대·삭제 도구가 없음).
- 초대: 초대하기 → 이메일 → 권한 콤보(option에 pointer 이벤트+click) → 앱 권한은 기본 전체 → 초대하기.
- 삭제: 행에 hover 이벤트를 줘야 '삭제' 버튼이 생김 → 확인창 '삭제하기'.
- 멱등: 이미 있으면 초대 안 함, 없으면 삭제 안 함. --submit 없으면 dry-run.
- 사전 조건: 콘솔 로그인된 창(ait_app_register.console_tab).
검증 2026-11-06: dumdi.works@gmail.com 관리자 초대, handnew04@gmail.com 삭제(손으로 같은 순서).
"""
import sys, os, time, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

def console_tab(u):
    """이미 콘솔 workspace 탭이 있는 창에 새 탭을 연다(로그인 상태 유지)."""
    before = {r[4] for r in c.tabs(with_id=True)}
    r = c.jxa("var ws=C.windows(); for (var i=0;i<ws.length;i++){var ts=ws[i].tabs(); for(var j=0;j<ts.length;j++){"
              "if(String(ts[j].url()).indexOf('apps-in-toss.toss.im/workspace/')>=0){ ws[i].tabs.push(C.Tab({url:%s})); return 'ok';}}} return 'none';" % c.q(u))
    if r != 'ok':
        sys.exit('RESULT: LOGIN_REQUIRED 콘솔 탭이 열린 창이 없음 — toss_business_login.sh')
    for _ in range(15):
        time.sleep(1)
        new = [x for x in c.tabs(with_id=True) if x[4] not in before]
        if new:
            t = 'id:' + new[-1][4]
            c.jxa("var ws=C.windows(); for (var i=0;i<ws.length;i++){var ts=ws[i].tabs(); for(var j=0;j<ts.length;j++){ if(ts[j].id()==%s){ws[i].activeTabIndex=j+1; return 1}}}" % new[-1][4])
            time.sleep(5)
            return t
    sys.exit('RESULT: ERROR 탭이 안 열림')

WS = os.environ.get('AIT_WORKSPACE', '35273')

def rows(t):
    return c.js_json(t, "return [...document.querySelectorAll('main li')].map(l=>l.innerText.replace(/\\s+/g,' ').trim())") or []

ap = argparse.ArgumentParser()
ap.add_argument('cmd', choices=['list', 'invite', 'remove'])
ap.add_argument('email', nargs='?')
ap.add_argument('--role', default='관리자')
ap.add_argument('--submit', action='store_true')
a = ap.parse_args()

t = console_tab(f'https://apps-in-toss.toss.im/workspace/{WS}/member')
try:
    time.sleep(2)
    r = rows(t)
    print('\n'.join(r))
    has = a.email and any(a.email in x for x in r)
    if a.cmd == 'list':
        print('RESULT: OK', len(r)); sys.exit()
    if a.cmd == 'invite':
        if has: print('RESULT: EXISTS', a.email); sys.exit()
        if not a.submit: print('RESULT: DRY_RUN invite', a.email, a.role); sys.exit()
        E = json.dumps(a.email); R = json.dumps(a.role)
        c.js_json(t, "[...document.querySelectorAll('button')].find(x=>x.innerText.trim()=='초대하기').click();return 1")
        time.sleep(2)
        c.js_json(t, "var d=document.querySelector('[role=dialog]');var i=d.querySelector('input');var s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;s.call(i,%s);i.dispatchEvent(new Event('input',{bubbles:true}));"
                     "var cb=d.querySelector('[role=combobox]');['pointerdown','mousedown','mouseup','click'].forEach(ev=>cb.dispatchEvent(new MouseEvent(ev,{bubbles:true})));return 1" % E)
        time.sleep(1.2)
        c.js_json(t, "var o=[...document.querySelectorAll('[role=option]')].find(e=>e.innerText.trim().startsWith(%s));var r=o.getBoundingClientRect();var p={bubbles:true,clientX:r.x+20,clientY:r.y+10,pointerId:1,isPrimary:true};"
                     "o.dispatchEvent(new PointerEvent('pointerdown',p));o.dispatchEvent(new MouseEvent('mousedown',p));o.dispatchEvent(new PointerEvent('pointerup',p));o.dispatchEvent(new MouseEvent('mouseup',p));o.click();return 1" % R)
        time.sleep(1)
        role = c.js_json(t, "return document.querySelector('[role=dialog] [role=combobox]').innerText.trim()")
        if role != a.role: print('RESULT: FAIL 권한 선택 안 됨', role); sys.exit(1)
        c.js_json(t, "var d=document.querySelector('[role=dialog]');[...d.querySelectorAll('button')].find(b=>b.innerText.trim()=='초대하기').click();return 1")
    else:
        if not has: print('RESULT: ABSENT', a.email); sys.exit()
        if not a.submit: print('RESULT: DRY_RUN remove', a.email); sys.exit()
        E = json.dumps(a.email)
        c.js_json(t, "var li=[...document.querySelectorAll('main li')].find(x=>x.innerText.includes(%s));['pointerover','pointerenter','mouseover','mouseenter','mousemove'].forEach(ev=>li.dispatchEvent(new MouseEvent(ev,{bubbles:true})));"
                     "[...li.querySelectorAll('button,[role=button]')].find(b=>(b.getAttribute('aria-label')||b.innerText)=='삭제').click();return 1" % E)
        time.sleep(1.5)
        c.js_json(t, "var d=document.querySelector('[role=dialog],[role=alertdialog]');[...d.querySelectorAll('button')].find(b=>b.innerText.trim()=='삭제하기').click();return 1")
    time.sleep(2.5)
    r = rows(t); ok = any(a.email in x for x in r) == (a.cmd == 'invite')
    print('\n'.join(r)); print('RESULT:', 'OK' if ok else 'FAIL', a.cmd, a.email)
finally:
    c.close_tab(t)
