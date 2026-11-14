#!/usr/bin/env python3
"""구글 계정을 전용 Chrome 프로필에서 로그인하고 지메일 앱 비밀번호를 만들어 .env에 넣는다 (SMTP 발신용).
2026-11-14 김은미(dmsal547) 계정으로 처음 돌린 순서를 그대로 옮김.

  google_app_password.py --profile "Profile 15" --email dmsal547@gmail.com \
      --pw-env KIMEUNMI_GMAIL_PASSWORD --out-env KIMEUNMI_GMAIL_APP_PASSWORD

- 비밀번호는 ~/.claude/.env 에서 읽고 화면·로그에 찍지 않는다.
- 새 프로필은 'Apple Events JS 허용'이 꺼져 있다 → 그 프로필 창을 닫고 Preferences에 직접 켠 뒤 다시 연다.
- 키 입력(cliclick)은 다른 세션이 창을 앞으로 올리면 엉뚱한 창으로 간다 → JS native setter로만 넣는다.
- 2단계 인증은 폰 '예' + 화면 숫자 탭(사람 몫). 숫자를 출력하고 최대 10분 기다린다.
- 로그인 완료 판정은 host로 한다(URL의 continue=mail.google.com 에 속지 않게).
마지막 줄: RESULT: OK | BLOCKED <이유>
"""
import argparse, json, os, re, smtplib, subprocess, sys, time, urllib.parse as up
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import chromectl as c

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--profile", required=True)
ap.add_argument("--email", required=True)
ap.add_argument("--pw-env", required=True)
ap.add_argument("--out-env", required=True)
ap.add_argument("--app-name", default="contest-smtp")
a = ap.parse_args()
ENV = Path.home() / ".claude/.env"
PDIR = Path.home() / "Library/Application Support/Google/Chrome" / a.profile
SET = """(function(sel,v){const e=sel?document.querySelector(sel):[...document.querySelectorAll('input')].find(i=>i.getClientRects().length&&i.type=='text');
if(!e)return 'NOEL';e.focus();Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,v);
e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));return 'SET'})"""
BTN = "(()=>{const b=[...document.querySelectorAll('button,[role=button],a')].find(e=>e.innerText.trim()==%s);if(!b)return 'none';b.click();return 'clk'})()"


def done(msg, ok=False):
    print(f"RESULT: {'OK' if ok else 'BLOCKED'} {msg}")
    sys.exit(0 if ok else 2)


def ensure_js_pref():
    pf = PDIR / "Preferences"
    if pf.exists() and json.loads(pf.read_text()).get("browser", {}).get("allow_javascript_apple_events"):
        return
    if pf.exists():  # 그 프로필 창이 열려 있으면 Chrome이 덮어쓴다 — 창을 먼저 닫아 두고 실행
        print("NOTE 그 프로필 창이 열려 있으면 닫힌 뒤 20초 기다렸다가 씀", flush=True)
        time.sleep(20)
    d = json.loads(pf.read_text()) if pf.exists() else {}
    d.setdefault("browser", {})["allow_javascript_apple_events"] = True
    PDIR.mkdir(parents=True, exist_ok=True)
    pf.write_text(json.dumps(d))


def url(t):
    try:
        return up.urlsplit(c.run_js(t, "location.href"))
    except Exception:
        return up.urlsplit("")


def wait_host(t, pred, secs=600):
    end = time.time() + secs
    while time.time() < end:
        p = url(t)
        if pred(p):
            return p
        time.sleep(4)
    return None


def challenge(t):
    """비밀번호 칸이면 넣고, 기기 확인이면 숫자를 알려 준다."""
    if "/challenge/pk" in url(t).path or "/challenge/selection" in url(t).path:
        c.run_js(t, BTN % json.dumps("다른 방법 시도"))
        c.run_js(t, BTN % json.dumps("인증 방법 더보기"))
        time.sleep(3)
        has_pw = c.run_js(t, "String(!!document.querySelector('[data-challengetype=\"1\"]'))") == "true"
        c.run_js(t, "document.querySelector('[data-challengetype=\"%s\"]')?.click();'x'" % ("1" if has_pw else "39"))
        time.sleep(4)
    if c.run_js(t, "String(!!document.querySelector('input[type=password]'))") == "true":
        c.run_js(t, SET + "('input[type=password]'," + json.dumps(c.secret(a.pw_env)) + ")")
        time.sleep(0.5)
        c.run_js(t, BTN % json.dumps("다음"))
        time.sleep(7)
    if "/challenge/dp" in url(t).path or "/challenge/selection" in url(t).path:
        if "/challenge/selection" in url(t).path:
            c.run_js(t, "document.querySelector('[data-challengetype=\"39\"]')?.click();'x'")
            time.sleep(4)
        txt = c.run_js(t, "document.body.innerText")
        n = re.search(r"휴대전화에서 (\d+) 값을", txt or "")
        print(f"NEED_PHONE 폰 알림에서 '예'{' 후 숫자 ' + n.group(1) if n else ''} 탭", flush=True)


ensure_js_pref()
t = c.new_tab("https://accounts.google.com/ServiceLogin?service=mail&continue=https://mail.google.com/mail/&hl=ko", a.profile, timeout=25)
time.sleep(4)
if url(t).netloc != "mail.google.com":
    c.run_js(t, SET + "('#identifierId'," + json.dumps(a.email) + ")")
    c.run_js(t, BTN % json.dumps("다음"))
    time.sleep(6)
    challenge(t)
    if not wait_host(t, lambda p: p.netloc != "accounts.google.com" or "/challenge/" not in p.path):
        done("로그인 2단계 인증 시간 초과")
c.goto(t, "https://myaccount.google.com/apppasswords?hl=ko")
time.sleep(6)
if url(t).netloc == "accounts.google.com":
    challenge(t)
    if not wait_host(t, lambda p: p.netloc == "myaccount.google.com"):
        done("앱 비밀번호 화면 재인증 시간 초과")
c.run_js(t, SET + "(null," + json.dumps(a.app_name) + ")")
time.sleep(1)
c.run_js(t, BTN % json.dumps("만들기"))
time.sleep(5)
m = re.search(r"([a-z]{4}\s[a-z]{4}\s[a-z]{4}\s[a-z]{4})", c.run_js(t, "document.body.innerText") or "")
if not m:
    done("앱 비밀번호 대화상자를 못 읽음(2단계 인증 꺼짐·Workspace 정책일 수 있음)")
pw = m.group(1).replace(" ", "")
s = ENV.read_text() if ENV.exists() else ""
s = re.sub(rf"(?m)^{a.out_env}=.*\n?", "", s)
s = (s if s.endswith("\n") or not s else s + "\n") + f"{a.out_env}={pw}\n"
ENV.write_text(s)
sm = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20)
code = sm.login(a.email, pw)[0]
sm.quit()
done(f"{a.out_env} 저장, SMTP 로그인 {code}", ok=code == 235)
