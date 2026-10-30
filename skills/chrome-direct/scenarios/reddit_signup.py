#!/usr/bin/env python3
"""[레딧] 먹맵 계정 가입 (멱등). Profile 7 "먹맵" 창에서만. 구글 로그인 가입 금지(이메일 가입).

  reddit_signup.py [--id mukmap_kr] [--email remin1994+mukmap@gmail.com] [--submit]
  reddit_signup.py --persona BIZ --profile "Profile 5" --id oguriworks --email remin1994+oguri@gmail.com --submit

- 이미 MUK_REDDIT_ID 가 sns.env 에 있으면 RESULT: EXISTS 로 끝낸다(중복 가입 금지).
- 흐름(10/30 실제): /register/ → (reCAPTCHA 체크박스; 이미지 챌린지가 뜨면 BLOCKED — 그림을 읽어 직접 1회만 풀고 재시도 루프 금지)
  → 이메일 입력·계속 → 이메일 6자리 코드(gmail_code.py 'from:reddit', 제목 "NNNNNN is your Reddit verification code")
  → 사용자 이름·비밀번호 → 계속 → 관심사 건너뛰기. 전화·얼굴 인증은 없었다. 나오면 BLOCKED.
- 이름 칸은 실제 키입력이 안 먹어 JS native setter + composed 이벤트(shadow DOM 순회)로 넣는다. 같은 창을 다른 세션이 쓰므로 cliclick 대신 JS 위주.
- 비번은 임의 생성 후 제출 전에 sns.env(MUK_REDDIT_PW)에 저장, 출력하지 않는다.
- 상태: partial (10/30 수동+임시 스크립트로 가입 성공, 이 파일은 그 흐름을 옮긴 것이라 통합 실행은 미검증).
Exit 0 = OK, 1 = 실패, 2 = BLOCKED. 마지막 줄 RESULT:. tmux -L gh 안에서 실행.
"""
import json, os, re, secrets, string, subprocess, sys, time
from pathlib import Path

from _common import Blocked, emit, js, parser, run, tab
import chromectl as c

ap = parser(__doc__)
ap.set_defaults(profile="Profile 7", no_fallback=True)
ap.add_argument("--id", default="mukmap_kr")
ap.add_argument("--email", default="remin1994+mukmap@gmail.com")
ap.add_argument("--persona", default="MUK", help="sns.env 키 앞머리 (MUK·BIZ 등). --profile 도 그 페르소나 프로필로")
ap.add_argument("--submit", action="store_true")
a = ap.parse_args()
a.no_fallback = True
ENV = Path.home() / ".claude/sns.env"
URL = "https://www.reddit.com/register/"
GMAIL_CODE = Path(__file__).with_name("gmail_code.py")

DEEP = """const deep=(r,sel,out=[])=>{out.push(...r.querySelectorAll(sel));r.querySelectorAll('*').forEach(e=>{if(e.shadowRoot)deep(e.shadowRoot,sel,out)});return out};"""


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


def setv(tid, sel, val):
    return js(tid, DEEP + f"""const f=deep(document,{json.dumps(sel)}).filter(e=>e.offsetParent!==null||true)[0]; if(!f)return 0;
      const s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; s.call(f,{json.dumps(val)});
      for(const t of ['input','change'])f.dispatchEvent(new Event(t,{{bubbles:true,composed:true}})); return 1""")


def click_text(tid, pat):
    return js(tid, DEEP + f"""const b=deep(document,'button').find(b=>/{pat}/.test(b.innerText)&&!b.disabled); if(!b)return 0; b.click(); return 1""")


def reddit_code():
    r = subprocess.run([sys.executable, str(GMAIL_CODE), "from:reddit", "--newer", "10m", "--no-fallback", "--pattern", r"(\d{6}) is your Reddit"], capture_output=True, text=True)
    m = re.search(r"\b(\d{6})\b", r.stdout)
    return m.group(1) if m else None


def main(*_):
    if env_get(f"{a.persona}_REDDIT_ID"):
        emit({}, "EXISTS", "이미 가입됨(sns.env 저장됨)")
        return
    pw = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(14)) + "!7"
    with tab(URL, argparse_ns()) as tid:
        for _ in range(10):  # 10/30 Profile 5: js_challenge 리다이렉트 뒤에야 이메일 칸이 생긴다
            time.sleep(3)
            if js(tid, DEEP + "return deep(document,'input[type=email],input[name=email]').length"):
                break
        txt = js(tid, "return document.body.innerText.slice(0,400)") or ""
        if re.search(r"로봇이 아닙니다|not a robot", txt):
            raise Blocked("reCAPTCHA 체크 필요: iframe[src*=anchor] 사각형 left+28 세로 중앙 클릭, 이미지 챌린지는 그림을 직접 읽어 1회만")
        if not setv(tid, "input[type=email],input[name=email]", a.email):
            raise Blocked("이메일 입력칸 없음(화면 변경)")
        if not a.submit:
            emit({}, "OK", "dry-run 이메일 칸까지")
            return
        env_set(f"{a.persona}_REDDIT_PW", pw); env_set(f"{a.persona}_REDDIT_PROFILE", a.profile)
        time.sleep(1); click_text(tid, "계속|Continue")
        code = None
        for _ in range(15):  # 10/30 BIZ: 코드 메일이 1분 넘게 걸려 48초로는 놓쳤다
            time.sleep(6)
            code = reddit_code()
            if code:
                break
        if not code:
            raise Blocked("이메일 코드 못 찾음(재전송 금지)")
        setv(tid, "input[name=code],input[inputmode=numeric],input[type=text]", code)
        time.sleep(1); click_text(tid, "계속|Continue")
        time.sleep(6)
        setv(tid, "input[name=username]", a.id)
        c.front(tid)
        setv(tid, "input[name=password],input[type=password]", pw)
        time.sleep(1); click_text(tid, "계속|Continue")
        time.sleep(6)
        u = js(tid, "return location.href")
        env_set(f"{a.persona}_REDDIT_ID", a.id)
        # 10/30: 다음 화면은 Chrome 패스키 저장 시트 → Esc, 그리고 '내 정보'·관심사 '건너뛰기' 2번
        subprocess.run(["cliclick", "kp:esc"]); time.sleep(2)
        for _ in range(3):
            if not click_text(tid, "^(건너뛰기|Skip)$"):
                break
            time.sleep(5)
        u = js(tid, "return location.href")
        emit({"url": u}, "SUBMITTED", "로그인 상태 /user/%s/ 로 확인, 전화·얼굴 인증이 뜨면 멈춤" % a.id)


def argparse_ns():
    return a


run(main, a, "레딧 가입")
