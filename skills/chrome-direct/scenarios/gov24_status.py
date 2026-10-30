#!/usr/bin/env python3
"""정부24 신청 내역(MyGOV > 서비스 신청 내역)에서 민원 처리 상태를 읽는다. 아무것도 제출하지 않는다.

  gov24_status.py --match 통신판매업            → 로그인돼 있으면 바로 읽음, 아니면 카카오 간편인증 요청까지 하고 멈춤
  gov24_status.py --match 통신판매업 --approved → 사용자가 카톡에서 승인한 뒤 같은 탭에서 '인증 완료' → 내역 읽기
- 마지막 줄: RESULT: OK <상태줄> | NEEDS_PHONE_APPROVAL | NOT_FOUND | FAIL <이유>  (종료코드 0 / 2 / 3 / 1)
- 사람 몫: 카카오톡 인증 요청 승인 1번. 값(이름·생년월일·휴대폰)은 개인정보.md '## 대표자'에서 패턴으로 읽고 출력하지 않는다.
- 왜 화면 조작인가: 정부24 신청 내역은 공개 API가 없고 간편인증이 iframe이다. 로그인 흐름은 gov24_chobon.py와 같다.
- Chrome Apple 이벤트라 tmux -L gh(또는 Ghostty)에서 돌린다.
"""
import argparse
import glob
import os
import re
import sys
import time

sys.path.insert(0, os.path.expanduser("~/.claude/skills/chrome-direct"))
import chromectl as c  # noqa: E402

LIST = "https://plus.gov.kr/mypage/mbrAplySrvcList"
IFR = "document.querySelector('iframe[src*=simpleCert]').contentDocument"
TABFILE = os.path.expanduser("~/.cache/gov24_status.tab")

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--match", required=True, help="찾을 민원 이름 일부 (예: 통신판매업)")
ap.add_argument("--approved", action="store_true")
ap.add_argument("--profile", default="Profile 1")
ap.add_argument("--provider", default="카카오톡")
ap.add_argument("--wait", type=int, default=0, help="요청 뒤 이 초만큼 승인을 기다리며 '인증 완료'를 계속 눌러 본다(10/30: 승인 뒤 늦게 --approved 하면 만료돼 로그인 안 됨)")
a = ap.parse_args()


class Fail(Exception):
    pass


def result(status, note=""):
    print(f"RESULT: {status} {note}".rstrip())
    sys.exit({"OK": 0, "NEEDS_PHONE_APPROVAL": 2, "NOT_FOUND": 3}.get(status, 1))


def person():
    txt = open(sorted(glob.glob(os.path.expanduser("~/Documents/*/개인정보.md")))[0], encoding="utf-8").read()
    m = re.search(r"^##\s*대표자\s*$(.*?)(?=^##\s|\Z)", txt, re.S | re.M)
    sec = m.group(1) if m else txt
    name = re.search(r"이름[^:：\n]*[:：]\s*\**\s*([가-힣]{2,5})", sec)
    birth = re.search(r"(\d{4})-(\d{2})-(\d{2})", sec)
    phone = re.search(r"(01\d)-(\d{3,4})-(\d{4})", sec)
    if not (name and birth and phone):
        raise Fail("개인정보.md '## 대표자' 에서 이름/생년월일/휴대폰을 못 찾음")
    p = phone.groups()
    return {"name": name.group(1), "birth": "".join(birth.groups()), "p1": p[0], "p2": p[1] + p[2]}


def wait_js(t, body, timeout=25, every=1.0):
    end, last = time.time() + timeout, None
    while time.time() < end:
        try:
            last = c.js_json(t, body)
            if last:
                return last
        except Exception as e:
            last = str(e)
        time.sleep(every)
    raise Fail(f"timeout: {str(last)[:150]}")


