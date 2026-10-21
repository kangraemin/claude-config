#!/usr/bin/env python3
"""[제출] 앱인토스 콘솔 — 버전 하나 '검토 요청하기'. 출시(출시하기)·요청 취소·롤백은 절대 안 누름.
기본 dry-run: 그 버전 행의 상태와 '검토 요청하기' 활성 여부만 보고.
--submit: 버튼 → 창에 출시 노트 칸이 있으면 --notes 로 채움(없으면 멈춤) → 창의 요청 버튼 → 상태 '검토 중' 확인.
창에 동의 체크·약관이 나오면 멈춤(NEEDS_OWNER).

  ait_review_request.py seoultax --version 20261016-22
  ait_review_request.py seoultax --version 20261016-22 --notes "광고를 불러오지 못할 때 안내가 나오도록 개선했어요." --submit
"""
import time

from _ait import table, url, wait_page
from _common import Blocked, emit, js, parser, poll, run, tab

ap = parser(__doc__, submit=True)
ap.add_argument("app")
ap.add_argument("--version", required=True, help="버전 내역의 '버전' 값 (예: 20261017-24)")
ap.add_argument("--notes", help="출시 노트(업데이트 내용)")
ap.add_argument("--workspace", default="35273")
a = ap.parse_args()
ROW = f"const tr = [...document.querySelectorAll('table tbody tr')].find(r => r.children[1] && r.children[1].innerText.trim() === {a.version!r});"
DLG = "const d = [...document.querySelectorAll('[role=dialog], [role=alertdialog]')].filter(__vis).pop();"


def row(tid):
    rows = [r for r in table(tid) if len(r["cells"]) > 3 and r["cells"][1] == a.version]
    if not rows:
        raise Blocked(f"NO_VERSION {a.version} 이 1쪽에 없음 (ait_builds.py {a.app} 로 확인)")
    return rows[0]


def main():
    with tab(url(a.workspace, a.app, "app-build"), a) as tid:
        wait_page(tid, "버전 내역")
        r = row(tid)
        btn = next((b for b in r["buttons"] if b["text"] == "검토 요청하기"), None)
        info = {"app": a.app, "version": a.version, "status": r["cells"][3], "reviewButton": btn,
                "inReview": [x["cells"][1] for x in table(tid) if len(x["cells"]) > 3 and x["cells"][3] == "검토 중"]}
        if not btn:
            emit(info, "NOT_AVAILABLE", f"'검토 요청하기' 없음 (상태 {r['cells'][3]})")
            raise Blocked("NOT_AVAILABLE")
        if btn["disabled"]:
            emit(info, "DISABLED", "버튼 비활성 — 토스앱에서 그 버전을 한 번 열어야 켜짐(콘솔 반영 ~20분 지연) · 검토 중인 다른 버전이 있어도 꺼짐")
            raise Blocked("DISABLED")
        if not a.submit:
            emit(info, "DRY_RUN", "검토 요청 가능 — --submit 으로 요청")
            return
        if js(tid, ROW + "const b = [...tr.querySelectorAll('button')].find(b => b.innerText.trim() === '검토 요청하기'); __press(b); return 1") != 1:
            raise RuntimeError("버튼 누르기 실패")
        dtext = poll(tid, DLG + "return d ? d.innerText : null", 15)
        info["dialog"] = dtext[:800]
        if any(k in dtext for k in ("약관", "동의")):
            raise Blocked("NEEDS_OWNER 검토 요청 창에 약관/동의 — " + dtext[:200].replace("\n", " "))
        if js(tid, DLG + "return !!(d && d.querySelector('textarea'))"):
            if not a.notes:
                js(tid, DLG + "const c = [...d.querySelectorAll('button')].find(b => /취소|닫기/.test(b.innerText)); if (c) __press(c); return 1")
                raise Blocked("NEED_NOTES 출시 노트 칸이 있음 — --notes 로 다시")
            if js(tid, DLG + f"return __setv(d.querySelector('textarea'), {a.notes!r})") is not True:
                raise RuntimeError("출시 노트 채우기 실패")
        ok = js(tid, DLG + """const bs = [...d.querySelectorAll('button')].filter(b => __vis(b) && !b.disabled && !/취소|닫기|출시하기/.test(b.innerText));
          const b = bs.find(b => /검토 요청|요청하기|요청|확인/.test(b.innerText)) ; if (!b) return 'NOBUTTON:' + bs.map(b => b.innerText).join('|');
          __press(b); return 'OK';""")
        if ok != "OK":
            raise RuntimeError(f"창 요청 버튼: {ok}")
        for _ in range(20):
            time.sleep(1.5)
            st = [x["cells"][3] for x in table(tid, 2) if len(x["cells"]) > 3 and x["cells"][1] == a.version]
            if st and st[0] == "검토 중":
                emit(info, "REQUESTED", f"{a.app} {a.version} 검토 중")
                return
        raise Blocked("UNCONFIRMED 요청 버튼은 눌렀으나 상태가 '검토 중'으로 안 바뀜 — ait_builds.py 로 확인, 다시 누르지 말 것")


run(main, a, f"앱인토스 콘솔 워크스페이스 {a.workspace} 앱 {a.app} → 앱 출시 → 버전 {a.version} 행. "
    + (f"'검토 요청하기'를 눌러 출시 노트가 필요하면 \"{a.notes}\" 로 쓰고 요청을 한 번만 보낸 뒤 상태 '검토 중'을 확인." if a.submit
       else "'검토 요청하기' 버튼 활성 여부와 상태만 보고(누르지 마라).")
    + " 출시하기·요청 취소·롤백·다른 앱 금지. 약관 동의가 나오면 NEEDS_OWNER.", cwd="/tmp")
