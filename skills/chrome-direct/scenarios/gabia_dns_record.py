#!/usr/bin/env python3
"""[제출] 가비아 DNS(dns.gabia.com) 레코드 값을 바꾸거나 새로 넣는다.

  gabia_dns_record.py eodimeok.kr A@=104.21.92.210 CNAMEwww=eodimeok.kr.            # DRY_RUN(지금 값만 출력)
  gabia_dns_record.py 글쓰기공모전.kr A@=104.21.53.133 Awww=104.21.53.133 --submit
  키 = 타입+호스트(A@, Awww, CNAMEwww). 있으면 값만 바꾸고(mod), 없으면 새로 넣는다(add).
왜 쓰나: NS를 Cloudflare 등으로 옮긴 직후, 옛 가비아 NS를 캐시한 리졸버(KT 168.126.63.1 등, .kr 위임 TTL 하루)가
  가비아 레코드를 계속 준다. 옛 호스팅(Vercel 76.76.21.21)이 남아 있으면 일부 사용자에게 404/402가 보인다(2026-10-28 글쓰기공모전.kr·eodimeok.kr).
  레코드가 비어 있으면 그 사용자에겐 접속이 아예 안 된다(상권.kr).
함정(2026-10-28 실측):
- '수정' 버튼은 jQuery 위임 이벤트인데, Chrome AppleScript JS는 격리된 월드라 jQuery가 안 보이고 click()도 안 먹는다
  → <script> 태그를 넣어 페이지 메인 월드에서 실행(main()). 결과는 body data 속성으로 받는다.
- 화면 입력칸 대신 레이어(#records_modify)의 숨은 값(.hidden_area status=mod/add, data)을 바꾸고 dnsSet.saveRecordEvent()를 부른다.
  저장 뒤 '설정이 완료되었습니다' 네이티브 alert가 JS를 멈춘다 → setTimeout으로 부르고 '확인' 좌표를 실제 클릭.
- 로그인은 '구글 로그인' 팝업: 팝업 창에서 [data-identifier="remin1994@gmail.com"]을 AppleScript로 누른다(gabia_nameserver.py와 같음).
기본 tmux 서버에선 Chrome Apple 이벤트가 -1743 → tmux -L gh 창에서 돌린다.
"""
import json, re, subprocess, time
from _common import Blocked, emit, parser, run, tab
import chromectl as c

ap = parser(__doc__, submit=True)
ap.add_argument("domain", help="가비아 목록에 보이는 이름(한글 그대로)")
ap.add_argument("records", nargs="+", help="타입호스트=값 (예: A@=1.2.3.4)")
a = ap.parse_args()
want = {}
for r in a.records:
    k, v = r.split("=", 1)
    m = re.fullmatch(r"(A|AAAA|CNAME|TXT|MX)(.+)", k)
    if not m: raise SystemExit(f"키 형식: A@, Awww, CNAMEwww — {k}")
    want[k] = (m.group(1), m.group(2), v)


def ok():  # 네이티브 alert '확인' 실제 클릭(gabia_nameserver.py와 같은 좌표)
    subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate']); time.sleep(1)
    b = subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to get bounds of front window'], capture_output=True, text=True).stdout
    x1, y1, x2, _ = (list(map(int, re.findall(r"-?\d+", b))) + [0, 30, 1920, 0])[:4] if b.strip() else (0, 30, 1920, 0)
    subprocess.run(["cliclick", f"c:{(x1 + x2) // 2 + 171},{y1 + 189}"]); time.sleep(3)


def main_world(tid, code):
    c.run_js(tid, "(()=>{const s=document.createElement('script');s.textContent=" + json.dumps(
        "try{document.body.dataset.cxr=String((function(){" + code + "})())}catch(e){document.body.dataset.cxr='ERR '+e}")
        + ";document.body.dataset.cxr='';document.head.appendChild(s);s.remove();return 1})()")
    time.sleep(1)
    return c.run_js(tid, "document.body.dataset.cxr")


