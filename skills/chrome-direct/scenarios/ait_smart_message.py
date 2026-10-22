#!/usr/bin/env python3
"""[제출] 앱인토스 콘솔 푸시알림(스마트 발송) — 기능성 캠페인 목록 / '토스에게 발송 요청하기' 정기 캠페인 만들기.

  ait_smart_message.py list   <appName>
  ait_smart_message.py create <appName> --title 캠페인명 --push-title 새메뉴판(7자) --body "내용(25자, ~요.)"
        --code weekly-menu --days 금 --start 2026-10-30 --time 12:00
        --agreement "동의문 이름" --timing "1. 매주 금요일 낮 12시, …때" --purpose "새 메뉴판" [--submit]

- 앱에서는 Notification.requestAgreement({options:{templateCode:'<appName>-<code>'}}) 로 동의를 받는다(발송 코드 = templateCode).
- 같은 캠페인명이 목록에 있으면 만들지 않고 EXISTS(멱등).
- 함정(2026-10-22 eodimeok 손으로 성공한 순서):
  * 탭이 백그라운드면 React 날짜칸(spinbutton)·대화창 버튼이 반응하지 않는다 → 매 단계 전에 탭을 앞으로 띄운다(front).
  * 날짜·시각 칸은 role=spinbutton. focus 후 keydown/beforeinput 으로 숫자를 한 글자씩 넣는다.
  * 요일은 div[role=combobox] → [role=option] 토글(aria-selected). 기본 월~금이 골라져 있다.
  * 동의문에 '매주 금요일 12시'처럼 구체 시각이 없으면 "발송 시각이 구체적으로 명시되지 않았어요"로 거절. 동의문은 수정 불가, 새로 만들어 '변경'으로 연결.
  * 11:00 은 "미리예약하는 시간이 전날짜로 넘어갈 수 없습니다"로 거절, 12:00 은 통과(예약이 약 12시간 전에 잡히는 듯).
  * 첫 등록 시도가 실패해도 캠페인이 '임시저장'으로 남는다 → 목록에서 행을 눌러 '수정' 화면(/functional-smart-message/<no>/edit)에서 다시 등록.
    이 경로에선 시각이 00:00 으로 다시 읽히니 다시 넣는다. 등록 성공 토스트 "캠페인을 등록했어요", 상태 '승인됨'(즉시).
  * 신청서 문구의 회사명은 콘솔이 사업자명으로 자동으로 넣는다(바꿀 칸 없음).
- 왜 화면 조작인가: 콘솔 공개 API 없음.
검증: list 됨(2026-10-22). create 는 같은 순서를 손으로 성공(eodimeok Campaign 128436), 스크립트 create 경로는 미검증.
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ait_app_register.py')).read().split("ap = argparse")[0]
_g = {'__name__': 'ait_app_register_lib'}
exec(_src, _g)
c, SETV, console_tab = _g['c'], _g['SETV'], _g['console_tab']
WS = '35273'
PRESS = ("function __p(e){['pointerdown','mousedown','pointerup','mouseup','click'].forEach(n=>e.dispatchEvent(new (n.startsWith('pointer')?PointerEvent:MouseEvent)"
         "(n,{bubbles:true,cancelable:true,pointerType:'mouse',button:0})))};")
KEYS = ("function __k(e,k){e.dispatchEvent(new KeyboardEvent('keydown',{key:k,bubbles:true,cancelable:true}));"
        "e.dispatchEvent(new InputEvent('beforeinput',{data:k,inputType:'insertText',bubbles:true,cancelable:true}));e.dispatchEvent(new KeyboardEvent('keyup',{key:k,bubbles:true}))};")


def front(t):
    w, ti = c.find_tab(t)
    _t, win = c.ref(t)
    c.jxa(f"{win}.activeTabIndex = {ti}; {win}.index = 1; C.activate()")
    time.sleep(1.2)


def js(t, code):
    return c.run_js(t, code)


def press_btn(t, text, scope='document', last=True):
    r = js(t, PRESS + "var b=[...%s.querySelectorAll('button')].filter(b=>b.innerText.trim()==%s);b=b[%s];if(!b)'NOTFOUND';else{__p(b);'OK'}"
           % (scope, json.dumps(text), 'b.length-1' if last else '0'))
    if r != 'OK':
        raise RuntimeError(f'button {text}: {r}')


def spin(t, idx, val):
    js(t, KEYS + "var s=[...document.querySelectorAll('[role=spinbutton]')][%d];s.focus();%s.split('').forEach(ch=>__k(s,ch));1" % (idx, json.dumps(val)))
    time.sleep(0.3)


def alerts(t):
    return js(t, "[...document.querySelectorAll('[role=alert],[role=status],[role=dialog]')].map(x=>x.innerText.slice(0,200)).filter(x=>!x.includes('방해 금지')).join(' ## ')") or ''


def campaigns(t, app):
    c.goto(t, f'https://apps-in-toss.toss.im/workspace/{WS}/mini-app/{app}/smart-message?tab=FUNCTIONAL')
    time.sleep(7)
    return json.loads(js(t, "JSON.stringify([...document.querySelectorAll('tbody tr')].map(r=>[...r.cells].map(x=>x.innerText.trim().replace(/\\n/g,' '))))") or '[]')


def fill_schedule(t, a):
    front(t)
    # 요일: 원하는 것만 남긴다
    js(t, PRESS + "__p([...document.querySelectorAll('div[role=combobox]')].find(e=>/[월화수목금토일]/.test(e.innerText)));1")
    time.sleep(1)
    want = set(a.days)
    for d in '월화수목금토일':
        js(t, PRESS + "var o=[...document.querySelectorAll('[role=option]')].find(e=>e.innerText.trim()==%s);"
                      "if(o&&(o.getAttribute('aria-selected')=='true')!=%s)__p(o);1" % (json.dumps(d), 'true' if d in want else 'false'))
        time.sleep(0.3)
    js(t, "document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));1")
    js(t, "var cb=document.querySelector('input[type=checkbox]');if(cb&&!cb.checked)cb.click();1")  # 종료일 없음
    time.sleep(0.5)
    y, m, d = a.start.split('-')
    hh, mm = a.time.split(':')
    for i, v in enumerate([y, m, d, hh, mm]):
        spin(t, i, v)
    return js(t, "[...document.querySelectorAll('[role=spinbutton]')].map(e=>e.innerText).join(' ')+' | '+[...document.querySelectorAll('div[role=combobox]')].map(e=>e.innerText).join()")


def attach_agreement(t, a):
    front(t)
    press_btn(t, '변경' if js(t, "[...document.querySelectorAll('button')].some(b=>b.innerText.trim()=='변경')") == True else '등록하기', last=False)
    time.sleep(2)
    for k, v in {'agreementName': a.agreement, 'notificationTiming': a.timing, 'purpose': a.purpose}.items():
        js(t, SETV + "var e=document.querySelector('[role=dialog] [name=%s]');__setv(e,%s);1" % (k, json.dumps(v)))
    front(t)
    press_btn(t, '등록하기', scope="document.querySelector('[role=dialog]')")
    for _ in range(10):
        time.sleep(1)
        if js(t, "document.querySelectorAll('[role=dialog]').length") == 0:
            return
    raise RuntimeError('알림동의문 대화창이 안 닫힘')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['list', 'create'])
    ap.add_argument('app')
    for k in ['title', 'push-title', 'body', 'code', 'start', 'time', 'agreement', 'timing', 'purpose']:
        ap.add_argument('--' + k)
    ap.add_argument('--days', default='금')
    ap.add_argument('--submit', action='store_true')
    a = ap.parse_args()
    t = console_tab(f'https://apps-in-toss.toss.im/workspace/{WS}/mini-app/{a.app}/smart-message')
    try:
        rows = campaigns(t, a.app)
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        if a.cmd == 'list':
            print(f'RESULT: OK {len(rows)}개')
            return
        if any(a.title in ' '.join(r) for r in rows):
            print(f'RESULT: EXISTS {a.title}')
            return
        c.goto(t, f'https://apps-in-toss.toss.im/workspace/{WS}/mini-app/{a.app}/functional-smart-message/create')
        time.sleep(7)
        front(t)
        for name, v in {'campaignTitle': a.title, 'messageContent.0.pushTemplate.title': a.push_title,
                        'messageContent.0.pushTemplate.content': a.body, 'messageContent.0.code': a.code}.items():
            js(t, SETV + "var e=document.querySelector('[name=\"%s\"]');__setv(e,%s);1" % (name, json.dumps(v)))
        js(t, PRESS + "var b=[...document.querySelectorAll('button,label')].find(e=>e.innerText.includes('토스에게 발송 요청하기'));b&&__p(b);1")
        js(t, PRESS + "__p(document.querySelector('button[value=RECURRING]'));1")
        time.sleep(1)
        print('schedule', fill_schedule(t, a))
        attach_agreement(t, a)
        print('schedule', fill_schedule(t, a))
        if not a.submit:
            print('RESULT: DRY_RUN 채움(등록 안 누름)')
            return
        front(t)
        press_btn(t, '등록하기')
        for _ in range(12):
            time.sleep(1)
            al = alerts(t)
            if '등록했어요' in al:
                print(json.dumps(campaigns(t, a.app), ensure_ascii=False))
                print(f'RESULT: REGISTERED {a.title}')
                return
            if '실패' in al or '명시' in al or '입력해주세요' in al:
                print(f'RESULT: REJECTED {al}')
                sys.exit(1)
        print(f'RESULT: UNCONFIRMED {alerts(t)} — 목록에서 임시저장 여부 확인, 다시 누르지 말 것')
        sys.exit(2)
    finally:
        c.close_tab(t)


if __name__ == '__main__':
    main()
