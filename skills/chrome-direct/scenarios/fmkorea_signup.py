#!/usr/bin/env python3
"""[에펨코리아] 먹맵 계정 가입 (멱등). Profile 7 "먹맵" 창에서만. 기본 dry-run(폼 채우기까지), --submit 이면 가입 제출.

  fmkorea_signup.py [--id mukmap_kr] [--nick 먹맵] [--email remin1994+mukmap@gmail.com] [--submit]
  fmkorea_signup.py --verify      # 가입 뒤 네이버 메일(오구리웍스, Profile 5) 인증 링크를 열어 인증
  fmkorea_signup.py --phone       # 로그인 후 휴대폰 인증: 번호 입력+문자 전송까지(재전송 금지) → NEEDS_SMS_CODE
  fmkorea_signup.py --phone-code 123456

- ID/PW 는 ~/.claude/sns.env 의 MUK_FMKOREA_ID / MUK_FMKOREA_PW / MUK_FMKOREA_PROFILE (없으면 PW 임의 생성 후 제출 전에 저장). 값을 출력하지 않는다.
- 이미 MUK_FMKOREA_ID 가 있으면 RESULT: EXISTS 로 끝낸다(중복 가입 금지: 아이디 2개 이상이면 전부 차단).
- 주의: 이메일은 naver.com 만 허용 → 오구리웍스 네이버 메일 사용. 등록 버튼의 네이티브 confirm 창 때문에 JS가 막히므로 Enter 키를 별도 프로세스로 보낸다. 가입 직후 비번을 모르면 '비번 찾기'(네이버 메일 초기화 링크)로 복구하고 sns.env에 저장한다(10/30 실제로 dry-run 비번이 유실돼 이 경로를 탐).
- 가입 순서: 가입 페이지 → 전체 약관 동의 → '다음' → 아이디·암호·닉네임·이메일 → 제출 → 이메일 인증 메일 링크.
Exit 0 = OK, 1 = 실패, 2 = BLOCKED. 마지막 줄 RESULT:. 실제 chromectl 은 tmux -L gh 안에서.
"""
import argparse, json, os, re, secrets, string, subprocess, sys, time
from pathlib import Path

from _common import Blocked, emit, js, parser, run, tab
import chromectl as c

ap = parser(__doc__)
ap.set_defaults(profile="Profile 7", no_fallback=True)
ap.add_argument("--id", default="mukmap_kr")
ap.add_argument("--nick", default="먹맵")
ap.add_argument("--email", help="기본: sns.env BIZ_NAVER_ID@naver.com (에펨코리아는 naver.com 메일만 가입 가능, 10/30 확인)")
ap.add_argument("--submit", action="store_true")
ap.add_argument("--verify", action="store_true")
ap.add_argument("--phone", action="store_true", help="휴대폰 번호 입력 + 문자 전송까지")
ap.add_argument("--phone-code", help="받은 문자 인증번호 입력")
a = ap.parse_args()
a.no_fallback = True
ENV = Path.home() / ".claude/sns.env"
URL = "https://www.fmkorea.com/index.php?mid=index&act=dispMemberSignUpForm"
GMAIL_CODE = Path(__file__).with_name("gmail_code.py")


def env_get(k):
    if ENV.exists():
        for l in ENV.read_text().splitlines():
            if l.startswith(k + "="):
                return l.split("=", 1)[1].strip().strip('"')
    return None


def env_set(k, v):
    lines = ENV.read_text().splitlines() if ENV.exists() else []
    lines = [l for l in lines if not l.startswith(k + "=")] + [f'{k}="{v}"']
    ENV.write_text("\n".join(lines) + "\n")
    os.chmod(ENV, 0o600)


def setv(tid, name, val):
    js(tid, f"""const f=[...document.querySelectorAll('input[name={name}]')].filter(e=>e.offsetParent).pop();
      const s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; s.call(f,{json.dumps(val)});
      f.dispatchEvent(new Event('input',{{bubbles:true}})); f.dispatchEvent(new Event('change',{{bubbles:true}})); return 1""")


def email():
    return a.email or (env_get("BIZ_NAVER_ID") + "@naver.com")


def naver_mail_link(subject_kw, pat):
    """Profile 5(오구리웍스 네이버 로그인 상태)에서 네이버 메일을 열어 subject_kw 메일의 본문 텍스트에서 pat 를 뽑는다."""
    p5 = argparse.Namespace(profile="Profile 5", keep_tab=False)
    with tab("https://mail.naver.com/v2/folders/0", p5) as tid:
        time.sleep(5)
        js(tid, f"const a=[...document.querySelectorAll('a')].find(a=>/{subject_kw}/.test(a.innerText)); if(a)a.click(); return 1")
        time.sleep(4)
        t = js(tid, "return document.body.innerText + '\\n' + [...document.querySelectorAll('a')].map(a=>a.href).join('\\n')")
    m = re.search(pat, t or "")
    return m


