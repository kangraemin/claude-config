"""Usage: ait_push_status.py <app> [--ws 35273]

Apps-in-Toss console 푸시알림(스마트 발송) readiness. Opens <app>/smart-message, prints the page summary, presses
'만들기' and reports whether creation is gated or which form fields appear. Never fills or submits anything.
Pre: console login on Chrome Profile 1. Screen-driven because the console has no public API for smart messages.
Gotcha: the '만들기' button ignores __press; it needs a dispatched pointer/mouse/click sequence.
RESULT: GATED_APP_REVIEW (앱 정보 검토 먼저) | FORM (fields listed) | NO_CREATE_BUTTON | UNKNOWN
"""
import sys
import time

from _ait import url, wait_page
from _common import js, parser, tab

ap = parser("Apps-in-Toss smart-message (push) status")
ap.add_argument("app")
ap.add_argument("--ws", default="35273")
a = ap.parse_args()

with tab(url(a.ws, a.app, "smart-message"), a) as tid:
    wait_page(tid, "푸시알림")
    time.sleep(2)
    print(js(tid, "return (document.querySelector('main')||document.body).innerText.slice(0,1500)"))
    r = js(tid, """const b=[...document.querySelectorAll('button')].find(e=>__vis(e)&&e.innerText.trim()==='만들기');
      if(!b) return 'none'; b.scrollIntoView(); const r=b.getBoundingClientRect();
      ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(t=>b.dispatchEvent(new MouseEvent(t,{bubbles:true,clientX:r.x+5,clientY:r.y+5})));
      return 'clicked'""")
    if r == "none":
        print("RESULT: NO_CREATE_BUTTON"); sys.exit(0)
    time.sleep(5)
    body = js(tid, "return document.body.innerText")
    if "앱 정보 검토를 먼저 완료" in body:
        print("RESULT: GATED_APP_REVIEW"); sys.exit(0)
    fields = js(tid, """return [...document.querySelectorAll('input,textarea,select')].filter(__vis)
      .map(e=>e.tagName+'|'+e.type+'|'+(e.name||'')+'|'+(e.placeholder||'')).join('\\n')""")
    print(js(tid, "return location.href"))
    print(fields)
    print("RESULT: FORM" if fields else "RESULT: UNKNOWN")