def request_kakao(t, who):
    c.click(t, text="간편인증")
    wait_js(t, f"return !!document.querySelector('iframe[src*=simpleCert]')&&!!{IFR}.body&&{IFR}.body.innerText.includes({a.provider!r})", 25)
    setv = """const S=(e,v)=>{e.focus();Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,v);
      for(const k of ['input','change','keyup'])e.dispatchEvent(new Event(k,{bubbles:true}));};"""
    r = c.js_json(t, f"""const d={IFR};
      const cand=[...d.querySelectorAll('*')].filter(e=>e.innerText&&e.innerText.trim()=={a.provider!r}&&e.offsetParent);
      cand.sort((x,y)=>x.getBoundingClientRect().width*x.getBoundingClientRect().height-y.getBoundingClientRect().width*y.getBoundingClientRect().height);
      if(!cand.length)return 'NOPROVIDER'; cand[0].click(); return 'OK'""")
    if r != "OK":
        raise Fail(f"공급자 선택 {r}")
    wait_js(t, f"return !!{IFR}.querySelector('#oacx_name')", 15)
    r = c.js_json(t, f"""{setv}const d={IFR};
      S(d.querySelector('#oacx_name'),{who['name']!r});S(d.querySelector('#oacx_birth'),{who['birth']!r});
      const sel=d.querySelector('select');
      if(sel){{const o=[...sel.options].find(o=>o.value=={who['p1']!r}||o.text.includes({who['p1']!r}));if(o){{sel.value=o.value;sel.dispatchEvent(new Event('change',{{bubbles:true}}));}}}}
      S(d.querySelector('#oacx_phone2'),{who['p2']!r});
      d.querySelector('#totalAgree').click();
      return d.querySelector('#oacx_name').value.length>0&&d.querySelector('#oacx_phone2').value.length>0""")
    if not r:
        raise Fail("간편인증 입력칸 채우기 실패")
    time.sleep(0.8)
    if c.js_json(t, f"const b={IFR}.querySelector('#oacx-request-btn-pc');if(!b)return 'NOBTN';b.click();return 'OK'") != "OK":
        raise Fail("인증 요청 버튼 없음")
    time.sleep(6)  # 10/30: 값이 안 맞으면 바로 '입력하신 정보로 인증을 진행할 수 없습니다' 안내가 뜬다 → 기다려 봐야 소용없다
    err = c.js_json(t, f"const x={IFR}.body.innerText; const m=x.match(/[^\\n]*(진행할 수 없습니다|확인 후 다시)[^\\n]*/); return m?m[0]:''")
    if err:
        raise Fail(f"간편인증 요청 거절: {err[:120]}")


def finish_login(t):
    wait_js(t, f"""const b=[...{IFR}.querySelectorAll('button,a')].find(e=>e.innerText&&e.innerText.replace(/\\s/g,'').includes('인증완료')&&e.offsetParent);
      if(!b)return null;b.click();return 'OK'""", 40)
    time.sleep(5)


def read_list(t):
    if "mbrAplySrvcList" not in c.js_json(t, "return location.href"):
        c.goto(t, LIST)
    wait_js(t, "return location.href.includes('mbrAplySrvcList')&&document.body.innerText.length>500", 30)
    time.sleep(3)
    txt = c.js_json(t, "return document.body.innerText")
    if "로그인이 필요한" in txt:
        raise Fail("로그아웃 상태 — --approved 없이 다시")
    lines = [x.strip() for x in txt.split("\n") if x.strip()]
    hits = [i for i, x in enumerate(lines) if a.match in x]
    if not hits:
        result("NOT_FOUND", f"신청 내역에 '{a.match}' 없음")
    for i in hits:
        print(" | ".join(lines[max(0, i - 2):i + 6]))
    i = hits[0]
    st = next((x for x in lines[i:i + 10] if re.search(r"처리중|처리완료|완료|취소|반려|접수|보완", x)), "?")
    return st


def main():
    tab = None
    try:
        if a.approved:
            tab = open(TABFILE).read().strip()
            finish_login(tab)
        else:
            tab = c.new_tab(LIST, a.profile)
            time.sleep(6)
            if "login" in c.js_json(tab, "return location.href") or "로그인이 필요한" in c.js_json(tab, "return document.body.innerText"):
                c.goto(tab, "https://plus.gov.kr/login?awqf=!2f")  # 목록은 로그아웃이면 '로그인이 필요한 서비스' 창만 띄우고 안 넘어간다
                time.sleep(4)
                wait_js(tab, "return !!document.querySelector('button.login-type')||document.body.innerText.includes('간편인증')", 20)
                request_kakao(tab, person())
                if a.wait:
                    print("APPROVE_ON_PHONE", flush=True)
                    end = time.time() + a.wait
                    first = time.time() + 30  # 승인 전에 '인증완료'를 누르면 요청이 깨질 수 있어 30초 뒤부터 누른다
                    while time.time() < end:
                        time.sleep(8)
                        if time.time() < first:
                            continue
                        c.js_json(tab, f"""const f=document.querySelector('iframe[src*=simpleCert]'); if(!f) return 0;
                          const b=[...f.contentDocument.querySelectorAll('button,a')].find(e=>e.innerText&&e.innerText.replace(/\\s/g,'').includes('인증완료')&&e.offsetParent);
                          if(b) b.click(); return 1""")
                        time.sleep(4)
                        if "login" not in c.js_json(tab, "return location.href"):
                            break
                    else:
                        raise Fail("승인 대기 시간 초과")
                    result("OK", read_list(tab))
                os.makedirs(os.path.dirname(TABFILE), exist_ok=True)
                open(TABFILE, "w").write(tab)
                tab = None  # 승인 뒤 같은 탭에서 이어간다
                result("NEEDS_PHONE_APPROVAL", "카카오톡에서 승인한 뒤 --approved 로 다시 실행")
        st = read_list(tab)
        result("OK", st)
    finally:
        if tab:
            try:
                c.close_tab(tab)
            except Exception:
                pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        result("FAIL", f"{type(e).__name__}: {str(e)[:200]}")
