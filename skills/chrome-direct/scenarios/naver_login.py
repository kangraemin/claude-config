#!/usr/bin/env python3
"""[로그인] 이 Chrome 프로필의 네이버 로그인 확인 → 로그아웃이면 비밀번호 없이 로그인을 띄운다.
지식iN·카페·네이버폼·네이버 로그인 공공사이트 작업 전에 먼저 돌린다(사용자 10/19 "스킬화해둬라").

  naver_login.py                      # 상태만: exit 0 IN, 2 LOGGED_OUT
  naver_login.py --qr --notify        # QR을 텔레그램으로 바로 보냄(사용자 폰). 로그인되면 확인 메시지
  naver_login.py --qr [--out q.png]   # QR 로그인 띄우고 QR png + 앱에서 고를 숫자 출력, 로그인될 때까지 대기
  naver_login.py --otp 12345678       # 일회용 번호(네이버 앱 설정 > 로그인 아이디 관리 > 더보기)로 로그인
  naver_login.py --profile "Profile 5" --pw BIZ   # ~/.claude/sns.env <BIZ>_NAVER_ID/_PW를 한 글자씩 키 이벤트로 넣어 로그인
  naver_login.py --profile "Profile 5" --pw BIZ --tab <id> --captcha 300   # CAPTCHA로 멈췄을 때: /tmp/naver-captcha.jpg(영수증 질문)를 읽고 답 1회

- --pw 없이는 비밀번호를 쓰지 않는다. --pw는 sns.env 값만 쓰고 출력하지 않는다(10/23 오구리웍스: 보안문자·새 기기 확인 없이 됨).
  value만 넣으면 키 입력 흔적이 없어 보안문자로 막히므로 한 글자씩 키 이벤트를 보내 친다(cliclick은 앞 창이 바뀌면 샘). '로그인 상태 유지'를 켜서 다음 로그아웃을 줄인다.
- QR: 네이버 앱 검색창 옆 렌즈 → QR 스캔 → 앱에 뜬 숫자 중 출력된 숫자 선택. QR은 3분마다 바뀌어 --rounds번 새로 띄운다.
  사용자가 맥 앞에 없으면 png를 폰으로 보내 다른 화면에 띄워 스캔하게 하거나 --otp를 쓴다.
- 일회용 번호 로그인은 네이버가 '종료 예정'이라 공지(10/19 화면 문구). 막히면 QR로.
Exit 0 = 로그인됨, 2 = 로그아웃/시간 초과(사람 몫).
"""
import base64, json, os, re, time, urllib.parse, urllib.request, uuid
from pathlib import Path

from _common import Blocked, emit, js, parser, poll, run, tab
import chromectl as c

ap = parser(__doc__)
ap.add_argument("--qr", action="store_true")
ap.add_argument("--otp")
ap.add_argument("--pw", metavar="PERSONA", help="sns.env의 <PERSONA>_NAVER_ID/_PW로 로그인")
ap.add_argument("--captcha", metavar="ANSWER", help="--tab의 보안문자 화면에 답을 넣고 로그인을 마저 한다(--pw와 함께)")
ap.add_argument("--tab", help="보안문자에서 멈춘 탭 id(CAPTCHA 결과에 출력됨, /tmp/naver-login-tab)")
ap.add_argument("--out", default="/tmp/naver-qr.png")
ap.add_argument("--notify", action="store_true", help="QR·숫자·결과를 텔레그램(RAM_NOTI_TG_*)으로 바로 보냄")
ap.add_argument("--rounds", type=int, default=3, help="QR 새로 띄우는 횟수(1회 약 3분)")
a = ap.parse_args()

LOGIN = "https://nid.naver.com/nidlogin.login?mode=form&url=https%3A%2F%2Fwww.naver.com"
STATE = r"""const u=location.href;
  if (/nid\.naver\.com\/nidlogin/.test(u)) return {state:'LOGGED_OUT'};
  if (/nid\.naver\.com\/user2\/help\/myInfo/.test(u) && document.body && document.body.innerText.length>50) return {state:'IN'};
  return null;"""