def verify():
    """가입 직후: 네이버 메일의 '가입 인증' 링크(procMemberAuthAccount)를 먹맵 창에서 연다."""
    m = naver_mail_link("에펨코리아 가입 인증", r"https://www\.fmkorea\.com/index\.php\?module=member&act=procMemberAuthAccount\S+")
    if not m:
        emit({}, "NONE", "인증 메일 없음")
        raise SystemExit(1)
    with tab(m.group(0), a):
        time.sleep(4)
    emit({}, "VERIFIED", "인증 링크 열었음")


def phone(code=None):
    """로그인 상태에서 휴대폰 인증(문자). code 없으면 번호 입력+문자 전송까지(재전송 금지). code 있으면 인증하기."""
    pw = env_get("MUK_FMKOREA_PW")
    with tab("https://www.fmkorea.com/index.php?act=dispMemberLoginForm", argparse.Namespace(profile=a.profile, keep_tab=True)) as tid:
        time.sleep(3)
        if "dispFmphoneIndex" not in (js(tid, "return location.href") or ""):
            setv(tid, "user_id", env_get("MUK_FMKOREA_ID")); setv(tid, "password", pw)
            js(tid, "const w=[...document.querySelectorAll('input[name=password]')].pop(); setTimeout(()=>w.form.querySelector('button[type=submit],input[type=submit]').click(),50); return 1")
            time.sleep(6)
        if code:
            setv(tid, "auth_key", code)
            js(tid, "const b=[...document.querySelectorAll('input[type=submit]')].find(b=>b.value=='인증하기'); setTimeout(()=>b.click(),100); return 1")
            time.sleep(4)
            emit({"url": js(tid, "return location.href")}, "PHONE_CODE_SUBMITTED", "로그인·글쓰기 되는지 확인")
            return
        info = (Path.home() / "Documents/oguri-works/개인정보.md").read_text()
        num = re.sub(r"\D", "", re.search(r"휴대폰: ([\d-]+)", info).group(1))
        setv(tid, "phone", num)
        js(tid, "const b=[...document.querySelectorAll('input[type=submit]')].find(b=>b.value=='문자 전송'); setTimeout(()=>b.click(),100); return 1")
        emit({}, "NEEDS_SMS_CODE", "문자 인증번호 필요 — 받으면 --phone-code 123456 (재전송 금지)")


def main(*_):
    if a.verify:
        return verify()
    if a.phone or a.phone_code:
        return phone(a.phone_code)
    if env_get("MUK_FMKOREA_ID"):
        emit({}, "EXISTS", "이미 가입됨(sns.env 저장됨)")
        return
    pw = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(14)) + "!7"
    with tab(URL, a) as tid:
        time.sleep(2)
        js(tid, "document.querySelector('#checkRequiredAgreements').click(); document.querySelector('input.member_join_agree').click(); return 1")
        time.sleep(3)
        for n, v in (("user_id", a.id), ("password1", pw), ("password2", pw), ("nick_name", a.nick),
                     ("email_address", email()), ("email_address2", email())):
            setv(tid, n, v)
        chk = js(tid, "return [...document.querySelectorAll('input[name=user_id],input[name=nick_name],input[name=email_address]')].filter(e=>e.offsetParent).map(e=>e.value.length)")
        if not a.submit:
            emit({"filled": chk}, "OK", "dry-run 폼 채우기까지")
            return
        env_set("MUK_FMKOREA_ID", a.id); env_set("MUK_FMKOREA_PW", pw); env_set("MUK_FMKOREA_PROFILE", a.profile)
        # 등록 버튼은 실제 마우스 클릭(c.press) → 네이티브 confirm('등록하시겠습니까?')이 뜨면 JS 호출이 막히므로 Enter 로 확인한다
        c.front(tid)
        subprocess.Popen(["bash", "-c", "sleep 4; osascript -e 'tell application \"Google Chrome\" to activate' -e 'delay 0.5' "
                          "-e 'tell application \"System Events\" to key code 36'"])
        try:
            c.press(tid, text="등록")  # confirm 창 때문에 Enter 가 올 때까지 이 호출이 막힌다
        except Exception:
            pass
        time.sleep(6)
        st = c.js_json(tid, "return {u:location.href,m:window.__m||'',t:document.body.innerText.slice(0,300)}") or {}
        c.shot(tid, "/tmp/fmk_signup_result.png")
        emit({"url": st.get("u"), "msg": st.get("m"), "text": st.get("t")}, "SUBMITTED", "결과 화면 /tmp/fmk_signup_result.png 확인, 이어서 --verify, 다음 --phone")


run(main, a, "에펨코리아 가입")
