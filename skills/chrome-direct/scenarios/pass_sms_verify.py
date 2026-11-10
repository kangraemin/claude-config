#!/usr/bin/env python3
"""[제출] 휴대폰 본인확인 표준창(cert.mobile-ok.com, PASS) 문자 인증.

  pass_sms_verify.py send [--match mobile-ok]   → 통신사·이름·생년월일·성별·번호·보안문자까지 넣고 문자 발송 후 멈춤
  pass_sms_verify.py code 123456 [--match ..]   → 인증번호 입력·확인
  pass_sms_verify.py extend                     → 남은 시간 연장
  pass_sms_verify.py ogq-open                   → OGQ 크리에이터 스튜디오 휴대폰 인증 창 열기(업로드 2단계 인증)
  pass_sms_verify.py open <페이지URL> [--button 본인확인]  → 사이트의 본인확인 버튼을 실제 마우스로 눌러 팝업을 연다(합성 클릭은 팝업 차단)
  pass_sms_verify.py wait [--match ..]          → 알림 봇(RAM_NOTI_TG)으로 6자리 요청 → 답장(또는 answer 파일)을 5초마다 보고 즉시 code 입력, 2분마다 시간연장
- 11/10 고령 설문: 다른 세션(텔레그램 채널 플러그인)이 답장을 먼저 가져가 늦게 전달 → 창 만료. wait는 /tmp/pass-answer.txt 도 본다
  (다른 세션이 받은 번호는 `echo 123456 > /tmp/pass-answer.txt`로 넘긴다). 만료되면 open부터 다시.

- 사전 조건: 본인확인 창이 이미 열려 있어야 한다(사이트의 '휴대폰 인증' 버튼으로 연다).
- OGQ 주의: 통합계정(oid.ogq.me/me '인증')과 크리에이터 스튜디오(creators.ogq.me/profile/verification)는 인증이 따로다.
  업로드에 필요한 건 크리에이터 쪽(api verifyPhone). 그 '인증하기' 버튼은 API 응답 뒤 window.open이라 합성 클릭이면 팝업 차단 →
  ogq-open 은 /api/user/verification/identity 를 직접 불러 받은 주소를 새 탭으로 연다. 결과는 rtn_url(api.ocs) 서버 콜백으로 저장된다.
- 값은 ~/Documents/oguri-works/개인정보.md 에서 패턴으로 뽑는다(출력 안 함). 통신사 SKT 알뜰폰, 주민번호 뒤 첫 숫자 1.
- 보안문자는 이미지(data URL)를 CAPTCHA_PNG 로 저장하고 멈춘다 → 읽어서 `send --captcha 123456` 로 다시 부른다.
  (단계마다 다음 칸이 나타나는 방식이라, 보안문자 이전 단계는 다시 불러도 이미 채워진 칸은 건너뛴다.)
- 사람 몫은 폰에 온 인증번호 6자리뿐이다. 창은 오래 두면 "유효시간이 만료" → 사이트에서 다시 연다.
- 왜 화면 조작인가: 본인확인은 공개 API가 없다. 칸은 keyup이 있어야 '다음'이 나타나고, 버튼은 press(포인터 이벤트)만 먹는다.
"""
import argparse
import base64
import os
import re
import sys
import time

sys.path.insert(0, os.path.expanduser("~/.claude/skills/chrome-direct"))
import chromectl as c  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("cmd", choices=["send", "code", "extend", "ogq-open", "open", "wait"])
ap.add_argument("--button", default="본인확인")
ap.add_argument("--timeout", type=int, default=900)
ap.add_argument("value", nargs="?")
ap.add_argument("--captcha")
ap.add_argument("--match", default="cert.mobile-ok.com")
a = ap.parse_args()
CAPTCHA_PNG = "/tmp/pass-captcha.png"
SETV = """(e,v)=>{e.focus();Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set.call(e,v);
  for(const k of ["input","change","keydown","keyup"])e.dispatchEvent(k.startsWith("key")?new KeyboardEvent(k,{key:"1",bubbles:true}):new Event(k,{bubbles:true}));return e.value.length}"""


def put(t, pick, v):
    """보이는 input 중 pick(JS 식, e 변수)에 맞는 첫 칸에 값을 넣는다. 이미 차 있으면 건너뛴다."""
    return c.run_js(t, f"""(()=>{{const e=[...document.querySelectorAll("input")].filter(e=>e.offsetParent).find(e=>{pick});
      if(!e)return "NOTFOUND";if(e.value)return "SKIP";return ({SETV})(e,{v!r})}})()""")


