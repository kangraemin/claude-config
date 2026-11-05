#!/usr/bin/env python3
"""서울시 이택스 지방세 조회·카카오페이 납부. tmux -L gh 안에서 돌린다.

사용법: etax_pay.py <전자납부번호 19자리> [--submit]
- 기본은 조회만 한다(세목·금액·납부기한 출력).
- --submit: 카카오페이 > 카톡결제로 결제요청을 보내고 폰 승인을 기다린다(5분). 승인 뒤 납부 완료 문구를 읽는다.

사전 조건: 사용자가 이 건 납부를 직접 지시했을 것. 폰 카카오톡 승인은 사람 몫이다.
왜 화면 조작인가: 이택스·카카오페이 납부 API가 없다.

함정
- 내용은 top이 아니라 첫 iframe 문서 안에 있다.
- '세입금 납부(취소불가)'를 JS click으로 누르면 결제 팝업이 차단돼 아무 일도 안 난다(토스페이 11/5).
  실제 마우스(cliclick)로 눌러야 팝업이 열린다.
- 납부 완료 뒤 결제창 '확인'은 안 눌러도 창이 닫히고 이택스가 완료 화면으로 바뀐다.
- 재결제 금지: 실패로 보여도 다시 조회해 납부 버튼이 있을 때만 다시 시도한다.
"""
import argparse, json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.expanduser("~/.config/claude-accounts/personal/skills/chrome-direct"))
import chromectl as c

F = "document.querySelector('iframe,frame').contentDocument"
INFO = os.path.expanduser("~/Documents/oguri-works/개인정보.md")


def doc(t, body):
    return c.run_js(t, "(()=>{const d=%s;%s})()" % (F, body))


def field(txt, label):
    m = re.search(label + r"\s*[:\s]\s*([^\n\t]{1,40})", txt)
    return m.group(1).strip() if m else "?"


def lookup(t, no):
    c.goto(t, "https://etax.seoul.go.kr/")
    time.sleep(8)
    doc(t, "const i=d.getElementById('in_search');i.value=%s;setTimeout(()=>d.getElementById('in_search_btn').click(),10);return 1" % json.dumps(no))
    time.sleep(7)
    txt = doc(t, "return d.body.innerText") or ""
    can = doc(t, "const b=d.getElementById('btnDiv_napbu');return b&&b.offsetParent?'yes':'no'")
    amt = re.findall(r"\d{1,3}(?:,\d{3})+", txt)
    print("납부버튼", can, "| 금액", amt[:3], "| 납부기한", (re.findall(r"20\d\d\.\d\d\.\d\d", txt) or ["?"])[0])
    return can == "yes"


def personal():
    s = open(INFO, encoding="utf8").read()
    ph = re.search(r"휴대폰:\s*(\d{3})-(\d{3,4})-(\d{4})", s)
    bd = re.search(r"생년월일:\s*\d\d(\d\d)-(\d\d)-(\d\d)", s)
    return "".join(ph.groups()), "".join(bd.groups())


def to_consent(t):
    doc(t, "setTimeout(()=>d.getElementById('btnDiv_napbu').click(),10);return 1")
    time.sleep(6)
    doc(t, "d.getElementById('chBank3').click();return 1")
    time.sleep(2)
    doc(t, "d.getElementById('sel_kakaopay').click();setTimeout(()=>d.getElementById('napbuBtn').click(),10);return 1")
    time.sleep(8)
    doc(t, "const b=d.getElementById('chk_agree_nocncl');if(b&&!b.checked)setTimeout(()=>b.click(),10);return 1")
    time.sleep(5)


def real_click_pay(t):
    _, win = c.ref(t)
    c.front(t)
    c.jxa(f"{win}.index = 1; C.activate()")
    time.sleep(0.6)
    s = json.loads(c.run_js(t, """(()=>{const d=%s;const bs=[...d.querySelectorAll('button,a,input[type=button]')].filter(a=>a.offsetParent&&/세입금 납부/.test(a.innerText||a.value||''));
if(bs.length!=1)return JSON.stringify({n:bs.length});
const fr=document.querySelector('iframe,frame').getBoundingClientRect(),r=bs[0].getBoundingClientRect();
return JSON.stringify({n:1,x:Math.round(window.screenX+fr.left+r.left+r.width/2),y:Math.round(window.screenY+window.outerHeight-window.innerHeight+fr.top+r.top+r.height/2),kakao:/납부방법\\s*:?\\s*카카오/.test(d.body.innerText)})})()""" % F))
    if s.get("n") != 1 or not s.get("kakao"):
        raise RuntimeError(f"납부 확인창 이상: {s}")
    subprocess.run(["cliclick", f"c:{s['x']},{s['y']}"], check=True)


def kakao_request():
    for _ in range(20):
        rows = [r for r in c.tabs(with_id=True) if "online-payment.kakaopay.com" in r[3]]
        if rows:
            break
        time.sleep(1)
    else:
        raise RuntimeError("카카오페이 창이 안 열림")
    k = "id:" + rows[0][4]
    time.sleep(2)
    c.run_js(k, "(()=>{const e=[...document.querySelectorAll('a,button,li,span,div')].filter(a=>a.children.length==0&&a.innerText&&a.innerText.trim()=='카톡결제')[0];(e.closest('a,button,[role=tab]')||e).click();return 1})()")
    time.sleep(3)
    phone, birth = personal()
    r = json.loads(c.run_js(k, """(()=>{const set=(id,v)=>{const e=document.getElementById(id);Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,v);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));};
set('phoneNumber',%s);set('dateOfBirth',%s);
const b=[...document.querySelectorAll('button')].filter(x=>x.offsetParent&&x.innerText.trim()=='결제요청')[0];
if(!b||b.disabled)return JSON.stringify({ok:false});setTimeout(()=>b.click(),10);return JSON.stringify({ok:true})})()""" % (json.dumps(phone), json.dumps(birth))))
    if not r["ok"]:
        raise RuntimeError("결제요청 버튼이 안 켜짐")


def main():
    a = argparse.ArgumentParser()
    a.add_argument("number")
    a.add_argument("--submit", action="store_true")
    a = a.parse_args()
    no = re.sub(r"\D", "", a.number)
    t = c.new_tab("https://etax.seoul.go.kr/", profile="Profile 1")
    try:
        can = lookup(t, no)
        if not can:
            print("RESULT: NOT_PAYABLE 납부 버튼 없음(이미 납부했거나 번호 오류)")
            return
        if not a.submit:
            print("RESULT: DRY_RUN")
            return
        to_consent(t)
        real_click_pay(t)
        kakao_request()
        print("폰 카카오톡에서 결제요청을 승인하세요", flush=True)
        for _ in range(60):
            time.sleep(5)
            txt = doc(t, "return d.body.innerText") or ""
            if re.search(r"원\s*납부 완료되었습니다", txt):
                print("RESULT: PAID")
                return
        print("RESULT: TIMEOUT 납부 안 된 것으로 단정하지 말고 다시 조회")
    finally:
        c.close_tab(t)


if __name__ == "__main__":
    main()
