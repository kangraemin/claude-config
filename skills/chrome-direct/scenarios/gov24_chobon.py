#!/usr/bin/env python3
"""[발급] 정부24 주민등록표 초본 발급 → 문서출력 화면을 JPG로 저장.

  gov24_chobon.py --sido 서울특별시 --sigungu 강남구 [--out chobon.jpg]   → 1단계: 로그인 창에서 카카오 간편인증 요청까지 하고 멈춤
  gov24_chobon.py --approved --sido .. --sigungu .. [--out ..]            → 폰에서 승인한 뒤: 인증 완료 → 신청 → 문서출력 → JPG 저장

- 마지막 줄: RESULT: OK <경로> | NEEDS_PHONE_APPROVAL | FAIL <이유>  (종료코드 0 / 2 / 1)
- 사람 몫: 카카오톡에서 인증 요청 승인 1번뿐. NEEDS_PHONE_APPROVAL 이 나오면 사용자에게 승인만 부탁하고 --approved 로 다시 부른다.
- 사전 조건: Chrome 로그인 프로필이 열려 있고(--profile), 쓰는 터미널에 Apple Events·손쉬운 사용 권한이 있다. cliclick 설치.
- 이름·생년월일·휴대폰은 ~/Documents/*/개인정보.md '## 대표자' 섹션에서 패턴으로 뽑는다(출력 안 함).
- 초본(tpSeq=02)을 쓴다. 등본(01)은 세대주만 나와 동거인 신청자 이름이 없을 수 있다.
  '선택 발급' 에서 체크박스를 전부 해제 상태로 두면 과거주소·주민번호 뒷자리가 안 나온다.
- 왜 화면 조작인가: 정부24 발급은 공개 API가 없고 간편인증이 iframe, 문서출력은 팝업이라
  합성 클릭이 차단된다 → 실제 마우스 클릭(cliclick)으로 눌러야 뷰어 창이 열린다.
- AhnLab Safe Transaction '연결 확인' 창이 뜨면 System Events 로 '허용'을 누른다(헬퍼 포함).
- 검증: 2026-10-27 수동 흐름으로 성공. 이 스크립트는 py_compile 만 통과, 실행 미검증(로그인·카카오 승인 필요).
"""
import argparse
import base64
import glob
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.expanduser("~/.claude/skills/chrome-direct"))
import chromectl as c  # noqa: E402

START = "https://www.gov.kr/mw/AA020InfoCappView.do?HighCtgCD=A01010001&CappBizCD=13100000015"
FORM = "https://plus.gov.kr/minwon/apply/applyMinwonForm?cappBizCd=13100000015&tpSeq=02"
LIST = "mbrAplySrvcList"
IFR = "document.querySelector('iframe[src*=simpleCert]').contentDocument"

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--approved", action="store_true", help="카카오톡 승인을 마친 뒤 이어서 진행")
ap.add_argument("--sido", required=True, help="예: 서울특별시")
ap.add_argument("--sigungu", required=True, help="예: 강남구 (옵션 텍스트에 포함되면 선택)")
ap.add_argument("--out", default=os.path.expanduser("~/Downloads/gov24_chobon.jpg"))
ap.add_argument("--profile", default="Profile 1")
ap.add_argument("--provider", default="카카오톡")
ap.add_argument("--keep-tab", action="store_true")
a = ap.parse_args()


class Fail(Exception):
    pass


def result(status, note=""):
    print(f"RESULT: {status} {note}".rstrip())
    sys.exit({"OK": 0, "NEEDS_PHONE_APPROVAL": 2}.get(status, 1))


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


def find_tab(sub):
    for line in c.tabs():
        if sub in str(line):
            return sub
    return None


def wait_js(t, body, timeout=25, every=1.0):
    end, last = time.time() + timeout, None
    while time.time() < end:
        try:
            last = c.js_json(t, body)
            if last:
                return last
        except c.NeedsPermission:
            raise
        except Exception as e:
            last = str(e)
        time.sleep(every)
    raise Fail(f"timeout: {str(last)[:150]}")


def allow_astx():
    """AhnLab Safe Transaction 연결 확인 창의 '허용' 클릭(없으면 아무 일 없음)."""
    s = '''tell application "System Events"
      if exists process "astxStatus" then
        tell process "astxStatus"
          repeat with w in windows
            try
              click button "허용" of w
              return "ALLOWED"
            end try
          end repeat
        end tell
      end if
    end tell
    return "NONE"'''
    try:
        return c.osa(s, timeout=10)
    except Exception:
        return "ERR"


def open_login():
    """발급하기 → 로그인 화면(plus.gov.kr/login)까지."""
    t = c.new_tab(START, a.profile)
    time.sleep(3)
    href = wait_js(t, "const e=[...document.querySelectorAll('a')].find(e=>(e.getAttribute('href')||'').includes('AA040OfferMainFrm')&&e.offsetParent);return e?e.href:null")
    c.goto(t, href)
    wait_js(t, "return location.host.includes('plus.gov.kr')&&!!document.querySelector('button.login-type')", 30)
    return t


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


