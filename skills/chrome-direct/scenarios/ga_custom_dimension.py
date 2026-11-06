#!/usr/bin/env python3
"""GA4 맞춤 측정기준 등록 (서비스 계정은 뷰어라 API 403 → GA 화면, Profile 1). LLM 없음.

  ga_custom_dimension.py <계정ID> <속성ID> <param> <표시 이름> [--scope event|user] [--desc 설명]
  예: ga_custom_dimension.py 136249894 559940826 app_platform "앱 플랫폼 사용자" --scope user

- 표시 이름은 문자·숫자·공백·밑줄만(괄호 불가, 11/07 확인).
- 이미 같은 param·범위가 있으면 EXISTS.
마지막 줄: RESULT: CREATED | EXISTS | FAILED <이유>
"""
import argparse, os, sys, time
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

ap = argparse.ArgumentParser()
ap.add_argument('account'); ap.add_argument('prop'); ap.add_argument('param'); ap.add_argument('name')
ap.add_argument('--scope', default='event', choices=['event', 'user']); ap.add_argument('--desc', default='')
a = ap.parse_args()
SC = {'event': '이벤트', 'user': '사용자'}[a.scope]
t = c.new_tab(f'https://analytics.google.com/analytics/web/#/a{a.account}p{a.prop}/admin/customdefinitions/hub', 'Profile 1')
js = lambda b: c.js_json(t, b)
def count():
    return js("const m=document.body.innerText.match(/([0-9]+)개 중/);return m?Number(m[1]):-1")
try:
    time.sleep(12)
    rows = js("return [...document.querySelectorAll('mat-row,tr')].map(r=>r.innerText.replace(/\\s+/g,' '))") or []
    if any(f' {SC} {a.param} ' in f' {r} ' for r in rows):
        print('RESULT: EXISTS'); sys.exit(0)
    before = count()
    js("[...document.querySelectorAll('button')].find(b=>b.innerText.trim()=='맞춤 측정기준 만들기').click();return 1")
    time.sleep(4)
    if a.scope == 'user':
        js("[...document.querySelectorAll('mat-select,[role=combobox]')].find(e=>e.innerText.trim()=='이벤트').click();return 1")
        time.sleep(2)
        js("[...document.querySelectorAll('[role=option],mat-option')].find(o=>o.innerText.trim()=='사용자').click();return 1")
        time.sleep(2)
    vals = [a.name, a.desc or a.param, a.param]
    js("const v=%s;const ins=[...document.querySelectorAll('input')];[2,3,4].forEach((k,n)=>{const i=ins[k];i.focus();i.select();document.execCommand('insertText',false,v[n]);i.blur()});return 1" % repr(vals).replace("'", '"'))
    time.sleep(2)
    if js("const b=[...document.querySelectorAll('button')].find(b=>b.innerText.trim()=='저장');if(b.disabled)return true;b.click();return false"):
        err = js("return [...document.querySelectorAll('mat-error')].map(e=>e.innerText.trim()).join('/')")
        print('RESULT: FAILED 저장 버튼 꺼짐', err); sys.exit(1)
    time.sleep(5)
    after = count()
    print('RESULT:', 'CREATED' if after > before else f'FAILED 개수 그대로 {before}->{after}')
finally:
    c.close_tab(t)
