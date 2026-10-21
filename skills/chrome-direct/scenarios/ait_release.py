#!/usr/bin/env python3
"""[제출] 앱인토스 콘솔 — 검토 통과('출시 준비됨') 버전 하나를 '출시하기'. 요청 취소·롤백·다른 버전은 안 누름.
기본 dry-run: 그 버전 행의 상태와 '출시하기' 버튼만 보고.
--submit: 버튼 → 확인 창의 출시 버튼 → 상단 '현재 출시된 버전'이 그 버전인지 확인.
창에 약관·동의가 나오면 멈춤(NEEDS_OWNER). 멱등: 이미 현재 출시 버전이면 ALREADY.

  ait_release.py eodimeok --version 20261021-13
  ait_release.py eodimeok --version 20261021-13 --submit
"""
import time

from _ait import table, url, wait_page
from _common import Blocked, emit, js, parser, poll, run, tab

ap = parser(__doc__, submit=True)
ap.add_argument("app")
ap.add_argument("--version", required=True, help="버전 내역의 '버전' 값 (예: 20261021-13)")
ap.add_argument("--workspace", default="35273")
a = ap.parse_args()
ROW = f"const tr = [...document.querySelectorAll('table tbody tr')].find(r => r.children[1] && r.children[1].innerText.trim() === {a.version!r});"
DLG = "const d = [...document.querySelectorAll('[role=dialog], [role=alertdialog]')].pop();"  # __vis 필터는 창이 떠도 0개가 돼 시간 초과(10/22)
CUR = r"return (document.body.innerText.match(/현재 출시된 버전:\s*(\S+)/) || [, ''])[1];"


def row(tid):
    rows = [r for r in table(tid) if len(r["cells"]) > 3 and r["cells"][1] == a.version]
    if not rows:
        raise Blocked(f"NO_VERSION {a.version} 이 1쪽에 없음 (ait_builds.py {a.app} 로 확인)")
    return rows[0]


def main():
    with tab(url(a.workspace, a.app, "app-build"), a) as tid:
        wait_page(tid, "버전 내역")
        if js(tid, CUR) == a.version:
            emit({"app": a.app, "version": a.version}, "ALREADY", f"{a.version} 이미 출시됨")
            return
        r = row(tid)
        btn = next((b for b in r["buttons"] if b["text"] == "출시하기"), None)
        info = {"app": a.app, "version": a.version, "status": r["cells"][3], "buttons": r["buttons"], "current": js(tid, CUR)}
        if not btn or btn["disabled"]:
            emit(info, "NOT_AVAILABLE", f"'출시하기' 없음/비활성 (상태 {r['cells'][3]})")
            raise Blocked("NOT_AVAILABLE")
        if not a.submit:
            emit(info, "DRY_RUN", "출시 가능 — --submit 으로 출시")
            return
        if js(tid, ROW + "const b = [...tr.querySelectorAll('button')].find(b => b.innerText.trim() === '출시하기'); __press(b); return 1") != 1:
            raise RuntimeError("버튼 누르기 실패")
        dtext = poll(tid, DLG + "return d ? d.innerText : null", 15)
        info["dialog"] = dtext[:800]
        if any(k in dtext for k in ("약관", "동의")):
            raise Blocked("NEEDS_OWNER 출시 창에 약관/동의 — " + dtext[:200].replace("\n", " "))
        ok = js(tid, DLG + """const bs = [...d.querySelectorAll('button')].filter(b => __vis(b) && !b.disabled && !/취소|닫기/.test(b.innerText));
          const b = bs.find(b => /출시/.test(b.innerText)) || bs.find(b => /확인/.test(b.innerText)); if (!b) return 'NOBUTTON:' + bs.map(b => b.innerText).join('|');
          __press(b); return 'OK';""")
        if ok != "OK":
            raise RuntimeError(f"창 출시 버튼: {ok}")
        for _ in range(20):
            time.sleep(1.5)
            if js(tid, CUR) == a.version:
                emit(info, "RELEASED", f"{a.app} {a.version} 출시됨")
                return
        raise Blocked("UNCONFIRMED 출시 버튼은 눌렀으나 '현재 출시된 버전'이 안 바뀜 — ait_builds.py 로 확인, 다시 누르지 말 것")


run(main, a, f"앱인토스 콘솔 워크스페이스 {a.workspace} 앱 {a.app} → 앱 출시 → 버전 {a.version} 행. "
    + ("'출시하기'를 한 번만 눌러 확인 창에서 출시한 뒤 '현재 출시된 버전'이 그 버전인지 확인." if a.submit
       else "'출시하기' 버튼 활성 여부와 상태만 보고(누르지 마라).")
    + " 요청 취소·롤백·다른 버전·다른 앱 금지. 약관 동의가 나오면 NEEDS_OWNER.", cwd="/tmp")
