#!/usr/bin/env python3
"""[제출] GCP Google Auth Platform: 동의 화면(External)·브랜딩·범위·프로덕션 게시·웹 OAuth 클라이언트를 만든다.

  gcp_oauth_web_client.py <project> --name "앱 이름" --home https://site/ --privacy https://site/privacy \
      --origin https://site --origin http://localhost:4791 [--scope https://www.googleapis.com/auth/drive.appdata] [--submit]
마지막 줄 RESULT: OK CLIENT_ID <id>. 이미 클라이언트가 있으면 만들지 않고 ID만 출력한다. 시크릿은 읽지 않는다.
프로젝트·API 사용 설정은 gcloud로 먼저(gcloud projects create / services enable). 비민감 범위만 쓰면 심사 없이 게시된다.
Angular 폼이라 값은 네이티브 setter+input 이벤트, cfc-select는 pointer 이벤트로 연다. 2026-10-31 threads-unfollow-web 검증.
"""
import re, time
from _common import Blocked, emit, parser, run, tab
import chromectl as c

ap = parser(__doc__, submit=True)
ap.add_argument("project")
ap.add_argument("--name", required=True)
ap.add_argument("--email", default="remin1994@gmail.com")
ap.add_argument("--home", required=True)
ap.add_argument("--privacy", required=True)
ap.add_argument("--origin", action="append", required=True)
ap.add_argument("--scope", action="append", default=[])
a = ap.parse_args()
U = lambda p: f"https://console.cloud.google.com/auth/{p}?project={a.project}"

H = r"""
window.__p=(e)=>{for(const k of ['pointerdown','mousedown','pointerup','mouseup','click'])e.dispatchEvent(new MouseEvent(k,{bubbles:true}))};
window.__b=(t)=>[...document.querySelectorAll('button,a')].find(b=>b.offsetParent&&b.innerText.trim()===t);
window.__v=(e,v)=>{e.focus();Object.getOwnPropertyDescriptor(Object.getPrototypeOf(e),'value').set.call(e,v);
  for(const k of ['input','change','blur'])e.dispatchEvent(new Event(k,{bubbles:true}))};
"""
uesc = lambda s: "".join(ch if ord(ch) < 128 else "\\u%04x" % ord(ch) for ch in s).replace("'", "\\'")


def js(t, code):
    return c.run_js(t, H + code, timeout=60)


def go(t, p):
    c.goto(t, U(p)); time.sleep(6)


def click(t, text, wait=2):
    r = js(t, f"const b=__b('{text}'); b? (b.click(),'ok') : 'NF'"); time.sleep(wait); return r


def client_ids(t):
    # 목록은 ID를 줄여 보여 준다. 링크 주소에서 읽는다
    hrefs = js(t, "[...document.querySelectorAll('a[href*=\"clients/\"]')].map(a=>a.getAttribute('href')).join(' ')") or ""
    return sorted(set(re.findall(r"\d+-[a-z0-9]+\.apps\.googleusercontent\.com", hrefs + " " + c.page_text(t))))


def main():
    with tab(U("overview"), a) as t:
        txt = c.page_text(t)
        if "not configured yet" in txt:
            if not a.submit:
                emit({"project": a.project}, "DRY_RUN", "consent screen not configured"); return
            click(t, "Get started", 4)
            js(t, f"__v(document.querySelector('input[formcontrolname=displayName]'),'{uesc(a.name)}');"
                  "__p(document.querySelector('cfc-select[formcontrolname=userSupportEmail]'))"); time.sleep(1.5)
            js(t, f"__p([...document.querySelectorAll('[role=option]')].find(o=>o.innerText.trim()==='{a.email}'))"); time.sleep(1)
            click(t, "Next")
            js(t, "document.querySelector('input[type=radio][value=external]').click()"); click(t, "Next")
            js(t, f"const e=document.querySelector('input[aria-label=\"Text field for emails\"]');__v(e,'{a.email}');"
                  "for(const k of ['keydown','keyup'])e.dispatchEvent(new KeyboardEvent(k,{key:'Enter',keyCode:13,bubbles:true}))")
            time.sleep(1); click(t, "Next")
            js(t, "document.querySelector('mat-checkbox input[type=checkbox]').click()"); click(t, "Continue")
            click(t, "Create", 6)
        # 브랜딩: 이름 없는 입력 첫 두 칸 = 홈페이지·개인정보
        go(t, "branding")
        js(t, f"const i=[...document.querySelectorAll('input')].filter(e=>e.offsetParent&&!e.getAttribute('formcontrolname')&&!e.getAttribute('aria-label'));"
              f"__v(i[0],'{a.home}');__v(i[1],'{a.privacy}')")
        if a.submit: click(t, "Save", 4)
        if a.scope:
            go(t, "scopes")
            if not all(s.rsplit('/', 1)[-1] in c.page_text(t) for s in a.scope):
                click(t, "Add or remove scopes", 3)
                js(t, f"__v(document.querySelector('textarea[aria-label=\"Manually paste scopes\"]'),'{' '.join(a.scope)}')")
                click(t, "Add to table"); click(t, "Update", 3)
                if a.submit: click(t, "Save", 4)
        go(t, "audience")
        if "In production" not in c.page_text(t) and a.submit:
            click(t, "Publish app"); click(t, "Confirm", 6)
        go(t, "clients")
        ids = client_ids(t)
        if not ids and a.submit:
            go(t, "clients/create")
            js(t, "__p(document.querySelector('cfc-select[formcontrolname=typeControl]'))"); time.sleep(1.5)
            js(t, "__p([...document.querySelectorAll('[role=option]')].find(o=>o.innerText.trim()==='Web application'))"); time.sleep(2)
            js(t, f"__v(document.querySelector('input[formcontrolname=displayName]'),'{a.project} web')")
            for i, o in enumerate(a.origin):
                js(t, "__p([...document.querySelectorAll('button')].filter(b=>/Add URI/.test(b.innerText))[0])"); time.sleep(1)
                js(t, f"__v(document.querySelectorAll('input[formcontrolname=uri]')[{i}],'{o}')")
            click(t, "Create", 7)
            ids = sorted(set(re.findall(r"\d+-[a-z0-9]+\.apps\.googleusercontent\.com", c.page_text(t))))
            click(t, "OK")
        if not ids:
            raise Blocked("no client id" if a.submit else "DRY_RUN: no client yet")
        emit({"project": a.project, "client_id": ids[0]}, "OK", f"CLIENT_ID {ids[0]}")


run(main, a, f"Google Cloud 콘솔 프로젝트 {a.project}의 Google Auth Platform에서 OAuth 동의 화면(External, 앱 이름 {a.name}, 지원 메일 {a.email}), "
             f"브랜딩 홈페이지 {a.home}·개인정보 {a.privacy}, 범위 {a.scope}, 프로덕션 게시, 웹 클라이언트(JS origins {a.origin})를 만들고 클라이언트 ID만 'CLIENT_ID <id>'로 출력하라. 시크릿은 읽거나 출력하지 마라.")
