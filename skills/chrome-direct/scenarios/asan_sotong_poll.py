#!/usr/bin/env python3
"""[쓰기] 아산시 시민참여 온라인플랫폼(sotong) 설문 응모 — 로그인 → 칸 채우기 → 등록.
2026-11-24 아산 플랫폼 명칭 공모 제출 때 쓴 순서를 그대로 옮김.
  asan_sotong_poll.py <pds_no> --answers answers.json [--submit]
answers.json: {"txt478":"...", "example485":"1", ...}  값 "@name" "@phone" "@address" "@email" 는 personal_info 로 채움.
로그인: ~/.claude/.env ASAN_SOTONG_ID / ASAN_SOTONG_PW (아산시 통합회원, 강래민 remin1994).
페이지 함수는 격리 world 라 직접 못 불러서 <script> 주입으로 loginProc()/pollSendit() 실행.
--submit 없으면 채우기까지만(dry-run). 등록 뒤 버튼이 '이미 등록을 완료하셨습니다.'로 바뀌면 접수 확인.
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.expanduser("~/.claude/skills/chrome-direct"))
sys.path.insert(0, os.path.dirname(__file__))
import chromectl as c
from _common import personal_info

ap = argparse.ArgumentParser(); ap.add_argument("pds_no"); ap.add_argument("--answers", required=True)
ap.add_argument("--submit", action="store_true"); ap.add_argument("--profile", default="Profile 1"); a = ap.parse_args()
URL = f"https://www.asan.go.kr/sotong/develop/opinion_poll/?tb_nm=setting_opinionPoll&m_mode=view&pds_no={a.pds_no}&PageNo=1&tab=all"
P = personal_info(); MAP = {"@name": P["name"], "@phone": P["phone"], "@address": P["address"], "@email": P["email"]}
ans = {k: MAP.get(v, v) for k, v in json.load(open(a.answers)).items()}

def inject(t, code):
    return c.run_js(t, "(()=>{const s=document.createElement('script');s.textContent=" + json.dumps(code) + ";document.body.appendChild(s);return 1})()")

t = c.new_tab("https://www.asan.go.kr/sotong/", profile=a.profile); time.sleep(4)
if "로그아웃" not in (c.run_js(t, "document.body.innerText") or ""):
    c.run_js(t, "var f=document.forms['loginForm']; f.action='/passni/sso/spLogin.php'; f.submit(); 1"); time.sleep(5)
    c.run_js(t, "(()=>{document.getElementById('login_id').value=" + json.dumps(os.environ["ASAN_SOTONG_ID"]) +
             ";[...document.querySelectorAll('input[type=password]')].find(e=>e.offsetParent).value=" + json.dumps(os.environ["ASAN_SOTONG_PW"]) + ";return 1})()")
    inject(t, "loginProc()"); time.sleep(7)
c.run_js(t, f"location.href={json.dumps(URL)};1"); time.sleep(6)
if "이미 등록을 완료" in (c.run_js(t, "document.documentElement.innerHTML") or ""):
    print("RESULT: ALREADY 이미 등록된 계정"); sys.exit(0)
js = "(()=>{const V=" + json.dumps(ans, ensure_ascii=False) + ";const o=[];for(const k in V){const e=document.getElementById(k);if(e){e.value=V[k];e.dispatchEvent(new Event('input',{bubbles:true}));o.push(k+':'+(e.value===V[k]))}else{const r=document.querySelector('input[name='+k+'][value=\"'+V[k]+'\"]');if(r){r.checked=true;o.push(k+':radio')}else o.push(k+':MISSING')}}return o.join(',')})()"
res = c.run_js(t, js); print("FILL", res)
if "MISSING" in res or "false" in res: print("RESULT: FAIL 칸 채우기"); sys.exit(1)
if not a.submit: print("RESULT: DRYRUN"); sys.exit(0)
inject(t, "window.alert=function(m){document.documentElement.setAttribute('data-al',String(m))};window.confirm=function(){return true};pollSendit();"); time.sleep(8)
c.run_js(t, f"location.href={json.dumps(URL)};1"); time.sleep(6)
ok = "이미 등록을 완료" in (c.run_js(t, "document.documentElement.innerHTML") or "")
print("RESULT:", "OK 등록 확인" if ok else "UNKNOWN 등록 상태 확인 못 함 — 재제출 금지, 화면 확인")
