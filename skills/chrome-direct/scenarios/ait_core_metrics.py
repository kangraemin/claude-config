#!/usr/bin/env python3
"""[제출] 앱인토스 콘솔 — 핵심 지표(활성 1개 + 대표 전환 1개) 등록. 이미 등록돼 있으면 현재 지표만 읽고 끝낸다(멱등).

  ait_core_metrics.py seoultax                                    # 읽기: 등록된 지표 출력
  ait_core_metrics.py seoultax --event deck_end_view --name "오늘 카드 끝까지 봄" --desc "..." [--submit]
활성 지표는 템플릿 '7일 이후 재방문 유저'(기본값) 그대로 둔다. 전환은 '직접 조합하기' → 이벤트 목록에서 --event 선택.
사전 조건: 그 이벤트가 앱에서 한 번 이상 로깅돼 콘솔 이벤트 목록에 떠 있어야 한다(없으면 BLOCKED).
화면 조작인 이유: 핵심 지표는 공개 API가 없다. 바뀐 지표는 다음 날부터 집계된다.
함정: TDS 탭·버튼은 .click() 무시 → __press. '이벤트 추가하기'는 radix 팝오버(body 마지막 div, __vis=false로 잡힘) — 한 번만 누른다(두 번 누르면 닫힘).
"""
import time

from _ait import url, wait_page
from _common import Blocked, emit, js, parser, run, tab

ap = parser(__doc__, submit=True)
ap.add_argument("app")
ap.add_argument("--event", help="대표 전환으로 쓸 이벤트 이름 (없으면 읽기만)")
ap.add_argument("--name", help="전환 지표 이름 (2~30자)")
ap.add_argument("--desc", default="", help="전환 지표 설명")
ap.add_argument("--workspace", default="35273")
a = ap.parse_args()
MAIN = "return (document.querySelector('main')||document.body).innerText"


def read(tid):
    t = js(tid, MAIN)
    lines = [x.strip() for x in t.split("\n") if x.strip()]
    out = {"registered": "수정하기" in lines, "active": None, "conversion": None}
    for i, x in enumerate(lines):
        if x == "활성" and i:
            out["active"] = lines[i - 1]
        if x == "대표 전환" and i + 1 < len(lines):
            out["conversion"] = lines[i + 1]
    return out


def main():
    with tab(url(a.workspace, a.app, "core-metrics"), a) as tid:
        wait_page(tid, "핵심 지표")
        time.sleep(2)
        cur = read(tid)
        if cur["registered"] or not a.event:
            emit({"app": a.app, **cur}, "ALREADY" if cur["registered"] else "NONE", "읽기만 함")
            return
        if not a.name:
            raise Blocked("--name 필요")
        js(tid, "const b=[...document.querySelectorAll('button')].find(e=>e.innerText.trim()==='등록하기'); __press(b); return 1")
        wait_page(tid, "전환 지표")
        js(tid, "const bs=[...document.querySelectorAll('button')].filter(b=>b.innerText.trim().startsWith('직접 조합하기')); __press(bs[bs.length-1]); return 1")
        time.sleep(1.5)
        import chromectl as c
        c.fill(tid, 'input[placeholder^="지표를 구분할"]', a.name)
        if a.desc:
            c.fill(tid, 'input[placeholder^="이 지표가 무엇을"]', a.desc)
        js(tid, "const b=[...document.querySelectorAll('button')].find(b=>b.innerText.trim()==='이벤트 추가하기'); b.scrollIntoView({block:'center'}); __press(b); return 1")
        time.sleep(2)
        # 팝업 목록은 20개만 보여 준다 → 검색칸에 이름을 넣어 거른다(10/30 먹맵 video_watch_click이 목록 밖이라 BLOCKED로 잘못 나왔다)
        js(tid, f"""const p=[...document.querySelectorAll('body > div')].pop(); const i=p.querySelector('input'); if(!i) return 0;
          i.focus(); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,{a.event!r});
          i.dispatchEvent(new Event('input',{{bubbles:true}})); return 1""")
        time.sleep(3)
        r = js(tid, f"""const p=[...document.querySelectorAll('body > div')].pop();
          const li=[...p.querySelectorAll('li')].find(l=>l.innerText.trim()==={a.event!r}); if(!li) return 'NOEVENT';
          __press(li.querySelector('div')||li); return 'OK'""")
        if r != "OK":
            raise Blocked(f"이벤트 목록에 {a.event} 없음 — 앱에서 한 번 로깅된 뒤 다시")
        time.sleep(1.5)
        if a.event not in js(tid, MAIN):
            raise RuntimeError("이벤트 선택이 화면에 반영되지 않음")
        if not a.submit:
            emit({"app": a.app, "event": a.event, "name": a.name}, "DRY_RUN", "--submit 없으면 등록 안 누름")
            return
        js(tid, "const b=[...document.querySelectorAll('button[type=submit]')].find(b=>b.innerText.trim()==='등록하기'); __press(b); return 1")
        time.sleep(4)
        wait_page(tid, "수정하기")
        emit({"app": a.app, **read(tid)}, "SUBMITTED")


run(main, a, f"앱인토스 콘솔(워크스페이스 {a.workspace}) 앱 {a.app}의 핵심 지표 화면에서 "
    f"활성=7일 이후 재방문 유저(템플릿), 대표 전환=직접 조합하기·이벤트 {a.event}·이름 {a.name}로 등록"
    + (" 후 등록하기를 눌러라." if a.submit else ". 등록하기는 누르지 마라."))
