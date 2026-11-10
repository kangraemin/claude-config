#!/usr/bin/env python3
"""토스 비즈니스(앱인토스 콘솔) 휴대폰 로그인 — Codex 없이 chromectl로.
사용: toss_business_login.py send   → 인증 문자 요청까지 (RESULT: SMS_SENT | ALREADY)
      toss_business_login.py code 123456 → 인증번호 입력 + remin1994 계정 선택 (RESULT: LOGGED_IN)
사람 몫: 폰에 온 6자리 하나. 입력 시간 2분.
왜 화면 조작: 토스 비즈니스 로그인은 API가 없다. toss_business_login.sh는 Codex를 써서 한도(11/15) 때 막혔다(2026-11-10).
함정: 통신사 드롭다운·계정 목록은 .click()이 아니라 pointerdown~click 이벤트를 쏴야 열린다.
개인정보는 제천 build_application.py INFO(dict: 5=생년월일, 9=전화)에서 읽고 출력하지 않는다.
"""
import ast, json, os, re, sys, time
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

INFO_PY = '/Users/ram/programming/vibecoding/공모전/2026-10_제천AI데이터분석/submission/build_application.py'
STATE = '/tmp/toss-login-tab'
PRESS = "for(const ty of ['pointerdown','mousedown','pointerup','mouseup','click'])tgt.dispatchEvent(new MouseEvent(ty,{bubbles:true}));"
SETV = "const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;"


def info():
    src = open(INFO_PY).read()
    s = src.index('INFO = {'); e = src.index('\n}', s)
    d = ast.literal_eval(src[s + 7:e + 2].replace('TITLE', 'None'))
    birth = re.sub(r'\D', '', str(d[5])); phone = re.sub(r'\D', '', str(d[9]))
    return str(d[3]), phone, birth[-6:]


def press_text(t, text, sel='*'):
    return c.run_js(t, f"(()=>{{const el=[...document.querySelectorAll('{sel}')].filter(e=>e.children.length==0&&e.textContent.trim()==={json.dumps(text)}).pop();if(!el)return 'NF';const tgt=el.closest('button,a,li,[role=button],[role=option]')||el;{PRESS}return 'ok'}})()")


def send():
    t = c.new_tab('https://apps-in-toss.toss.im/workspace', profile='Profile 1'); time.sleep(7)
    open(STATE, 'w').write(t)
    if '/workspace/' in c.run_js(t, 'location.href'):
        print('RESULT: ALREADY'); return
    c.run_js(t, "[...document.querySelectorAll('a,button')].find(b=>b.innerText.trim()==='휴대폰 번호 로그인').click(),1"); time.sleep(4)
    name, phone, birth = info()
    vals = json.dumps([name, phone, None, birth, '1'])
    c.run_js(t, f"(()=>{{const v={vals};{SETV}[...document.querySelectorAll('input')].forEach((i,k)=>{{if(v[k]==null)return;i.focus();set.call(i,v[k]);i.dispatchEvent(new Event('input',{{bubbles:true}}));i.dispatchEvent(new Event('change',{{bubbles:true}}));i.blur()}});return 1}})()")
    time.sleep(1)
    c.run_js(t, "[...document.querySelectorAll('button')].find(b=>b.innerText.includes('본인 인증하기')).click(),1"); time.sleep(5)
    press_text(t, '통신사를 선택해 주세요.'); time.sleep(2)
    press_text(t, 'SKT 알뜰폰', 'div'); time.sleep(2)
    c.run_js(t, "[...document.querySelectorAll('button')].find(b=>b.innerText.trim()==='다음').click(),1"); time.sleep(5)
    ok = '인증번호를 입력' in c.run_js(t, 'document.body.innerText')
    print('RESULT:', 'SMS_SENT' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


def code(n):
    t = open(STATE).read().strip()
    c.run_js(t, f"(()=>{{const i=document.querySelector('input');{SETV}i.focus();set.call(i,'{n}');i.dispatchEvent(new Event('input',{{bubbles:true}}));setTimeout(()=>[...document.querySelectorAll('button')].find(b=>b.innerText.trim()==='인증하기').click(),300);return 1}})()")
    time.sleep(7)
    if 'select-account' in c.run_js(t, 'location.href'):
        press_text(t, 'remin1994@gmail.com'); time.sleep(8)
    ok = '/workspace/' in c.run_js(t, 'location.href')
    print('RESULT:', 'LOGGED_IN' if ok else 'FAILED')  # 탭은 남긴다: ait_app_register.py push가 콘솔 탭을 쓴다
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['send']: send()
    elif a[:1] == ['code'] and len(a) == 2 and re.fullmatch(r'\d{6}', a[1]): code(a[1])
    else: print(__doc__); sys.exit(2)
