#!/usr/bin/env python3
"""[제출] Cloudflare Workers Builds: 워커의 빌드 트리거 브랜치를 바꾼다(로그인된 대시보드 세션의 /api/v4).
wrangler OAuth·API 토큰엔 Builds 권한이 없어 대시보드 쿠키 + x-cross-site-security: dash 헤더로 부른다.

  cf_workers_build_branch.py mukmap main            # 지금 트리거 출력(DRY_RUN)
  cf_workers_build_branch.py mukmap main --submit   # branch_includes를 [main]으로 바꾼다
tmux -L gh 창에서 돌린다(기본 tmux 서버는 Chrome Apple 이벤트 -1743). 2026-10-28 mukmap cf-workers→main.
"""
import json, time
from _common import Blocked, emit, parser, run, tab
import chromectl as c

ap = parser(__doc__, submit=True)
ap.add_argument("worker")
ap.add_argument("branch")
ap.add_argument("--account", default="c023da92383ce204b357f6f18b86eb86")
ap.add_argument("--email", default="remin1994@gmail.com")
a = ap.parse_args()


# cf_pages_domain.py와 같은 대시보드 API 도우미
def api(tid, method, path, body=None):
    b = "undefined" if body is None else json.dumps(json.dumps(body))
    c.run_js(tid, f"""window.__r=null;fetch('/api/v4{path}',{{method:'{method}',credentials:'include',
      headers:{{'content-type':'application/json','x-cross-site-security':'dash'}},body:{b}}})
      .then(r=>r.text().then(x=>window.__r=r.status+' '+x)).catch(e=>window.__r='ERR '+e);1""")
    for _ in range(60):
        time.sleep(1)
        r = c.run_js(tid, "window.__r")
        if r and r not in ("null", "missing value"):
            st, _, txt = r.partition(" ")
            return int(st) if st.isdigit() else 0, (json.loads(txt) if txt.startswith("{") else txt)
    raise RuntimeError(f"api timeout {path}")


def login(tid):
    if "/login" not in c.run_js(tid, "location.href"):
        return
    c.fill(tid, "input[name=email],input[type=email]", a.email)
    c.fill(tid, "input[name=password],input[type=password]", c.secret("CLOUDFLARE_PASSWORD"))
    c.click(tid, "button[type=submit]"); time.sleep(12)
    if "two-factor-interstitial" in c.run_js(tid, "location.href"):
        c.rclick(tid, text="Skip for now"); time.sleep(8)
    if "/login" in c.run_js(tid, "location.href"):
        raise Blocked("LOGIN_FAILED (캡차·2단계 인증?)")




def main():
    with tab(f"https://dash.cloudflare.com/{a.account}/workers-and-pages", a) as tid:
        time.sleep(8); login(tid)
        # 트리거 API는 워커 이름이 아니라 스크립트 tag를 받는다(이름을 넣으면 빈 목록)
        _, sr = api(tid, "GET", f"/accounts/{a.account}/workers/scripts")
        tag = next((x.get("tag") for x in sr.get("result") or [] if x["id"] == a.worker), None)
        if not tag:
            raise Blocked(f"NO_WORKER {a.worker}")
        st, r = api(tid, "GET", f"/accounts/{a.account}/builds/workers/{tag}/triggers")
        if st != 200:
            raise RuntimeError(f"triggers {st} {r}")
        ts = r.get("result") or []
        if not ts:
            raise Blocked("NO_TRIGGER (대시보드에서 Git 연결 먼저)")
        out = []
        for t in ts:
            row = {"uuid": t["trigger_uuid"], "branch_includes": t.get("branch_includes"), "build": t.get("build_command"), "deploy": t.get("deploy_command")}
            if t.get("branch_includes") != [a.branch] and a.submit:
                st2, r2 = api(tid, "PATCH", f"/accounts/{a.account}/builds/triggers/{t['trigger_uuid']}", {"branch_includes": [a.branch]})
                row["patch"] = st2
                if st2 != 200:
                    raise RuntimeError(f"patch {st2} {r2}")
                row["after"] = (r2.get("result") or {}).get("branch_includes")
            out.append(row)
        emit({"triggers": out}, "SUBMITTED" if a.submit else "DRY_RUN", f"{a.worker} {a.branch}")


run(main, a, f"Cloudflare 대시보드에서 워커 {a.worker}의 Settings > Build > Branch control 운영 브랜치를 {a.branch}로 바꾼다. 다른 설정은 건드리지 않는다.")
