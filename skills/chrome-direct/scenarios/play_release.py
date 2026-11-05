#!/usr/bin/env python3
"""Usage: play_release.py --dev <개발자ID> --app <앱ID> status | sha1 | submit [--submit]

Play Console 앱 한 개의 출시 상태를 읽고, 앱 서명 SHA-1을 얻고, '검토를 위해 변경사항 N개 제출'을 누른다.
- status: 게시 개요의 제출 버튼 글자·활성 여부·차단 문제 수를 읽는다. 누르지 않는다.
- sha1: 앱 서명 키 SHA-1과 카카오용 base64 해시를 출력한다. 카카오 등록은 kakao_app_setup.py --hash.
- submit: 문제 0개이고 버튼이 켜졌을 때만 진행. --submit 없으면 dry-run. 실패 시 재클릭하지 않는다.
Pre: Profile 1 로그인. 화면 조작인 이유: 게시 개요 제출과 조직 계정 앱의 선언은 공개 API로 못 한다.
Gotcha: Angular라 c.shot으로 앞에 띄운 뒤 읽는다. 지문 값은 DOM에 없고 복사 버튼에만 있어 c.rclick 실제 클릭 후 pbpaste로 읽는다
        (JS click은 클립보드에 안 들어간다). 정규식은 20바이트 전체 일치로 본다(SHA-256 앞부분이 걸린다).
        한국 계정 정보 3칸이 비면 '문제 1개'로 막힌다(무료 앱도 면제 없음) → play_iap_bulk.py korea-info --submit 먼저.
        타겟 API·데이터 보안·건강 앱 선언 오류는 빠른 검사에 최대 14분 걸린 뒤 뜬다.
RESULT: READY <버튼> | BLOCKED <문제 수> | NOT_READY | SUBMITTED | DRY_RUN_READY | SHA1 <해시> | FAIL
"""
import base64
import os
import re
import subprocess
import sys
import tempfile
import time

from _common import c, js, parser, tab

ap = parser("Play Console release status / signing SHA-1 / submit", submit=True)
ap.add_argument("action", choices=["status", "sha1", "submit"])
ap.add_argument("--dev", required=True)
ap.add_argument("--app", required=True)
a = ap.parse_args()
BASE = f"https://play.google.com/console/u/0/developers/{a.dev}/app/{a.app}"
PNG = os.path.join(tempfile.gettempdir(), "play_release.png")


def out(s):
    print("RESULT:", s)
    sys.exit(0 if s.split()[0] in ("READY", "SUBMITTED", "DRY_RUN_READY", "SHA1") else 2)


def show(tid, wait=8):
    time.sleep(wait)
    c.shot(tid, PNG)
    time.sleep(3)


def status(tid):
    show(tid)
    r = js(tid, """const x=document.body.innerText; const m=x.match(/문제 (\\d+)개가 모든 변경사항/);
      const b=[...document.querySelectorAll('button')].find(e=>e.offsetParent&&/검토를 위해 변경사항 \\d+개 제출/.test(e.innerText));
      return {issues:m?+m[1]:0, btn:b?b.innerText.trim():'', on:!!(b&&!b.disabled&&b.getAttribute('aria-disabled')!='true')}""")
    print("issues", r["issues"], "| button", r["btn"] or "(none)", "| enabled", r["on"])
    return r


def sha1(tid):
    show(tid)
    js(tid, """const b=[...document.querySelectorAll('[debug-id="latest-classical-certificate"] button')].find(e=>/SHA-1/.test(e.getAttribute('aria-label')||''));
      if(b){b.setAttribute('data-sha1','1');b.scrollIntoView({block:'center'})} return !!b""")
    time.sleep(1)
    old = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
    c.rclick(tid, sel='[data-sha1="1"]')
    time.sleep(1.5)
    v = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout.strip()
    subprocess.run(["pbcopy"], input=old, text=True)
    if not re.fullmatch(r"([0-9A-Fa-f]{2}:){19}[0-9A-Fa-f]{2}", v):
        out("FAIL SHA-1 복사 안 됨")
    print("sha1", v)
    out("SHA1 " + base64.b64encode(bytes.fromhex(v.replace(":", ""))).decode())


def submit(tid):
    r = status(tid)
    if r["issues"]:
        out(f"BLOCKED {r['issues']}")
    if not r["on"]:
        out("NOT_READY")
    if not a.submit:
        out("DRY_RUN_READY")
    js(tid, """const b=[...document.querySelectorAll('button')].find(e=>e.offsetParent&&/검토를 위해 변경사항 \\d+개 제출/.test(e.innerText)); b.click(); return 1""")
    show(tid, 3)
    # 확인 창이 뜨면 그 안의 제출 버튼을 한 번 누른다
    js(tid, """const d=[...document.querySelectorAll('[role=dialog],mat-dialog-container,material-dialog')].find(e=>e.offsetParent);
      if(d){const b=[...d.querySelectorAll('button')].find(e=>/제출|전송/.test(e.innerText)); if(b)b.click()} return 1""")
    show(tid, 6)
    x = js(tid, "return document.body.innerText")
    out("SUBMITTED" if re.search(r"검토 중|검토를 위해 제출|제출됨", x) else "FAIL 제출 후 상태 확인 안 됨 — 재클릭 금지, 화면 확인")


path = "/keymanagement" if a.action == "sha1" else "/publishing"
with tab(BASE + path, a) as tid:
    if a.action == "sha1":
        sha1(tid)
    elif a.action == "submit":
        submit(tid)
    else:
        r = status(tid)
        out(f"BLOCKED {r['issues']}" if r["issues"] else (f"READY {r['btn']}" if r["on"] else "NOT_READY"))