def finish_login(t):
    wait_js(t, f"""const b=[...{IFR}.querySelectorAll('button,a')].find(e=>e.innerText&&e.innerText.replace(/\\s/g,'').includes('인증완료')&&e.offsetParent);
      if(!b)return null;b.click();return 'OK'""", 40)
    time.sleep(4)


def apply_form(t):
    c.goto(t, FORM)
    wait_js(t, "return !!document.querySelector('select[name$=_sido]')&&!!document.querySelector('#requestBtn')", 30)
    r = c.js_json(t, f"""const sel=document.querySelector('select[name$=_sido]');
      const o=[...sel.options].find(o=>o.text.trim()=={a.sido!r});if(!o)return 'NOSIDO';
      sel.value=o.value;sel.dispatchEvent(new Event('change',{{bubbles:true}}));return 'OK'""")
    if r != "OK":
        raise Fail(f"시도 선택 {r}")
    wait_js(t, f"const s=document.querySelector('select[name$=_sigungu]');return s&&[...s.options].some(o=>o.text.includes({a.sigungu!r}))", 15)
    c.js_json(t, f"""const s=document.querySelector('select[name$=_sigungu]');
      const o=[...s.options].find(o=>o.text.includes({a.sigungu!r}));s.value=o.value;s.dispatchEvent(new Event('change',{{bubbles:true}}));return 1""")
    # '선택 발급' 라디오 → 체크박스는 전부 해제 유지(과거주소·뒷자리 미표시)
    c.js_json(t, """const l=[...document.querySelectorAll('label,input[type=radio]')].find(e=>(e.innerText||e.value||'').includes('선택 발급')||(e.innerText||'').includes('선택발급'));
      if(l)l.click();return 1""")
    time.sleep(0.8)
    c.js_json(t, "document.querySelectorAll('input[type=checkbox]:checked').forEach(e=>{if(e.offsetParent&&!e.disabled)e.click()});return 1")
    c.click(t, sel="#requestBtn")
    allow_astx()
    wait_js(t, f"return location.href.includes({LIST!r})&&document.body.innerText.includes('처리완료')", 60)


def print_viewer(t):
    """문서출력 실제 클릭 → ezpdfwv 뷰어 → 캔버스 합성 → JPG."""
    time.sleep(2)
    c.rclick(t, text="문서출력")  # JS click 은 팝업 차단
    v = None
    for _ in range(30):
        allow_astx()
        v = find_tab("ezpdfwv/viewer")
        if v:
            break
        time.sleep(1)
    if not v:
        raise Fail("뷰어 창이 안 열림(문서출력 팝업)")
    try:
        wait_js(v, """const d=document.querySelector('#viewerFrame').contentDocument;
          return d&&[...d.querySelectorAll('canvas')].filter(x=>x.width==1490).length>0""", 60)
        time.sleep(2)
        c.js_json(v, """const d=document.querySelector('#viewerFrame').contentDocument;
          const cs=[...d.querySelectorAll('canvas')].filter(x=>x.width==1490);
          const o=document.createElement('canvas');o.width=cs[0].width;o.height=cs[0].height;
          const g=o.getContext('2d');g.fillStyle='#fff';g.fillRect(0,0,o.width,o.height);
          cs.forEach(x=>g.drawImage(x,0,0));
          window.__jpg=o.toDataURL('image/jpeg',0.95).split(',')[1];return window.__jpg.length""")
        n = c.js_json(v, "return window.__jpg.length")
        buf, step = [], 150000
        for i in range(0, n, step):
            buf.append(c.js_json(v, f"return window.__jpg.slice({i},{i + step})"))
        data = base64.b64decode("".join(buf))
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "wb") as f:
            f.write(data)
    finally:
        if not a.keep_tab:
            try:
                c.close_tab(v)
            except Exception:
                pass
    if len(data) < 10000:
        raise Fail("저장된 JPG가 비정상적으로 작음")


def main():
    who = person()
    tab = None
    try:
        if not a.approved:
            tab = open_login()
            request_kakao(tab, who)
            print("APPROVE_ON_PHONE")
            a.keep_tab = True  # 승인 뒤 같은 탭에서 이어간다
            result("NEEDS_PHONE_APPROVAL", "카카오톡에서 인증 요청을 승인한 뒤 --approved 로 다시 실행")
        tab = find_tab("plus.gov.kr/login") or find_tab("plus.gov.kr")
        if not tab:
            raise Fail("로그인 탭 없음 — --approved 없이 처음부터 다시 실행")
        finish_login(tab)
        apply_form(tab)
        print_viewer(tab)
        result("OK", a.out)
    finally:
        if tab and not a.keep_tab:
            try:
                c.close_tab(tab)
            except Exception:
                pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except c.NeedsPermission as e:
        result("FAIL", f"권한 필요: {e}")
    except Exception as e:
        result("FAIL", f"{type(e).__name__}: {str(e)[:200]}")
