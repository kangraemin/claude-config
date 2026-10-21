#!/usr/bin/env python3
"""[읽기] 앱인토스 콘솔 — 앱별 인앱 광고 노출·예상 수익 합계(기간).

  ait_ad_revenue.py oneul-kkum oneul-tarot-card son-calendar          # 이번 달 1일 ~ 오늘
  ait_ad_revenue.py oneul-tarot-card --from 2026-10-01 --to 2026-10-31
콘솔 '인앱 광고 > 성과' 표가 부르는 API(placement-groups?includeReport=true)를 로그인 탭 안 XHR로 읽는다.
리포트가 아직 없으면(그룹 '구글 반영 중', 노출 0) report=null → 0으로 센다.
report 안 필드 이름은 처음 값이 생길 때 확인한다: revenue/impression 이 들어간 숫자 필드를 더하고 원문(raw)도 같이 출력한다.
"""
import datetime as dt

from _ait import url, wait_page
from _common import emit, js, parser, run, tab

ap = parser(__doc__)
ap.add_argument("apps", nargs="+")
ap.add_argument("--from", dest="start", default=dt.date.today().replace(day=1).isoformat())
ap.add_argument("--to", dest="end", default=dt.date.today().isoformat())
ap.add_argument("--workspace", default="35273")
a = ap.parse_args()


def sums(rep):
    out = {"revenue": 0.0, "impression": 0}
    for k, v in (rep or {}).items():
        if isinstance(v, (int, float)):
            if "revenue" in k.lower():
                out["revenue"] += v
            elif "impression" in k.lower():
                out["impression"] += v
    return out


def main():
    with tab(url(a.workspace, a.apps[0], "home"), a) as tid:
        wait_page(tid, "홈")
        apps, total = [], 0.0
        for app in a.apps:
            api = (f"/console/api-public/v3/appsintossconsole/workspaces/{a.workspace}/mini-app/{app}/in-app-ads-v2/placement-groups"
                   f"?includeReport=true&reportStartDate={a.start}&reportEndDate={a.end}")
            res = js(tid, f"var x=new XMLHttpRequest();x.open('GET',{api!r},false);x.send();return JSON.parse(x.responseText)")
            groups = []
            for g in res.get("success") or []:
                s = sums(g.get("report"))
                total += s["revenue"]
                groups.append({"name": g["name"], "state": g["state"], **s, "raw": g.get("report")})
            apps.append({"app": app, "groups": groups})
            for g in groups:
                print(f"AD {app} {g['name']} {g['state']} 노출 {g['impression']} 수익 {g['revenue']:.0f}원")
        emit({"from": a.start, "to": a.end, "apps": apps, "total": round(total)}, "OK", f"합계 {total:.0f}원 ({a.start}~{a.end})")


run(main, a, f"READ ONLY. 앱인토스 콘솔 {a.apps} 인앱 광고 성과 탭의 기간 {a.start}~{a.end} 노출·예상 수익을 읽어 보고만 한다.")
