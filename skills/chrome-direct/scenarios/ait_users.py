#!/usr/bin/env python3
"""[읽기] 앱인토스 콘솔 — 앱별 일별 사용자 수(DAU)·신규·유입 경로.

  ait_users.py oneul-tarot-card son-calendar               # 최근 7일
  ait_users.py son-calendar --from 2026-10-15 --to 2026-10-22
콘솔 '홈 대시보드'가 부르는 API(POST .../mini-app/{app}/analytics/au, 본문 {timeUnit,startDate,endDate})를 로그인 탭 안 XHR로 읽는다.
앱은 appName(예: byeoljari-unse)으로만 부른다. miniAppId(숫자)를 넣으면 4031. 사용자가 없는 날은 au가 빈 {}로 온다(오류 아님).
본문 키는 timeUnit (timeUnitType 이면 4000, GET 이면 500). 집계는 하루 단위, 오늘 값은 캐시(cacheTime) 기준.
"""
import datetime as dt
import json

from _ait import url, wait_page
from _common import emit, js, parser, run, tab

ap = parser(__doc__)
ap.add_argument("apps", nargs="+")
ap.add_argument("--from", dest="start", default=(dt.date.today() - dt.timedelta(days=6)).isoformat())
ap.add_argument("--to", dest="end", default=dt.date.today().isoformat())
ap.add_argument("--workspace", default="35273")
a = ap.parse_args()


def main():
    with tab(url(a.workspace, a.apps[0], "home"), a) as tid:
        wait_page(tid, "홈")
        out = []
        body = json.dumps({"timeUnit": "DAY", "startDate": a.start, "endDate": a.end})
        for app in a.apps:
            api = f"/console/api-public/v3/appsintossconsole/workspaces/{a.workspace}/mini-app/{app}/analytics/au"
            res = js(tid, f"var x=new XMLHttpRequest();x.open('POST',{api!r},false);x.setRequestHeader('Content-Type','application/json');x.send({body!r});return JSON.parse(x.responseText)")
            s = res.get("success") or {}
            au = {d["dateKey"]: d["value"] for d in s.get("au") or []}
            new = {d["dateKey"]: d["value"] for d in s.get("newAu") or []}
            ref = {}
            for d in s.get("referrer") or []:
                ref[d["dimension"]] = ref.get(d["dimension"], 0) + d["value"]
            print(f"USERS {app} 일별 {au} 신규 {sum(new.values())} 유입 {ref}" + ("" if s else f" ERROR {res.get('error')}"))
            out.append({"app": app, "au": au, "new": new, "referrer": ref})
        emit({"from": a.start, "to": a.end, "apps": out}, "OK", f"{len(out)}개 앱 ({a.start}~{a.end})")


run(main, a, f"READ ONLY. 앱인토스 콘솔 {a.apps} 홈 대시보드의 {a.start}~{a.end} 일별 사용자 수를 읽어 보고만 한다.")
