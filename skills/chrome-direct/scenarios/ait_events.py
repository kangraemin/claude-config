#!/usr/bin/env python3
"""[읽기] 앱인토스 콘솔 — 앱별 이벤트 목록과 최근 14일 발생 수.

  ait_events.py byeoljari-unse son-calendar                 # 앱마다 이벤트 이름·유형·14일 건수
  ait_events.py byeoljari-unse --grep ad_                   # 이름에 ad_ 가 들어간 것만
콘솔 '유입·성장 > 이벤트'(…/mini-app/{app}/event/list)가 부르는 API(POST .../mini-app/{app}/log/catalogs/search, 본문 {})를 로그인 탭 안 XHR로 읽는다.
GET 이면 500. 화면의 '새로고침'은 이 API를 다시 부르지 않는다. 파라미터 값(예: status=no_fill)별 건수는 이 API에 없다.
쓸모: 앱 사용량 대비 광고 노출이 정상인지(app_open 대비 display_ads_all::impression__1px_banner), 직접 넣은 track() 이벤트가 들어오는지.
"""
import json

from _ait import url, wait_page
from _common import emit, js, parser, run, tab

ap = parser(__doc__)
ap.add_argument("apps", nargs="+")
ap.add_argument("--grep", default="")
ap.add_argument("--workspace", default="35273")
a = ap.parse_args()


def main():
    with tab(url(a.workspace, a.apps[0], "event/list"), a) as tid:
        wait_page(tid, "이벤트")
        out = []
        for app in a.apps:
            api = f"/console/api-public/v3/appsintossconsole/workspaces/{a.workspace}/mini-app/{app}/log/catalogs/search"
            res = js(tid, f"var x=new XMLHttpRequest();x.open('POST',{api!r},false);x.setRequestHeader('Content-Type','application/json');x.send('{{}}');return JSON.parse(x.responseText)")
            rows = [r for r in ((res.get("success") or {}).get("results") or []) if a.grep in r["logName"]]
            ev = {r["logName"]: r["cnt14D"] for r in rows}
            print(f"EVENTS {app} {json.dumps(ev, ensure_ascii=False)}" + ("" if res.get("success") else f" ERROR {res.get('error')}"))
            out.append({"app": app, "events": rows})
        emit({"apps": out}, "OK", f"{len(out)}개 앱 이벤트 (최근 14일)")


run(main, a, f"READ ONLY. 앱인토스 콘솔 {a.apps} 이벤트 화면의 이벤트별 최근 14일 건수를 읽어 보고만 한다.")