def text(t):
    return c.page_text(t)


def nxt(t):
    try:
        c.press(t, text="다음")
    except RuntimeError as e:  # 다날(teledit)은 다음 버튼 없이 바로 다음 칸으로 넘어간다
        if "NOTFOUND" not in str(e):
            raise
    time.sleep(2)


def ogq_open():
    t = c.new_tab("https://creators.ogq.me/profile/verification", profile="Profile 1")
    try:
        time.sleep(4)
        c.run_js(t, """window.__r=null;fetch('/api/user/verification/identity',{method:'POST',credentials:'include',
          headers:{'content-type':'application/json'},body:'{}'}).then(r=>r.json()).then(j=>window.__r=j.redirectUrl||'ERR').catch(e=>window.__r='ERR '+e);1""")
        time.sleep(3)
        url = c.run_js(t, "window.__r")
    finally:
        c.close_tab(t)
    if not url or not url.startswith("http"):
        sys.exit(f"RESULT: FAILED {url}")
    c.new_tab(url, profile="Profile 1")
    time.sleep(4)
    print("RESULT: OPENED — 이어서 send --match mobile-ok")


def open_popup():
    t = c.new_tab(a.value, profile="Profile 1")
    time.sleep(4)
    try:
        c.rclick(t, sel=f'input[value="{a.button}"]')
    except RuntimeError:
        c.rclick(t, text=a.button)
    time.sleep(5)
    ok = any("siren24" in x[3] or "mobile-ok" in x[3] or "checkplus" in x[3] or "kcp" in x[3] for x in c.tabs(with_id=True))
    print("SITE_TAB", t)
    print("RESULT:", "OPENED — 이어서 send --match <창 주소>" if ok else "FAILED 팝업 안 열림")


def wait_code():
    import json, subprocess
    tok, ch = os.environ.get("RAM_NOTI_TG_TOKEN"), str(os.environ.get("RAM_NOTI_TG_CHAT_ID"))
    if not tok:
        sys.exit("RESULT: FAILED RAM_NOTI_TG_TOKEN 없음 — set -a; source ~/.claude/.env")
    af, t0 = "/tmp/pass-answer.txt", int(time.time())
    subprocess.run(["curl", "-s", "-m", "15", "-d", f"chat_id={ch}", "--data-urlencode",
                    "text=[인증번호 요청]\n- 방금 휴대폰으로 온 본인확인 6자리만 답장해 주세요",
                    f"https://api.telegram.org/bot{tok}/sendMessage"], capture_output=True)
    end, last = time.time() + a.timeout, time.time()
    while time.time() < end:
        code = None
        try:
            ups = json.loads(subprocess.check_output(["curl", "-s", "-m", "15", f"https://api.telegram.org/bot{tok}/getUpdates?offset=-20"]))["result"]
            for u in ups:
                m = u.get("message", {})
                if m.get("date", 0) > t0 and str(m.get("chat", {}).get("id")) == ch:
                    x = re.search(r"\b(\d{6})\b", m.get("text", ""))
                    code = x.group(1) if x else code
        except Exception:
            pass
        if not code and os.path.exists(af) and os.path.getmtime(af) > t0:
            x = re.search(r"(\d{6})", open(af).read())
            code = x.group(1) if x else None
        if code:
            a.value = code
            a.cmd = "code"
            return main()
        if time.time() - last > 120:
            body = text(a.match)
            if "만료" in body or "통신사를" in body:
                sys.exit("RESULT: EXPIRED — open부터 다시")
            if "시간연장" in body:
                c.press(a.match, text="시간연장")
            last = time.time()
        time.sleep(5)
    sys.exit("RESULT: TIMEOUT")


