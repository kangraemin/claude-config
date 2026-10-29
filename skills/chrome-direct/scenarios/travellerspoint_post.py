#!/usr/bin/env python3
"""[Travellerspoint] 먹맵 계정 가입 + 포럼 글 (멱등). Profile 7 "먹맵" 창. 기본 dry-run, --submit 일 때만 제출.

  travellerspoint_post.py --signup [--submit]     # 이메일+아이디(15자)+비번+약관 체크, 회사 계정 체크 안 함
  travellerspoint_post.py --verify                # 가입 뒤 메일 인증 링크 열기(gmail_code.py)
  travellerspoint_post.py --login
  travellerspoint_post.py --probe-post            # 로그인 뒤 포럼 새 글 화면 구조 확인(제출 안 함)

- ID/PW: ~/.claude/sns.env MUK_TRAVELLERSPOINT_ID/_PW/_PROFILE/_EMAIL. 값 출력 금지. 있으면 RESULT: EXISTS.
- 실제 가입 폼(2026-10-30): email, username(max 15), password, terms 체크, isBusiness 체크(건드리지 않음). 캡차 없음.
tmux -L gh 안에서 실행. 마지막 줄 RESULT:.
"""
import json, subprocess, sys, time
from _common import emit, js, parser, run, tab
from _muk import env_get, env_set, fill_js, newpw

ap = parser(__doc__)
ap.set_defaults(profile="Profile 7", no_fallback=True)
for f in ("--signup", "--verify", "--login", "--probe-post", "--submit"):
    ap.add_argument(f, action="store_true")
ap.add_argument("--user", default="mukmap_kr")
ap.add_argument("--email", default="remin1994+mukmap@gmail.com")
a = ap.parse_args()
a.no_fallback = True
CODE = __file__.replace("travellerspoint_post.py", "gmail_code.py")


def signup():
    if env_get("MUK_TRAVELLERSPOINT_ID"):
        emit({}, "EXISTS", "이미 가입됨"); return
    pw = newpw()
    with tab("https://www.travellerspoint.com/signup/", a) as tid:
        time.sleep(2)
        for sel, v in (("#email", a.email), ("#username", a.user), ("#password", pw)):
            js(tid, fill_js(sel, v))
        js(tid, "const c=document.getElementById('accept-terms'); if(!c.checked) c.click(); return c.checked")
        if not a.submit:
            emit({}, "OK", "dry-run 폼 채우기까지"); return
        env_set("MUK_TRAVELLERSPOINT_ID", a.user); env_set("MUK_TRAVELLERSPOINT_PW", pw)
        env_set("MUK_TRAVELLERSPOINT_EMAIL", a.email); env_set("MUK_TRAVELLERSPOINT_PROFILE", "Profile 7")
        js(tid, "const b=[...document.querySelectorAll('button,input[type=submit]')].find(b=>/Join Travellerspoint/i.test(b.innerText||b.value)); b.click(); return 1")
        time.sleep(6)
        st = js(tid, "return {u:location.href,t:document.body.innerText.slice(0,500)}")
        emit(st, "SUBMITTED", "가입 결과 — 이어서 --verify")


def verify():
    out = subprocess.run([sys.executable, CODE, "from:travellerspoint", "--newer", "30m", "--link", "travellerspoint.com"], capture_output=True, text=True).stdout
    link = next((l[5:] for l in out.splitlines() if l.startswith("LINK ")), None)
    if not link:
        emit({"out": out[-300:]}, "NONE", "인증 메일 링크 없음"); raise SystemExit(1)
    with tab(link, a) as tid:
        time.sleep(4)
        emit({"t": js(tid, "return document.body.innerText.slice(0,300)")}, "VERIFIED")


def login():
    with tab("https://www.travellerspoint.com/login/", a) as tid:
        time.sleep(2)
        js(tid, fill_js("input[type=email],input[name=email],input[name=username]", env_get("MUK_TRAVELLERSPOINT_EMAIL")))
        js(tid, fill_js("input[type=password]", env_get("MUK_TRAVELLERSPOINT_PW")))
        js(tid, "const b=[...document.querySelectorAll('button,input[type=submit]')].find(b=>/log ?in/i.test(b.innerText||b.value)); b.click(); return 1")
        time.sleep(5)
        emit({"u": js(tid, "return location.href")}, "OK")


def probe_post():
    with tab("https://www.travellerspoint.com/forum/", a) as tid:
        time.sleep(3)
        emit(js(tid, "return {u:location.href,links:[...document.querySelectorAll('a')].map(x=>x.innerText.trim()+' '+x.getAttribute('href')).filter(x=>/asia|korea|new|post/i.test(x)).slice(0,25)}"), "OK")


run(lambda *_: (signup() if a.signup else verify() if a.verify else login() if a.login else probe_post()), a, "Travellerspoint")
