#!/usr/bin/env python3
"""[읽기] 앱인토스 콘솔 — 앱의 인앱 광고 그룹 목록과 각 adGroupId(ait.v2.live.xxxx), 유형·보상·만든 날짜.
행을 눌러 상세(오른쪽 패널)를 여는 것만 한다 — 수정·복사·생성 안 함.

  ait_adgroups.py seoultax
  ait_adgroups.py ttuk-chiro --name 뚝이어하기
Output lines `AD_GROUP <app> <name> <type> <adGroupId>` (codex_console 형식과 같음).
"""
import re
import time

from _ait import goto, table, url, wait_page
from _common import emit, js, parser, poll, run, tab
import chromectl as c

ap = parser(__doc__)
ap.add_argument("app")
ap.add_argument("--name", help="이 이름의 그룹만")
ap.add_argument("--workspace", default="35273")
a = ap.parse_args()
DETAIL = r"""const m = location.search.match(/groupId=([\w.]+)/); const d = [...document.querySelectorAll('[role=dialog]')].filter(__vis).pop();
  if (!m || !d || !d.innerText.includes(m[1])) return null; const t = d.innerText;
  const f = k => (t.match(new RegExp(k + '\\n([^\\n]+)')) || [, ''])[1];
  return {id: m[1], type: f('광고 타입'), reward: f('보상, 수량'), created: f('광고 그룹 만든 날짜'), status: f('상태')};"""
LIST = url(a.workspace, a.app, "placement-group/list?tab=adUnitGroup")


def main():
    with tab(LIST, a) as tid:
        wait_page(tid, "광고 그룹 이름")
        rows = table(tid)
        groups = []
        for r in rows:
            cl = r["cells"]
            if len(cl) < 2 or (a.name and cl[1] != a.name):
                continue
            det = None
            for attempt in range(3):  # the detail panel sometimes ignores the first click
                js(tid, f"""const tr = [...document.querySelectorAll('table tbody tr')].filter(__vis)[{r['i']}];
                  if (tr) (tr.children[1].firstElementChild || tr.children[1]).click(); return 1;""")
                try:
                    det = poll(tid, DETAIL, 10)
                    break
                except RuntimeError:
                    time.sleep(1)
            if not det:
                raise RuntimeError(f"광고 그룹 '{cl[1]}' 상세가 안 열림")
            groups.append({"name": cl[1], "listType": cl[0], "listStatus": cl[2] if len(cl) > 2 else "", **det})
            js(tid, "document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true})); return 1")
            c.goto(tid, LIST)
            time.sleep(2)
            wait_page(tid, "광고 그룹 이름")
        emit({"app": a.app, "groups": groups}, "OK", f"{len(groups)} groups")
        for g in groups:
            print(f"AD_GROUP {a.app} {g['name']} {g['type'] or g['listType']} {g['id']}")


run(main, a, f"READ ONLY. 앱인토스 콘솔 워크스페이스 {a.workspace} 앱 {a.app} → 수익화 > 인앱 광고 > 광고 그룹 탭. 그룹마다 행을 눌러 "
    "URL의 groupId(ait.v2.live.…)와 광고 타입·보상을 읽고 `AD_GROUP <app> <name> <type> <adGroupId>` 줄로 출력. 생성·수정·복사·약관 동의 금지.", cwd="/tmp")