def tg(text, photo=None):
    if not a.notify:
        return
    try:
        env = dict(re.findall(r"^(RAM_NOTI_TG_\w+)=['\"]?([^'\"\n]+)", Path.home().joinpath(".claude/.env").read_text(), re.M))
        base = f"https://api.telegram.org/bot{env['RAM_NOTI_TG_TOKEN']}/"
        if photo is None:
            urllib.request.urlopen(base + "sendMessage", urllib.parse.urlencode({"chat_id": env["RAM_NOTI_TG_CHAT_ID"], "text": text}).encode(), timeout=20)
            return
        b = uuid.uuid4().hex
        body = (f"--{b}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{env['RAM_NOTI_TG_CHAT_ID']}\r\n"
                f"--{b}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{text}\r\n"
                f"--{b}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"qr.png\"\r\nContent-Type: image/png\r\n\r\n").encode() + photo + f"\r\n--{b}--\r\n".encode()
        req = urllib.request.Request(base + "sendPhoto", body, {"Content-Type": f"multipart/form-data; boundary={b}"})
        urllib.request.urlopen(req, timeout=20)
    except Exception as e:
        print(f"TG_FAIL {type(e).__name__}", flush=True)


def big_png(raw):
    try:
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(raw)).convert("L").resize((800, 800), Image.NEAREST)
        buf = io.BytesIO(); im.save(buf, "PNG"); return buf.getvalue()
    except Exception:
        return raw


def status(tid):
    c.goto(tid, "https://nid.naver.com/user2/help/myInfo?lang=ko_KR")
    time.sleep(2)
    return poll(tid, STATE, 20)


def logged_in_after(tid, secs):
    end = time.time() + secs
    while time.time() < end:
        time.sleep(3)
        try:
            u = js(tid, "return location.href")
        except Exception:
            continue
        if "nid.naver.com/nidlogin" not in u:
            return True
    return False


def keep_login(tid):
    js(tid, r"""const k=document.querySelector('#nvlong,[name=nvlong]'); if(k&&!k.checked){k.click();} return !!k""")


def env_val(key):
    for line in Path("~/.claude/sns.env").expanduser().read_text().splitlines():
        m = re.match(r"\s*(?:export\s+)?%s\s*=\s*(.*)$" % re.escape(key), line)
        if m:
            return m.group(1).strip().strip("'\"")
    raise Blocked(f"NO_ENV {key}")


def type_js(tid, sel, text):
    # 한 글자씩 keydown/keypress/input/keyup을 보낸다. value만 넣으면 키 입력 흔적이 없어 보안문자 오답 처리되고,
    # cliclick 실제 키는 다른 세션이 앞 창을 바꾸면 엉뚱한 창으로 샌다(10/23 둘 다 겪음).
    js(tid, r"""const i=document.querySelector(%s), v=%s, set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
      i.focus(); set.call(i,'');
      for (const ch of v) { const o={key:ch,keyCode:ch.charCodeAt(0),which:ch.charCodeAt(0),bubbles:true};
        i.dispatchEvent(new KeyboardEvent('keydown',o)); i.dispatchEvent(new KeyboardEvent('keypress',o)); set.call(i,i.value+ch);
        i.dispatchEvent(new InputEvent('input',{data:ch,inputType:'insertText',bubbles:true})); i.dispatchEvent(new KeyboardEvent('keyup',o)); }
      i.dispatchEvent(new Event('change',{bubbles:true})); i.blur(); return 1""" % (json.dumps(sel), json.dumps(text)))


CAPTCHA_IMG = "/tmp/naver-captcha.jpg"