def main():
    if a.cmd == "ogq-open":
        return ogq_open()
    if a.cmd == "open":
        return open_popup()
    try:
        c.ref(a.match)  # 탭이 없으면 RuntimeError
    except RuntimeError:
        sys.exit(f"RESULT: FAILED '{a.match}' 탭 없음 — 사이트에서 휴대폰 인증 창을 먼저 연다")
    t = a.match
    if a.cmd == "wait":
        return wait_code()
    if a.cmd == "extend":
        c.press(t, text="시간연장")
        print("RESULT: EXTENDED")
        return
    if a.cmd == "code":
        if not re.fullmatch(r"\d{6}", a.value or ""):
            sys.exit("usage: code <6자리>")
        print(put(t, 'e.placeholder=="인증번호"', a.value))
        time.sleep(0.5)
        # 확인 버튼은 press가 안 먹고 DOM click만 먹는다
        c.run_js(t, """setTimeout(()=>[...document.querySelectorAll("button,a")].filter(b=>b.offsetParent)
          .find(b=>["확인","다음"].includes(b.innerText.trim())).click(),10);1""")
        time.sleep(4)
        try:
            body = text(t)
        except RuntimeError:
            body = "(창 닫힘 — 원래 사이트로 결과 넘김. 사이트 쪽 인증 상태를 따로 확인)"
        print(body[:300])
        print("RESULT:", "FAILED" if re.search(r"일치하지|만료|오류", body) else "DONE")
        return
    info = open(os.path.expanduser("~/Documents/oguri-works/개인정보.md")).read()
    name = re.search(r"- 이름:\s*(\S+)", info).group(1)
    y, m, d = re.search(r"생년월일:\s*(\d{4})-(\d{2})-(\d{2})", info).groups()
    phone = re.search(r"01\d-\d{3,4}-\d{4}", info).group(0).replace("-", "")
    if "통신사를" in text(t):
        # SKT 알뜰폰 (siren24 창은 data-telco가 없어 첫 save 버튼)
        c.press(t, sel="#telcomSM,li.tel_item.save button[data-telco=skt],li.tel_item.save button")  # #telcomSM = NICE checkplus
        time.sleep(2)
    if "인증방법을" in text(t):
        c.press(t, text="문자(SMS) 인증")
        time.sleep(1)
        # mobile-ok: user_agree_checkbox / KCP: agreeTotal / siren24(서울평가정보): check_txt / 다날(teledit, 크몽): agree_checkbox
        c.press(t, sel="label[for=user_agree_checkbox],label[for=check_txt],label[for=agree_checkbox],label[for=mobileCertAgree],label[for=agreeTotal]")  # agreeTotal = KCP(cert.kcp.co.kr)
        time.sleep(1)
        nxt(t)
    if "이름을" in text(t):
        put(t, 'e.name=="userName_sms"||e.id=="userName"||e.id=="sms_username"', name)
        time.sleep(0.5)
        nxt(t)
    if "생년월일/성별" in text(t):
        put(t, 'e.placeholder=="생년월일 6자리"', y[2:] + m + d)
        time.sleep(0.5)
        put(t, 'e.id=="myNum2"||(e.type=="tel"&&!e.placeholder)', "1")  # myNum2 = NICE checkplus
        time.sleep(1.5)
    if "휴대폰번호를" in text(t):
        put(t, 'e.name=="mobileNo_sms"||e.id=="mobileNo"||e.id=="sms_mobileno"||e.id=="userPhone"', phone)
        time.sleep(1.5)
    if "보안문자를" in text(t):
        if not a.captcha:
            # mobile-ok는 data URL, siren24는 같은 출처 jsp 이미지(#simpleCaptchaImg) → 캔버스로 이미 뜬 그림을 뽑는다(다시 받으면 글자가 바뀜)
            src = c.run_js(t, """(()=>{const d=[...document.querySelectorAll("img")].find(i=>i.src.startsWith("data:"));if(d)return d.src;
              const i=document.getElementById("simpleCaptchaImg")||document.getElementById("captcha")||[...document.querySelectorAll("img")].filter(i=>i.offsetParent).find(i=>/captcha/i.test(i.id+i.src+i.className)),k=document.createElement("canvas");k.width=i.naturalWidth;k.height=i.naturalHeight;
              k.getContext("2d").drawImage(i,0,0);return k.toDataURL("image/png")})()""", 30)
            open(CAPTCHA_PNG, "wb").write(base64.b64decode(src.split(",", 1)[1]))
            print(f"RESULT: CAPTCHA {CAPTCHA_PNG} — 읽어서 send --captcha <값>")
            return
        put(t, 'e.placeholder=="보안문자"||e.id=="captchaInput"||e.id=="inputCaptcha"||e.id=="captchaAnswer"', a.captcha)
        time.sleep(1)
        nxt(t)
        time.sleep(1)
    if "입력정보를" in text(t):  # KCP(cert.kcp.co.kr): 보안문자 뒤 '다음' 대신 '확인'
        c.press(t, text="확인")
        time.sleep(4)
    body = text(t)
    if "인증번호 6자리" in body:
        print("RESULT: SMS_SENT — 폰에 온 6자리를 code 로")
    else:
        print(body[:300])
        print("RESULT: FAILED")


main()
