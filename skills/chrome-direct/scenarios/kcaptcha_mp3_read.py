#!/usr/bin/env python3
# CLAUDE_P_MAX=0 (모델 호출 없음)
"""[읽기] 그누보드 kcaptcha(자동등록방지 숫자)를 그림 대신 음성 mp3로 정확히 읽는다.
사용: kcaptcha_mp3_read.py --match <탭> [--fill]   → RESULT: <숫자> (--fill이면 #captcha_key에 넣음)
- 11/17 commonz042 가입: 그림 판독(서브에이전트) 2번 연속 틀림. kcaptcha_mp3.php가 주는 mp3는
  /plugin/kcaptcha/mp3/basic/<0-9>.mp3 를 그대로 이어 붙인 파일이라, 숫자 파일과 바이트로 맞추면 100% 맞다.
- 페이지 세션(쿠키)으로 POST해야 해서 탭 안 XHR로 주소를 받는다. 새로고침(#captcha_reload)하면 숫자가 바뀌니 받은 뒤 누르지 않는다.
"""
import argparse, os, sys, urllib.parse, requests
sys.path.insert(0, os.path.expanduser("~/.claude/skills/chrome-direct"))
import chromectl as c  # noqa: E402
ap = argparse.ArgumentParser(); ap.add_argument("--match", required=True); ap.add_argument("--fill", action="store_true"); a = ap.parse_args()
url = c.run_js(a.match, '(()=>{const x=new XMLHttpRequest();x.open("POST","/plugin/kcaptcha/kcaptcha_mp3.php",false);x.send();return x.responseText})()')
if not url or not str(url).startswith("http"):
    sys.exit(f"RESULT: FAILED mp3 주소 못 받음 ({url})")
base = urllib.parse.urljoin(url, "/plugin/kcaptcha/mp3/basic/")
cap = requests.get(url, timeout=20).content
dig = {d: requests.get(f"{base}{d}.mp3", timeout=20).content for d in "0123456789"}
out, i = "", 0
while i < len(cap):
    for d, b in dig.items():
        if b and cap.startswith(b, i):
            out += d; i += len(b); break
    else:
        sys.exit(f"RESULT: FAILED {i}바이트에서 숫자 파일과 안 맞음(읽은 것 {out})")
if a.fill:
    c.fill(a.match, "[name=captcha_key]", out)
print("RESULT:", out)