def captcha_stop(tid):
    """영수증 질문형 보안문자면 그림·질문을 남기고 탭을 열어 둔 채 멈춘다. 답은 그림을 읽고 --captcha로 한 번만 넣는다."""
    q = js(tid, r"""if(!document.getElementById('captcha')) return null;
      const i=[...document.querySelectorAll('img')].sort((a,b)=>b.width*b.height-a.width*a.height)[0];
      const t=document.body.innerText.replace(/\s+/g,' '); const m=t.match(/아니에요\.\s*(.+?)\s*확인/);
      return {src:i?i.src:'', q:m?m[1]:t.slice(0,200), wrong:/잘못 입력/.test(t)}""")
    if not q:
        return
    if q["src"].startswith("data:"):
        Path(CAPTCHA_IMG).write_bytes(base64.b64decode(q["src"].split(",", 1)[1]))
    a.keep_tab = True
    Path("/tmp/naver-login-tab").write_text(tid)
    print(f"CAPTCHA_Q {q['q']}", flush=True)
    emit({"profile": a.profile, "tab": tid, "image": CAPTCHA_IMG, "question": q["q"], "previous_wrong": q["wrong"]}, "CAPTCHA",
         f"그림 {CAPTCHA_IMG}을 읽고 --pw {a.pw} --tab {tid} --captcha <답> 으로 한 번만(재시도 루프 금지)")
    raise Blocked("CAPTCHA")


def captcha_answer(tid):
    type_js(tid, "#captcha", a.captcha.strip())
    js(tid, r"""const b=[...document.querySelectorAll('button,a,input[type=submit]')].find(e=>(e.innerText||e.value||'').trim()=='확인');
      setTimeout(()=>b.click(),10); return !!b""")
    time.sleep(6)
    captcha_stop(tid)  # 틀리면 새 질문으로 다시 멈춘다
    if "nid.naver.com/nidlogin" in js(tid, "return location.href") and js(tid, "return !!document.querySelector('#pw')"):
        pw_login(tid)  # 통과하면 네이버가 '다시 로그인해 주세요'로 돌려보낸다
    else:
        ok = status(tid)["state"] == "IN"
        emit({"profile": a.profile}, "OK" if ok else "PW_FAIL", "")
        if not ok:
            raise Blocked("PW_FAIL")


def pw_login(tid):
    uid, pw = env_val(f"{a.pw}_NAVER_ID"), env_val(f"{a.pw}_NAVER_PW")
    for sel, val in (("#id", uid), ("#pw", pw)):
        type_js(tid, sel, val)
        time.sleep(0.3)
    # 버튼 .click()은 안 먹고 requestSubmit은 onsubmit 처리까지 탄다
    js(tid, r"""const f=document.querySelector('#frmNIDLogin')||document.querySelector('#pw').form;
      setTimeout(()=>f.requestSubmit(),10); return !!f""")
    seen = []
    for _ in range(12):
        time.sleep(1)
        try:
            u = js(tid, "return location.host+location.pathname")
        except Exception:
            continue
        if not seen or seen[-1] != u:
            seen.append(u)
    print("URLS", " > ".join(seen), flush=True)
    captcha_stop(tid)
    if seen and "idSafetyRelease" in seen[-1]:
        # 아이디 보호조치: 네이버가 이상 로그인으로 막음 → 본인확인(사람 몫)
        c.shot(tid, "/tmp/naver-pw-fail.png")
        print("PAGE", js(tid, "return document.body.innerText.replace(/\\s+/g,' ').slice(0,500)"), flush=True)
        emit({"profile": a.profile}, "ID_PROTECTED", "네이버 아이디 보호조치 화면 — 본인확인 필요, /tmp/naver-pw-fail.png")
        raise Blocked("ID_PROTECTED")
    left = logged_in_after(tid, 20)
    if not left:
        c.shot(tid, "/tmp/naver-pw-fail.png")
        print("PAGE", js(tid, "return location.host+location.pathname+' | '+document.body.innerText.replace(/\\s+/g,' ').slice(0,300)"))
    ok = left and status(tid)["state"] == "IN"
    emit({"profile": a.profile}, "OK" if ok else "PW_FAIL", "" if ok else "보안문자·새 기기 확인 화면일 수 있음 → 캡처 확인")
    if not ok:
        raise Blocked("PW_FAIL")