def login(tid):
    if "accounts.gabia.com" not in c.run_js(tid, "location.href"):
        return
    c.run_js(tid, "(()=>{const e=[...document.querySelectorAll('a,button')].filter(x=>x.offsetParent&&/구글/.test(x.innerText))[0];e.setAttribute('data-cx','gg');return 1})()")
    c.front(tid); c.rclick(tid, "[data-cx='gg']"); time.sleep(7)
    pick = '''tell application "Google Chrome"
  repeat with w in windows
    if URL of active tab of w contains "accounts.google.com" then execute active tab of w javascript "(function(){var e=document.querySelector('[data-identifier=\\"remin1994@gmail.com\\"]');if(e){e.click();return 'OK'}return 'NF'})()"
  end repeat
end tell'''
    subprocess.run(["osascript", "-e", pick], capture_output=True, text=True); time.sleep(15)
    if "accounts.gabia.com" in c.run_js(tid, "location.href"):
        raise Blocked("GABIA_LOGIN_NEEDED (구글 계정 팝업에서 remin1994 선택 실패)")


def records(tid):
    return main_world(tid, "return JSON.stringify(jQuery('#records_modify #record_list .hidden_area').map(function(){var f=function(n){return jQuery(this).find('[name='+n+']').val()}.bind(this);return [[f('type')+f('host'),f('data')]]}).get())")


def main():
    with tab("https://dns.gabia.com/dns/internals", a) as tid:
        time.sleep(8); login(tid)
        c.goto(tid, "https://dns.gabia.com/dns/internals"); time.sleep(8)
        r = c.run_js(tid, f"(()=>{{const tr=[...document.querySelectorAll('tr')].find(r=>r.querySelector('.fl')&&r.querySelector('.fl').innerText.trim()=={a.domain!r});if(!tr)return 'NF';[...tr.querySelectorAll('a,button')].find(x=>x.innerText.trim()=='설정').click();return 'OK'}})()")
        if r != "OK": raise Blocked(f"NOT_FOUND {a.domain}")
        time.sleep(8)
        c.run_js(tid, "(()=>{[...document.querySelectorAll('button')].find(x=>x.innerText.trim()=='레코드 수정').click();return 1})()"); time.sleep(4)
        if main_world(tid, "return jQuery('#domain_hidden').val()") != a.domain: raise RuntimeError("다른 도메인 화면")
        cur = dict(json.loads(records(tid)))
        todo = {k: v for k, v in want.items() if cur.get(k) != v[2]}
        if not todo:
            emit({"current": cur}, "ALREADY", "이미 같은 값"); return
        if not a.submit:
            emit({"current": cur, "change": {k: v[2] for k, v in todo.items()}}, "DRY_RUN", "바꾸려면 --submit"); return
        mod = {k: v[2] for k, v in todo.items() if k in cur}
        add = [{"status": "add", "type": t, "ttl": "600", "services_idx": "19", "services_name": "DNS 설정", "addition_service_name": "",
                "is_layer": "Y", "seqno": "", "host": h, "data": d, "priority": "", "service": "", "protocol": "", "weight": "", "port": "",
                "target": "", "hasdns": ""} for k, (t, h, d) in todo.items() if k not in cur]
        main_world(tid, "var $=jQuery,ch=" + json.dumps(mod) + ";$('#records_modify #record_list .hidden_area').each(function(){var k=$(this).find('[name=type]').val()+$(this).find('[name=host]').val();if(ch[k]!==undefined){$(this).find('[name=status]').val('mod');$(this).find('[name=data]').val(ch[k])}});"
                   + "$('#record_modify_tbl #record_list .record_no_list_tr').remove();$('#record_list_template').tmpl(" + json.dumps(add, ensure_ascii=False) + ").appendTo('#records_modify #record_list');"
                   + "setTimeout(function(){dnsSet.saveRecordEvent()},50);return 1")
        time.sleep(4); c.front(tid); ok(); time.sleep(5)
        txt = c.page_text(tid)
        emit({"domain": a.domain, "after": txt[txt.find("레코드 개수"):txt.find("도메인 연결 설정")].strip()}, "SUBMITTED",
             f"확인: dig +short A <호스트> @ns.gabia.co.kr")


run(main, a, f"가비아 DNS(dns.gabia.com)에서 {a.domain} → 레코드 수정 → {' '.join(a.records)} 로 바꾸고 저장.")
