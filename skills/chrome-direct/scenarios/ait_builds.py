#!/usr/bin/env python3
"""[읽기] 앱인토스 콘솔 — 앱 목록 / 앱 하나의 버전(번들) 내역·상태·출시 버전·검토 배너.

  ait_builds.py --apps                      # 워크스페이스의 앱 이름·분류
  ait_builds.py seoultax                    # 버전 내역 (생성일·버전·SDK·상태·메모·출시일시·버튼)
  ait_builds.py seoultax --version 20261017-24
  ait_builds.py seoultax --reject-reason 20261017-23   # 반려 사유 창 읽고 닫음
"""
from _ait import goto, table, url, wait_page
from _common import emit, js, parser, poll, run, tab

ap = parser(__doc__)
ap.add_argument("app", nargs="?", help="appName (예: seoultax, seoultaxdev, screw-toktok)")
ap.add_argument("--apps", action="store_true")
ap.add_argument("--version")
ap.add_argument("--reject-reason", metavar="VERSION", help="그 버전의 '반려 사유' 창 글을 읽음 (읽기 전용)")
ap.add_argument("--workspace", default="35273")
a = ap.parse_args()


def main():
    if a.apps or not a.app:
        with tab(url(a.workspace), a) as tid:
            wait_page(tid, "나의 앱")
            t = js(tid, r"""const t = document.body.innerText; const s = t.indexOf('나의 앱'), e = t.indexOf('가이드', s);
              return t.slice(s, e > s ? e : s + 1500).split('\n').map(x => x.trim()).filter(Boolean);""")
            # '나의 앱', N, '등록하기', then name / category pairs
            body = [x for x in t[1:] if x != "등록하기"]
            n = int(body[0]) if body and body[0].isdigit() else None
            rest = body[1:] if n is not None else body
            apps = [{"name": rest[i], "category": rest[i + 1] if i + 1 < len(rest) else ""} for i in range(0, len(rest), 2)]
            emit({"workspace": a.workspace, "count": n, "apps": apps}, "OK", f"{len(apps)} apps")
        return
    with tab(url(a.workspace, a.app, "app-build"), a) as tid:
        wait_page(tid, "버전 내역")
        head = js(tid, r"""const t = document.body.innerText;
          return {banner: (t.match(/(검토 중이에요[^\n]*|반려[^\n]*알려드릴게요[^\n]*|출시[^\n]*완료[^\n]*)/) || [''])[0],
                  current: (t.match(/현재 출시된 버전:\s*(\S+)/) || [, ''])[1], releasedAt: (t.match(/\((\d{4}\. \d{2}\. \d{2} [\d:]+)에 출시됨\)/) || [, ''])[1],
                  pager: [...document.querySelectorAll('nav button, [aria-label*=page], [class*=pagination] button')].map(b => b.innerText.trim()).filter(x => /^\d+$/.test(x))}""")
        rows = []
        for r in table(tid):
            cl = r["cells"]
            if len(cl) < 6:
                continue
            rows.append({"created": cl[0], "version": cl[1], "sdk": cl[2], "status": cl[3], "memo": cl[4].replace(" / 더보기", ""),
                         "releasedAt": cl[5], "buttons": [b["text"] + (" (비활성)" if b["disabled"] else "") for b in r["buttons"] if b["text"]]})
        if a.version:
            rows = [r for r in rows if r["version"] == a.version]
        if a.reject_reason:
            r = js(tid, f"""const tr = [...document.querySelectorAll('table tbody tr')].find(r => r.children[1] && r.children[1].innerText.trim() === {a.reject_reason!r});
              if (!tr) return 'NOROW'; const b = [...tr.querySelectorAll('button')].find(b => b.innerText.trim() === '반려 사유');
              if (!b) return 'NOBUTTON'; __press(b); return 'OK';""")
            if r != "OK":
                raise RuntimeError(f"반려 사유 {a.reject_reason}: {r}")
            head["rejectReason"] = poll(tid, "const d = [...document.querySelectorAll('[role=dialog], [role=alertdialog]')].filter(__vis).pop(); return d ? d.innerText.trim() : null", 10)
            js(tid, "document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true})); const d = [...document.querySelectorAll('[role=dialog] button')].filter(__vis).find(b => /닫기|확인/.test(b.innerText) || b.getAttribute('aria-label') === '닫기'); if (d) __press(d); return 1")
        emit({"app": a.app, **head, "versions": rows}, "OK", f"{len(rows)} versions (1쪽만)")


run(main, a, f"READ ONLY. 앱인토스 콘솔(https://apps-in-toss.toss.im, 워크스페이스 {a.workspace})에서 "
    + (f"앱 {a.app} → 앱 출시 화면의 버전 내역 표(생성일·버전·SDK·상태·메모·출시일시)와 상단 검토 배너·현재 출시 버전을 그대로 출력." if a.app else "나의 앱 목록(이름·분류)을 출력.")
    + " 아무 버튼(검토 요청·출시·요청 취소·롤백)도 누르지 마라.", cwd="/tmp")
