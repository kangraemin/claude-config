#!/usr/bin/env python3
"""[제출] Cloudflare: 도메인을 zone으로 추가하고 Pages 프로젝트에 apex·www를 붙인다(로그인된 대시보드 세션의 /api/v4).
CLOUDFLARE_API_TOKEN에 Zone·Pages 권한이 없어도 된다(대시보드 쿠키 + x-cross-site-security: dash 헤더).

  cf_pages_domain.py xn--ob0butqet42c6pmgpe.kr geulmagam            # 무엇을 할지 출력(DRY_RUN)
  cf_pages_domain.py xn--ob0butqet42c6pmgpe.kr geulmagam --submit   # zone 추가, CNAME 2개, Pages 도메인 2개, www→apex 301, Always HTTPS
  cf_pages_domain.py mukmap.kr --zone-only --submit   # zone만(DNS 스캔으로 TXT·MX 유지, 옛 A/CNAME 삭제). Worker Custom Domain은 wrangler로(2026-10-28 mukmap)
  cf_pages_domain.py eodimeok.kr eodimeok --routes "eodimeok=/*;eodimeok-intl=/en*,/ja*,/zh-cn*,/zh-tw*" --submit
      # Pages 대신 Workers(정적 자산) 경로 라우팅: AAAA 100::(proxied) 2개 + 워커 라우트(더 긴 패턴이 이긴다).
      # 커스텀 도메인은 라우트보다 우선이라 경로를 나누는 워커에는 쓰지 않는다(2026-10-28 eodimeok).
출력 NAMESERVERS a b → 등록기관 네임서버를 이것으로 바꾼다(가비아: gabia_nameserver.py).
로그아웃이면 CLOUDFLARE_PASSWORD(~/.claude/.env)로 로그인하고 2단계 인증 안내는 'Skip for now'.
2026-10-28 글쓰기공모전.kr에 같은 순서로 실행(tmux -L gh 창에서 — 기본 tmux 서버는 Chrome Apple 이벤트 -1743).
"""
import json, time
from _common import Blocked, emit, parser, run, tab
import chromectl as c

ap = parser(__doc__, submit=True)
ap.add_argument("domain", help="punycode 도메인")
ap.add_argument("project", nargs="?", help="Pages 프로젝트 이름(먼저 wrangler pages project create). --zone-only면 생략")
ap.add_argument("--zone-only", action="store_true", help="zone만 추가: DNS 스캔으로 TXT·MX 등은 가져오고 apex·www의 A/AAAA/CNAME(옛 호스팅)은 지운다. Worker Custom Domain은 wrangler가 붙인다")
ap.add_argument("--account", default="c023da92383ce204b357f6f18b86eb86")
ap.add_argument("--routes", help='워커 모드: "워커=/경로*,...;워커2=/..."')
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
            st, r = api(tid, "POST", "/zones", {"name": D, "account": {"id": a.account}, "type": "full", "jump_start": a.zone_only})
            if st != 200: raise RuntimeError(f"zone 추가 실패 {r}")
            zone = r["result"]
        Z = zone["id"]
        # API로 만든 zone은 플랜이 없어 'initializing'에 멈춘다(NS를 바꿔도 활성화 안 됨, 10/28 90분 정체) → Free 구독을 붙인다
        api(tid, "POST", f"/zones/{Z}/subscription", {"rate_plan": {"id": "free"}, "frequency": "monthly"})  # 이미 있으면 에러, 무시
        # 구독만으론 그대로였다. 대시보드가 /select-plan으로 보내면 Free의 'Select plan'을 실제 클릭해야 pending으로 넘어간다
        c.goto(tid, f"https://dash.cloudflare.com/{a.account}/{D}"); time.sleep(12)
        if "/select-plan" in c.run_js(tid, "location.href"):
            c.run_js(tid, """(()=>{const b=[...document.querySelectorAll('button,a')].filter(e=>e.offsetParent&&e.innerText.trim()=='Select plan')[0];
              b.setAttribute('data-cx','1');b.scrollIntoView({block:'center'});return 1})()""")  # 첫 카드 = Free
            c.front(tid); c.rclick(tid, "[data-cx='1']"); time.sleep(12)
        api(tid, "PUT", f"/zones/{Z}/activation_check")  # NS를 이미 바꿨으면 바로 확인
        if a.zone_only:
            _, recs = api(tid, "GET", f"/zones/{Z}/dns_records?per_page=100")
            for x in recs.get("result", []):
                if x["name"] in (D, "www." + D) and x["type"] in ("A", "AAAA", "CNAME"):
                    api(tid, "DELETE", f"/zones/{Z}/dns_records/{x['id']}"); print("DELETED", x["type"], x["name"], x["content"])
            _, recs = api(tid, "GET", f"/zones/{Z}/dns_records?per_page=100")
            print("KEPT", sorted({(x["type"], x["name"]) for x in recs.get("result", [])}))
            emit({"zone": Z, "status": zone.get("status"), "name_servers": zone["name_servers"]}, "OK",
                 "NAMESERVERS " + " ".join(zone["name_servers"]))
            return
        if a.routes:
            _, recs = api(tid, "GET", f"/zones/{Z}/dns_records")
            have = {x["name"] for x in recs.get("result", [])}
            for n in (D, "www." + D):
                if n not in have:
                    api(tid, "POST", f"/zones/{Z}/dns_records", {"type": "AAAA", "name": n, "content": "100::", "proxied": True, "ttl": 1})
            _, rr = api(tid, "GET", f"/zones/{Z}/workers/routes")
            had = {x["pattern"] for x in rr.get("result", [])}
            for part in a.routes.split(";"):
                w, paths = part.split("=")
                for path in paths.split(","):
                    if D + path not in had:
                        st, r = api(tid, "POST", f"/zones/{Z}/workers/routes", {"pattern": D + path, "script": w})
                        if st != 200: raise RuntimeError(f"route 실패 {D + path} {r}")
        _, recs = api(tid, "GET", f"/zones/{Z}/dns_records?type=CNAME")
        have = {x["name"] for x in recs.get("result", [])}
        for n in (() if a.routes else (D, "www." + D)):
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