def main():
    if a.captcha:
        if not (a.pw and a.tab):
            raise Blocked("--captcha는 --pw, --tab과 함께")
        tid = a.tab if a.tab.startswith("id:") else "id:" + a.tab
        try:
            captcha_answer(tid)
        finally:
            if not getattr(a, "keep_tab", False):
                with __import__("contextlib").suppress(Exception):
                    c.close_tab(tid)
        return
    with tab("https://nid.naver.com/user2/help/myInfo?lang=ko_KR", a) as tid:
        time.sleep(2)
        st = poll(tid, STATE, 25)
        st["profile"] = a.profile
        if st["state"] == "IN":
            emit(st, "OK", "네이버 로그인됨")
            return
        if not (a.qr or a.otp or a.pw):
            emit(st, "LOGGED_OUT", "--qr 또는 --otp <번호>로 다시 실행")
            raise Blocked("LOGGED_OUT")
        c.goto(tid, LOGIN)
        time.sleep(3)
        keep_login(tid)
        if a.pw:
            pw_login(tid)
            return
        if a.otp:
            js(tid, "document.querySelector('#onetime_login').click(); return 1")
            poll(tid, "return document.querySelector('#OnetimeCode') ? 1 : null", 15)
            js(tid, r"""const i=document.querySelector('#OnetimeCode');
              Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i, %r);
              i.dispatchEvent(new Event('input',{bubbles:true})); return 1""" % a.otp.strip())
            js(tid, "document.getElementById('otnlog.login').click(); return 1")
            ok = logged_in_after(tid, 20) and status(tid)["state"] == "IN"
            emit({"profile": a.profile}, "OK" if ok else "OTP_FAIL", "" if ok else "번호가 틀렸거나 만료(1회용, 몇 분 유효)")
            if not ok:
                raise Blocked("OTP_FAIL")
            return
        for r in range(a.rounds):
            js(tid, "document.querySelector('#qrcode_login').click(); return 1")
            q = poll(tid, r"""const i=document.querySelector('#qrImage'); if(!i||!i.src.startsWith('data:')) return null;
              const m=document.body.innerText.match(/QR Code\s*\n\s*(\d{1,3})/); return {src:i.src, num:m?m[1]:''}""", 20)
            png = big_png(base64.b64decode(q["src"].split(",", 1)[1].strip()))
            Path(a.out).write_bytes(png)
            tg(f"네이버 로그인: 앱 렌즈로 QR 스캔 → 숫자 {q['num']} 선택 (3분, {r + 1}/{a.rounds})", png)
            print(f"QR {a.out} NUMBER {q['num']} ROUND {r + 1}/{a.rounds}", flush=True)
            if logged_in_after(tid, 175):
                ok = status(tid)["state"] == "IN"
                emit({"profile": a.profile}, "OK" if ok else "UNCONFIRMED", "QR 로그인")
                tg("네이버 로그인 확인됨 — 작업 이어서 함" if ok else "네이버 로그인 확인 안 됨")
                if ok:
                    return
                raise Blocked("UNCONFIRMED")
            c.goto(tid, LOGIN)
            time.sleep(3)
            keep_login(tid)
        emit({"profile": a.profile}, "TIMEOUT", "QR 스캔 안 됨")
        tg("네이버 QR 시간 초과 — 필요하면 다시 띄울게요")
        raise Blocked("QR_TIMEOUT")


run(main, a, f"Chrome 프로필 '{a.profile}'에서 https://nid.naver.com/user2/help/myInfo 를 열어 네이버 로그인 여부만 확인해 IN/LOGGED_OUT 출력. 비밀번호 입력·로그인 시도 금지.")
