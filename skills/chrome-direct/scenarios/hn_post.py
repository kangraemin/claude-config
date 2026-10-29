#!/usr/bin/env python3
"""[Hacker News] 먹맵 계정 가입 + Show HN 게시 (멱등). Profile 7 "먹맵" 창. 기본 dry-run, --submit 일 때만 제출.

  hn_post.py --signup [--user mukmap] [--submit]      # 아이디·비번만으로 가입 (폼 acct/pw)
  hn_post.py --post --draft <초안.md> [--submit]       # news.ycombinator.com/submit

- ID/PW 는 ~/.claude/sns.env 의 MUK_HN_ID / MUK_HN_PW / MUK_HN_PROFILE. 값을 출력하지 않는다.
- 이미 MUK_HN_ID 가 있으면 --signup 은 RESULT: EXISTS. 게시된 URL 은 MUK_HN_LAST 에 저장해 중복 게시를 막는다.
- 보안문자가 뜨면 BLOCKED(사람이 읽는다). tmux -L gh 안에서 실행. 마지막 줄 RESULT:.
"""
import re, sys, time
from _common import emit, js, parser, poll, run, tab
from _muk import env_get, env_set, fill_js, newpw

ap = parser(__doc__)
ap.set_defaults(profile="Profile 7", no_fallback=True)
ap.add_argument("--signup", action="store_true")
ap.add_argument("--post", action="store_true")
ap.add_argument("--user", default="mukmap")
ap.add_argument("--draft")
ap.add_argument("--submit", action="store_true")
ap.add_argument("--login", action="store_true")
a = ap.parse_args()
a.no_fallback = True


def draft_parts(path):
    t = open(path).read()
    title = re.search(r"## 제목\n(.+)", t).group(1).strip()
    url = re.search(r"링크 1개: (\S+)", t).group(1)
    body = t.split("## 본문")[1].split("\n", 1)[1].strip()
    return title, url, body


def signup():
    if env_get("MUK_HN_ID"):
        emit({}, "EXISTS", "이미 가입됨")
        return
    user, pw = a.user, newpw()
    with tab("https://news.ycombinator.com/login?goto=news", a) as tid:
        time.sleep(2)
        # 두 번째 폼(creating=t)이 가입 폼
        r = js(tid, """const fs=[...document.forms].filter(f=>f.querySelector('input[name=creating]'));
          const f=fs[fs.length-1]; if(!f) return 'NOFORM';
          const acct=f.querySelector('input[name=acct]'), pw=f.querySelector('input[name=pw]');
          acct.value=%s; pw.value=%s; return 'filled'""" % (repr(user).replace("'", '"'), repr(pw).replace("'", '"')))
        if r != "filled":
            emit({"r": r}, "FAIL", "가입 폼 못 찾음")
            raise SystemExit(1)
        if not a.submit:
            emit({}, "OK", "dry-run 폼 채우기까지")
            return
        env_set("MUK_HN_ID", user); env_set("MUK_HN_PW", pw); env_set("MUK_HN_PROFILE", "Profile 7")
        js(tid, """const fs=[...document.forms].filter(f=>f.querySelector('input[name=creating]'));
          fs[fs.length-1].submit(); return 1""")
        time.sleep(4)
        st = js(tid, "return {u:location.href, t:document.body.innerText.slice(0,400), logged:!!document.getElementById('me')}")
        emit({"url": st["u"], "text": st["t"], "logged": st["logged"]}, "SUBMITTED" if st["logged"] else "CHECK", "가입 결과")


def post():
    title, url, body = draft_parts(a.draft)
    if env_get("MUK_HN_LAST"):
        emit({"last": env_get("MUK_HN_LAST")}, "EXISTS", "이미 게시함")
        return
    with tab("https://news.ycombinator.com/submit", a) as tid:
        time.sleep(2)
        st = js(tid, "return {u:location.href, form:!!document.querySelector('input[name=title]'), t:document.body.innerText.slice(0,200)}")
        if not st["form"]:
            emit(st, "BLOCKED", "로그인 안 됨 — hn_post.py --login 필요")
            raise SystemExit(2)
        js(tid, fill_js("input[name=title]", title)); js(tid, fill_js("input[name=url]", url))
        if not a.submit:
            emit({"title": title, "url": url}, "OK", "dry-run 폼 채우기까지")
            return
        js(tid, "document.querySelector('input[type=submit]').click(); return 1")
        time.sleep(5)
        st = js(tid, "return {u:location.href, t:document.body.innerText.slice(0,300)}")
        emit(st, "SUBMITTED", "게시 결과 — 첫 댓글은 --comment")


def login():
    with tab("https://news.ycombinator.com/login?goto=news", a) as tid:
        time.sleep(2)
        js(tid, fill_js("form input[name=acct]", env_get("MUK_HN_ID"))); 
        js(tid, """const f=document.forms[0]; f.querySelector('input[name=acct]').value=%s; f.querySelector('input[name=pw]').value=%s; f.submit(); return 1""" % (repr(env_get("MUK_HN_ID")).replace("'", '"'), repr(env_get("MUK_HN_PW")).replace("'", '"')))
        time.sleep(4)
        st = js(tid, "return {u:location.href, logged:!!document.getElementById('me'), t:document.body.innerText.slice(0,200)}")
        emit({"logged": st["logged"], "t": st["t"]}, "OK" if st["logged"] else "FAIL")


run(lambda *_: (login() if a.login else signup() if a.signup else post()), a, "HN")
