#!/usr/bin/env python3
"""[제출] 가비아 도메인 네임서버를 바꾼다(소유자 인증 = 이메일 인증번호, gmail_code.py로 읽음).

  gabia_nameserver.py 글쓰기공모전.kr aitana.ns.cloudflare.com merlin.ns.cloudflare.com            # DRY_RUN
  gabia_nameserver.py 글쓰기공모전.kr aitana.ns.cloudflare.com merlin.ns.cloudflare.com --submit
로그아웃이면 가비아 '구글 로그인'(remin1994) — 팝업이라 실제 클릭(rclick)과 cliclick 좌표로 계정을 고른다.
함정(2026-10-28 실측):
- 탭·라디오·버튼은 mantine이라 JS click이 안 먹는다 → rclick. 입력칸은 JS 값이 안 들어간다 → rclick + cmd+a 지우고 rtype.
- 입력칸에 type 속성이 없다(input[type=text] 안 잡힘) → input[name="nameServers.N.value"].
- '인증번호가 전송되었습니다'·'인증 완료'·'변경 신청하시겠습니까?'·'완료' 는 네이티브 alert/confirm — 떠 있는 동안 JS 실행이 멈춘다. Return 키로 닫는다(confirm은 Return = 확인).
- 반영은 신청 직후가 아니라 몇 분 뒤 .kr 레지스트리(dig NS <도메인> @b.dns.kr)에서 확인한다. 화면 목록은 한동안 옛 값.
기본 tmux 서버에선 Chrome Apple 이벤트가 -1743 → tmux -L gh 창에서 돌린다.
"""
import re, subprocess, time
from _common import Blocked, emit, parser, run, tab
import chromectl as c

ap = parser(__doc__, submit=True)
ap.add_argument("domain", help="가비아 목록에 보이는 이름(한글 그대로)")
ap.add_argument("ns", nargs="+")
a = ap.parse_args()
LIST = "https://domains.gabia.com/manage/domain/all"


def key(k):
    subprocess.run(["cliclick", f"kp:{k}"], check=True); time.sleep(2)


def btn(tid, label):  # 정확히 이 글자인 보이는 버튼에 표시를 달고 실제 클릭
    r = c.run_js(tid, f"""(()=>{{const b=[...document.querySelectorAll('[role=dialog] button,button')].filter(e=>e.offsetParent&&e.innerText.trim()=={label!r})[0];
      if(!b)return 'NF';b.setAttribute('data-cx','1');b.scrollIntoView({{block:'center'}});return 'OK'}})()""")
    if r != "OK": raise RuntimeError(f"버튼 없음 {label}")
    c.rclick(tid, "[data-cx='1']"); c.run_js(tid, "document.querySelector(\"[data-cx='1']\").removeAttribute('data-cx');1")


def login(tid):
    if "accounts.gabia.com" not in c.run_js(tid, "location.href"):
        return
    c.front(tid); c.rclick(tid, text="구글 로그인"); time.sleep(6)
    # 계정 선택은 별도 창(팝업): chromectl 탭 목록에 안 보인다. remin1994가 첫 줄이라는 가정 아래 Return으로 고르지 않고 직접 찾는다.
    js = 'var e=document.querySelector("[data-identifier=\\"remin1994@gmail.com\\"]");if(e){e.click();"OK"}else{"NF"}'
    out = subprocess.run(["osascript", "-e", 'tell application "Google Chrome"\nrepeat with w in windows\nif URL of active tab of w contains "accounts.google.com" then return execute active tab of w javascript "' + js.replace('"', '\\"') + '"\nend repeat\nend tell'],
                         capture_output=True, text=True).stdout.strip()
    time.sleep(8)
    if "accounts.gabia.com" in c.run_js(tid, "location.href"):
        raise Blocked(f"GABIA_LOGIN_NEEDED (구글 계정 선택 {out or '실패'} — 팝업에서 remin1994를 직접 눌러야 함)")


def main():
    with tab(LIST, a) as tid:
        time.sleep(8); login(tid)
        c.goto(tid, LIST); time.sleep(8)
        href = c.run_js(tid, f"(()=>{{const x=[...document.querySelectorAll('a')].find(a=>a.innerText.trim()=={a.domain!r});return x?x.href:''}})()")
        if not href: raise Blocked(f"NOT_FOUND {a.domain}")
        c.goto(tid, href); time.sleep(8); c.front(tid)
        c.rclick(tid, text="네임서버/DNS호스트/DNSSEC"); time.sleep(5)
        txt = c.page_text(tid); cur = re.findall(r"\n\d차\n\n(\S+)", txt[txt.find("네임 서버"):])
        if [x.lower() for x in cur[:len(a.ns)]] == [x.lower() for x in a.ns]:
            emit({"current": cur}, "ALREADY", "이미 같은 네임서버"); return
        if not a.submit:
            emit({"current": cur, "want": a.ns}, "DRY_RUN", "바꾸려면 --submit"); return
        btn(tid, "설정"); time.sleep(4)
        c.rclick(tid, "[role=dialog] input[type=radio][value=ns]"); time.sleep(1)
        n = int(c.run_js(tid, "document.querySelectorAll('[role=dialog] input[name^=nameServers]').length"))
        for i in range(n):
            c.rclick(tid, f'[role=dialog] input[name="nameServers.{i}.value"]'); time.sleep(0.5)
            subprocess.run(["cliclick", "kd:cmd", "t:a", "ku:cmd", "kp:delete"], check=True)
            if i < len(a.ns): c.rtype(value=a.ns[i])
        c.rclick(tid, "[role=dialog] input[type=radio][value=email]"); time.sleep(2)
        btn(tid, "인증번호 발송"); time.sleep(4); key("return")  # alert '인증번호가 전송되었습니다'
        time.sleep(15)
        r = subprocess.run(["python3", "gmail_code.py", "from:gabia 인증번호", "--newer", "15m"], capture_output=True, text=True, timeout=240,
                           cwd=__file__.rsplit("/", 1)[0])
        m = re.search(r"^CODE (\d+)", r.stdout, re.M)
        if not m: raise RuntimeError("가비아 인증번호 메일을 못 찾음")
        c.rclick(tid, '[role=dialog] input[placeholder="인증번호 입력"]'); c.rtype(value=m.group(1))
        btn(tid, "인증"); time.sleep(4); key("return")  # alert '인증이 성공적으로 완료되었습니다'
        btn(tid, "적용"); time.sleep(3); key("return")  # confirm '네임서버 변경 신청을 진행하시겠습니까?'
        time.sleep(5); key("return")                     # alert '네임서버 변경 신청이 완료되었습니다'
        emit({"domain": a.domain, "ns": a.ns}, "SUBMITTED", "몇 분 뒤 dig NS <도메인> @b.dns.kr 로 반영 확인")


run(main, a, f"가비아(domains.gabia.com) 로그인 상태에서 {a.domain} 상세 → 네임서버/DNS호스트/DNSSEC → 네임서버 설정을 {' '.join(a.ns)}로 바꾸고 소유자 이메일 인증 후 적용.")
