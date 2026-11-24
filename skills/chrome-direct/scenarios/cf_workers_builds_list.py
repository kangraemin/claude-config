#!/usr/bin/env python3
"""[조회] Cloudflare Workers Builds: 워커의 최근 빌드 기록(시각·상태·결과·브랜치·커밋)을 보여 준다(대시보드 세션 /api/v4).
wrangler OAuth·API 토큰엔 Builds 권한이 없다(12004 Forbidden).

  cf_workers_builds_list.py mukmap-dev            # 최근 5개
  cf_workers_builds_list.py mukmap-dev --log      # 맨 위 빌드 로그 끝부분도
  cf_workers_builds_list.py mukmap-dev --run dev   # [제출] 그 가지 최신 커밋으로 빌드를 새로 돌린다(빌드 환경변수 고친 뒤 등)
tmux -L gh 창에서 돌린다. 2026-11-25 mukmap-dev가 dev 푸시 뒤에도 배포가 안 바뀌어 만듦.
"""
import json, time
from _common import Blocked, emit, parser, run, tab
import chromectl as c

ap = parser(__doc__)
ap.add_argument("worker")
ap.add_argument("--n", type=int, default=5)
ap.add_argument("--log", action="store_true")
ap.add_argument("--run", metavar="BRANCH")
ap.add_argument("--account", default="c023da92383ce204b357f6f18b86eb86")
a = ap.parse_args()


def api(tid, path, body=None):
    m = "GET" if body is None else "POST"
    b = "undefined" if body is None else json.dumps(json.dumps(body))
    c.run_js(tid, f"""window.__r=null;fetch('/api/v4{path}',{{method:'{m}',credentials:'include',headers:{{'content-type':'application/json','x-cross-site-security':'dash'}},body:{b}}})
      .then(r=>r.text().then(x=>window.__r=r.status+' '+x)).catch(e=>window.__r='ERR '+e);1""")
    for _ in range(60):
        time.sleep(1)
        r = c.run_js(tid, "window.__r")
        if r and r not in ("null", "missing value"):
            st, _, txt = r.partition(" ")
            return int(st) if st.isdigit() else 0, (json.loads(txt) if txt.startswith("{") else txt)
    raise RuntimeError(f"api timeout {path}")


def main():
    with tab(f"https://dash.cloudflare.com/{a.account}/workers-and-pages", a) as tid:
        time.sleep(8)
        if "/login" in c.run_js(tid, "location.href"):
            raise Blocked("LOGIN_REQUIRED (cf_workers_build_branch.py가 로그인한다)")
        _, sr = api(tid, f"/accounts/{a.account}/workers/scripts")
        tag = next((x.get("tag") for x in sr.get("result") or [] if x["id"] == a.worker), None)
        if not tag:
            raise Blocked(f"NO_WORKER {a.worker}")
        if a.run:
            st, tr = api(tid, f"/accounts/{a.account}/builds/workers/{tag}/triggers")
            t = next((x for x in tr.get("result") or [] if a.run in (x.get("branch_includes") or [])), None)
            if not t:
                raise Blocked(f"NO_TRIGGER_FOR {a.run}")
            st, rr = api(tid, f"/accounts/{a.account}/builds/triggers/{t['trigger_uuid']}/builds", {"branch": a.run})
            if st not in (200, 201):
                raise RuntimeError(f"run {st} {str(rr)[:300]}")
            time.sleep(3)
        st, r = api(tid, f"/accounts/{a.account}/builds/workers/{tag}/builds?per_page={a.n}")
        if st != 200:
            raise RuntimeError(f"builds {st} {str(r)[:300]}")
        rows = []
        for b in (r.get("result") or [])[: a.n]:
            m = b.get("build_trigger_metadata") or {}
            rows.append({"uuid": b.get("build_uuid"), "created": b.get("created_on"), "status": b.get("status"),
                         "outcome": b.get("build_outcome"), "branch": m.get("branch"), "commit": (m.get("commit_hash") or "")[:7],
                         "message": (m.get("commit_message") or "")[:60]})
        out = {"builds": rows}
        if a.log and rows:
            st, lg = api(tid, f"/accounts/{a.account}/builds/builds/{rows[0]['uuid']}/logs")
            lines = (lg.get("result") or {}).get("lines") if isinstance(lg, dict) else None
            out["log_tail"] = [l[1] if isinstance(l, list) else l for l in (lines or [])][-40:] or str(lg)[:1500]
        emit(out, "OK", a.worker)


run(main, a, f"Cloudflare 대시보드 워커 {a.worker}의 Deployments/Builds 기록을 읽기만 한다.")
