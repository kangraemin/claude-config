#!/usr/bin/env python3
"""[제출] Cloudflare: 도메인을 zone으로 추가하고 Pages 프로젝트에 apex·www를 붙인다(로그인된 대시보드 세션의 /api/v4).
CLOUDFLARE_API_TOKEN에 Zone·Pages 권한이 없어도 된다(대시보드 쿠키 + x-cross-site-security: dash 헤더).

  cf_pages_domain.py xn--ob0butqet42c6pmgpe.kr geulmagam            # 무엇을 할지 출력(DRY_RUN)
  cf_pages_domain.py xn--ob0butqet42c6pmgpe.kr geulmagam --submit   # zone 추가, CNAME 2개, Pages 도메인 2개, www→apex 301, Always HTTPS
출력 NAMESERVERS a b → 등록기관 네임서버를 이것으로 바꾼다(가비아: gabia_nameserver.py).
로그아웃이면 CLOUDFLARE_PASSWORD(~/.claude/.env)로 로그인하고 2단계 인증 안내는 'Skip for now'.
2026-10-28 글쓰기공모전.kr에 같은 순서로 실행(tmux -L gh 창에서 — 기본 tmux 서버는 Chrome Apple 이벤트 -1743).
"""
import json, time
from _common import Blocked, emit, parser, run, tab
import chromectl as c

ap = parser(__doc__, submit=True)
ap.add_argument("domain", help="punycode 도메인")
ap.add_argument("project", help="Pages 프로젝트 이름(먼저 wrangler pages project create)")
ap.add_argument("--account", default="c023da92383ce204b357f6f18b86eb86")
ap.add_argument("--email", default="remin1994@gmail.com")
a = ap.parse_args()


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
    D = a.domain
    with tab(f"https://dash.cloudflare.com/{a.account}/home/domains", a) as tid:
        time.sleep(8); login(tid)
        _, r = api(tid, "GET", f"/zones?name={D}")
        zone = (r.get("result") or [None])[0]
        if not a.submit:
            emit({"zone": zone and zone["id"]}, "DRY_RUN", "zone 추가·CNAME·Pages 도메인·www 리다이렉트를 하려면 --submit"); return
        if not zone:
            st, r = api(tid, "POST", "/zones", {"name": D, "account": {"id": a.account}, "type": "full", "jump_start": False})
            if st != 200: raise RuntimeError(f"zone 추가 실패 {r}")
            zone = r["result"]
        Z = zone["id"]
        _, recs = api(tid, "GET", f"/zones/{Z}/dns_records?type=CNAME")
        have = {x["name"] for x in recs.get("result", [])}
        for n in (D, "www." + D):
            if n not in have:
                api(tid, "POST", f"/zones/{Z}/dns_records", {"type": "CNAME", "name": n, "content": f"{a.project}.pages.dev", "proxied": True, "ttl": 1})
            api(tid, "POST", f"/accounts/{a.account}/pages/projects/{a.project}/domains", {"name": n})  # 이미 있으면 409, 무시
        api(tid, "PUT", f"/zones/{Z}/rulesets/phases/http_request_dynamic_redirect/entrypoint", {"rules": [{
            "expression": f'(http.host eq "www.{D}")', "description": "www to apex", "action": "redirect",
            "action_parameters": {"from_value": {"status_code": 301, "preserve_query_string": True,
                                  "target_url": {"expression": f'concat("https://{D}", http.request.uri.path)'}}}}]})
        api(tid, "PATCH", f"/zones/{Z}/settings/always_use_https", {"value": "on"})
        emit({"zone": Z, "status": zone.get("status"), "name_servers": zone["name_servers"]}, "OK",
             "NAMESERVERS " + " ".join(zone["name_servers"]))


run(main, a, f"Cloudflare 대시보드(계정 {a.account})에서 {a.domain} 사이트를 Free 플랜으로 추가하고, Pages 프로젝트 {a.project}의 Custom domains에 {a.domain}·www.{a.domain}를 붙인다. 배정된 네임서버 2개를 출력.")
