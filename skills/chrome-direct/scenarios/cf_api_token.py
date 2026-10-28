#!/usr/bin/env python3
"""[제출] Cloudflare: 로그인된 대시보드 세션 /api/v4로 사용자 API 토큰을 만든다(권한 그룹 이름으로 지정).
기존 토큰에 KV·Routes 같은 권한이 없을 때 CI(GitHub Actions) 배포용 토큰을 사람 손 없이 만든다.

  cf_api_token.py ai-paper-deploy --account-perms "Workers Scripts Write,Workers KV Storage Write" \
      --zone paper-digest.app --zone-perms "Workers Routes Write,DNS Write,Zone Read"          # DRY_RUN: 권한 그룹 id만 확인
  cf_api_token.py ... --out /tmp/cf_token --submit                                                # 토큰 생성, 값은 --out 파일(600)에만
  그 뒤: gh secret set CLOUDFLARE_API_TOKEN < /tmp/cf_token && rm /tmp/cf_token
같은 이름 토큰이 이미 있으면 지우지 않고 새로 하나 더 만든다(값은 생성 때만 나온다).
2026-10-28 ai-paper(paper-digest.app) Vercel→Workers 이관 때 GitHub Actions 배포 토큰으로 만듦(tmux -L gh 창에서 실행).
"""
import json, os, time
from _common import Blocked, emit, parser, run, tab
import chromectl as c

ap = parser(__doc__, submit=True)
ap.add_argument("name", help="토큰 이름")
ap.add_argument("--account", default="c023da92383ce204b357f6f18b86eb86")
ap.add_argument("--account-perms", default="", help="계정 범위 권한 그룹 이름, 쉼표로")
ap.add_argument("--zone", help="zone 범위 권한을 줄 도메인")
ap.add_argument("--zone-perms", default="", help="zone 범위 권한 그룹 이름, 쉼표로")
ap.add_argument("--out", help="토큰 값을 쓸 파일(권한 600). --submit이면 필수")
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


def names(s):
    return [x.strip() for x in s.split(",") if x.strip()]


def main():
    with tab(f"https://dash.cloudflare.com/{a.account}/home", a) as tid:
        time.sleep(8); login(tid)
        st, r = api(tid, "GET", "/user/tokens/permission_groups")
        if st != 200:
            raise RuntimeError(f"권한 그룹 조회 실패 {st} {r}")
        by_name = {}
        for g in r["result"]:
            by_name.setdefault(g["name"], []).append(g)

        def pick(want, scope):
            out = []
            for n in want:
                g = [x for x in by_name.get(n, []) if any(scope in s for s in x.get("scopes", []))]
                if not g:
                    raise RuntimeError(f"권한 그룹 없음: {n} ({scope})")
                out.append({"id": g[0]["id"], "name": n})
            return out

        policies = []
        acc = pick(names(a.account_perms), "com.cloudflare.api.account")
        if acc:
            policies.append({"effect": "allow", "permission_groups": [{"id": x["id"]} for x in acc],
                             "resources": {f"com.cloudflare.api.account.{a.account}": "*"}})
        zone_id = None
        zp = pick(names(a.zone_perms), "com.cloudflare.api.account.zone")
        if zp:
            _, zr = api(tid, "GET", f"/zones?name={a.zone}")
            zone_id = (zr.get("result") or [{}])[0].get("id")
            if not zone_id:
                raise RuntimeError(f"zone 없음 {a.zone}")
            policies.append({"effect": "allow", "permission_groups": [{"id": x["id"]} for x in zp],
                             "resources": {f"com.cloudflare.api.account.zone.{zone_id}": "*"}})
        info = {"name": a.name, "account_perms": acc, "zone": a.zone, "zone_id": zone_id, "zone_perms": zp}
        if not a.submit:
            emit(info, "DRY_RUN", "토큰을 만들려면 --out <파일> --submit"); return
        if not a.out:
            raise RuntimeError("--out 필요")
        st, r = api(tid, "POST", "/user/tokens", {"name": a.name, "policies": policies})
        if st != 200:
            raise RuntimeError(f"토큰 생성 실패 {st} {r}")
        fd = os.open(a.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(r["result"]["value"])
        emit({**info, "token_id": r["result"]["id"], "out": a.out}, "OK", f"토큰 값은 {a.out}에만 저장")


run(main, a, f"Cloudflare 대시보드 > My Profile > API Tokens에서 '{a.name}' 토큰을 만든다. 계정 권한: {a.account_perms}. "
             f"zone {a.zone} 권한: {a.zone_perms}. 값은 {a.out} 파일에 저장.")
