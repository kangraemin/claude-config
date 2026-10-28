#!/usr/bin/env python3
"""토스 비즈니스(앱인토스 콘솔) 휴대폰 로그인 — chromectl 탭 id로 실제 Chrome(Profile 1) 조작. LLM 없음.

  toss_business_login.py send          → 로그인 탭 열기·본인정보·통신사(SKT 알뜰폰)·전체 동의·문자 요청. SMS_SENT
  toss_business_login.py code 123456   → 같은 탭에 인증번호 입력·계정 선택. LOGGED_IN
  toss_business_login.py resend        → 인증번호 다시 받기

toss_business_login_js.sh와 같은 순서인데, 그 스크립트는 'window 1' 인덱스(-1719)에 깨져 로그인 안 된 상태를
ALREADY_LOGGED_IN으로 잘못 끝냈다(10/28). 여기서는 new_tab이 준 id로만 탭을 다룬다. 탭 id는 /tmp/toss-login/tab 에 둔다.
개인정보 값은 제천 build_application.py INFO(5=생년월일, 9=전화)에서 읽고 출력하지 않는다.
사람 몫은 폰에 온 6자리를 알려 주는 것 하나(유효 2분). 문자는 한 번만 요청한다.
마지막 줄: RESULT: SMS_SENT | ALREADY | LOGGED_IN | FAILED <화면 글자>
"""
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c  # noqa: E402

INFO_PY = '/Users/ram/programming/vibecoding/공모전/2026-10_제천AI데이터분석/submission/build_application.py'
URL = 'https://apps-in-toss.toss.im/workspace/35273'
TAB = Path('/tmp/toss-login/tab')
FIRE = ("const fire=t=>['pointerdown','mousedown','pointerup','mouseup','click'].forEach(k=>t.dispatchEvent("
        "new (k.startsWith('pointer')?PointerEvent:MouseEvent)(k,{bubbles:true})));")


def js(t, body):
    return c.js_json(t, body)


def text(t):
    return js(t, "return document.body ? document.body.innerText.slice(0, 300) : ''") or ''


def href(t):
    return js(t, 'return location.href') or ''


def send():
    t = c.new_tab(URL, 'Profile 1')
    TAB.parent.mkdir(parents=True, exist_ok=True)
    TAB.write_text(t)
    time.sleep(6)
    if 'apps-in-toss.toss.im/workspace' in href(t):
        c.close_tab(t)
        return 'ALREADY'
    js(t, FIRE + "const b=[...document.querySelectorAll('button,a')].find(b=>/휴대폰 ?번호 로그인/.test(b.innerText.trim()));b&&fire(b);return 1")
    time.sleep(3)
    src = open(INFO_PY).read()
    info = {int(k): v for k, v in re.findall(r'(\d+):\s*"([^"]*)"', src)}
    b = re.sub(r'\D', '', info[5]); b = b[2:] if len(b) == 8 else b
    vals = json.dumps(['강래민', re.sub(r'\D', '', info[9]), None, b, '1'])
    js(t, "const set=(i,v)=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,v);"
          "i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}));};"
          f"const ins=[...document.querySelectorAll('input')];{vals}.forEach((x,k)=>{{if(x!==null&&ins[k])set(ins[k],x)}});"
          "const s=document.querySelector('button[type=submit]');s&&s.click();return 1")
    time.sleep(4)
    js(t, FIRE + "const b=[...document.querySelectorAll('button')].find(b=>/통신사를 선택/.test(b.innerText));b&&fire(b);return 1")
    time.sleep(2)
    js(t, FIRE + "const e=[...document.querySelectorAll('div,li,button')].find(e=>e.children.length==0&&e.innerText.trim()=='SKT 알뜰폰');e&&fire(e);return 1")
    time.sleep(2)
    # 전체 동의는 pointer 이벤트로는 안 켜지고 .click()만 먹는다(10/28)
    js(t, "const e=[...document.querySelectorAll('[role=button]')].find(e=>/^전체 동의/.test(e.innerText.trim()));e&&e.click();return 1")
    time.sleep(1)
    js(t, FIRE + "const b=[...document.querySelectorAll('button')].find(b=>b.innerText.trim()=='다음');b&&fire(b);return 1")
    time.sleep(5)
    tx = text(t)
    return 'SMS_SENT' if '인증번호를 입력' in tx else 'FAILED ' + tx[:120].replace('\n', ' / ')


def code(n):
    t = TAB.read_text().strip()
    js(t, "const i=document.querySelector('input');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,"
          f"'{n}');i.dispatchEvent(new Event('input',{{bubbles:true}}));" + FIRE +
          "setTimeout(()=>{const b=[...document.querySelectorAll('button')].find(b=>b.innerText.trim()=='인증하기');b&&fire(b)},300);return 1")
    time.sleep(7)
    js(t, FIRE + "const e=[...document.querySelectorAll('*')].find(e=>e.children.length==0&&/remin1994@gmail.com/.test(e.innerText||''));"
          "e&&fire(e.closest('button,[role=button],li')||e);return 1")
    time.sleep(6)
    if 'apps-in-toss.toss.im/workspace' in href(t):
        c.close_tab(t)
        return 'LOGGED_IN'
    return 'FAILED ' + text(t)[:120].replace('\n', ' / ')


def main():
    cmd = sys.argv[1:2]
    if cmd == ['send']:
        r = send()
    elif cmd == ['code'] and re.fullmatch(r'\d{6}', (sys.argv[2:3] or [''])[0]):
        r = code(sys.argv[2])
    elif cmd == ['resend']:
        js(TAB.read_text().strip(), FIRE + "const b=[...document.querySelectorAll('button')].find(b=>/다시 받기/.test(b.innerText));b&&fire(b);return 1")
        r = 'RESENT'
    else:
        print(__doc__); sys.exit(2)
    print('RESULT:', r)
    sys.exit(0 if not r.startswith('FAILED') else 1)


if __name__ == '__main__':
    main()
