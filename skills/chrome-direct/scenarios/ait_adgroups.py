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
        wait_page(tid, "인앱 광고")
        # 그룹이 0개면 표 대신 '광고를 등록하고 수익을 만들어 보세요' 화면이라 표를 기다리면 안 끝난다
        poll(tid, "return /광고 그룹 이름|광고를 등록하고 수익을|약관에 먼저 동의/.test(document.body.innerText) ? 1 : null", 30)
        rows = [] if js(tid, "return document.body.innerText.includes('광고를 등록하고 수익을')") else table(tid)
        # 상세 패널은 '구글 반영 중'이면 안 열린다 → 콘솔이 쓰는 API로 읽는다(로그인 탭 안 XHR)
        api = f"/console/api-public/v3/appsintossconsole/workspaces/{a.workspace}/mini-app/{a.app}/in-app-ads-v2/placement-groups"
        res = js(tid, f"var x=new XMLHttpRequest();x.open('GET',{api!r},false);x.send();return JSON.parse(x.responseText)")
        kind = {"BANNER": "배너", "INTERSTITIAL": "전면형", "REWARDED": "리워드"}
        groups = [{"name": g["name"], "type": kind.get(g["adFormat"], g["adFormat"]), "id": g["groupId"], "state": g["state"],
                   "reward": g.get("rewardSettings")} for g in (res.get("success") or []) if not a.name or g["name"] == a.name]
        if not rows and groups:
            raise RuntimeError("화면엔 그룹이 없는데 API엔 있음 — 화면 확인")
        emit({"app": a.app, "groups": groups}, "OK", f"{len(groups)} groups")
        for g in groups:
            print(f"AD_GROUP {a.app} {g['name']} {g['type'] or g['listType']} {g['id']}")


run(main, a, f"READ ONLY. 앱인토스 콘솔 워크스페이스 {a.workspace} 앱 {a.app} → 수익화 > 인앱 광고 > 광고 그룹 탭. 그룹마다 행을 눌러 "
    "URL의 groupId(ait.v2.live.…)와 광고 타입·보상을 읽고 `AD_GROUP <app> <name> <type> <adGroupId>` 줄로 출력. 생성·수정·복사·약관 동의 금지.", cwd="/tmp")
