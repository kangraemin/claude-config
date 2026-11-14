#!/usr/bin/env python3
"""Usage: play_release.py --dev <개발자ID> --app <앱ID> status | sha1 | managed [--submit] | publish [--submit] | submit [--submit] | upload --track <트랙ID> --aab <파일> [--notes "<ko-KR 노트>"] [--submit]

Play Console 앱 한 개의 출시 상태를 읽고, 앱 서명 SHA-1을 얻고, '검토를 위해 변경사항 N개 제출'을 누른다.
- status: 게시 개요의 제출 버튼 글자·활성 여부·차단 문제 수를 읽는다. 누르지 않는다.
- sha1: 앱 서명 키 SHA-1과 카카오용 base64 해시를 출력한다. 카카오 등록은 kakao_app_setup.py --hash.
- upload: 트랙에 '새 버전 만들기' → AAB 업로드 → 출시 노트 → 다음 → 저장(검토 제출은 안 함). 같은 버전 코드가 이미 트랙에 있으면 건너뛴다.
  미제출 출시가 있으면 새 출시가 그것을 대체한다. --submit 없으면 업로드까지만 하고 저장하지 않는다.
- upload 추가(2026-11-10): '버전 코드 이미 사용'이면(dry-run으로 먼저 올린 경우 등) 앱 라이브러리에서 방금 올린 번들을 추가한다. submit은 이미 '검토 중'인 변경이 있으면 '검토 다시 시작'(기존 검토 취소 후 대기 재시작)을 누른다.
- managed: 관리형 게시(승인돼도 '게시 준비됨'에서 대기, 수동 게시) 상태를 읽고 --submit이면 켠다. 이미 켜져 있으면 그대로 둔다.
  드롭다운은 JS click·cliclick으로 안 열리고 pointer/mouse 이벤트 연속 dispatch(CK)로만 열린다. 검토 중인 변경사항이 있어도 켤 수 있다.
- submit: 문제 0개이고 버튼이 켜졌을 때만 진행. --submit 없으면 dry-run. 실패 시 재클릭하지 않는다.
Pre: Profile 1 로그인. 화면 조작인 이유: 게시 개요 제출과 조직 계정 앱의 선언은 공개 API로 못 한다.
Gotcha: Angular라 c.shot으로 앞에 띄운 뒤 읽는다. 지문 값은 DOM에 없고 복사 버튼에만 있어 c.rclick 실제 클릭 후 pbpaste로 읽는다
        (JS click은 클립보드에 안 들어간다). 정규식은 20바이트 전체 일치로 본다(SHA-256 앞부분이 걸린다).
        한국 계정 정보 3칸이 비면 '문제 1개'로 막힌다(무료 앱도 면제 없음) → play_iap_bulk.py korea-info --submit 먼저.
        타겟 API·데이터 보안·건강 앱 선언 오류는 빠른 검사에 최대 14분 걸린 뒤 뜬다.
        첫 프로덕션은 트랙 국가가 0개라 '저장하려면 오류를 수정하세요'로 막힌다 → tracks/<ID>?tab=countryAvailability 에서
        '국가/지역 수정' → mat-checkbox[aria-label='모든 행 선택']의 .mat-checkbox-container에 마우스 이벤트(그냥 click은 안 먹음) → 저장(178개).
        --track production 도 된다(콘솔이 숫자 트랙 ID로 바꿈). 출시 노트 기본 언어가 en-US면 <en-US>도 넣는다.
- publish: 관리형 게시로 '게시 준비됨'인 승인 변경을 '변경사항 N개 게시'로 공개한다.
RESULT: PUBLISHED | MANAGED_ON | MANAGED_OFF | READY <버튼> | BLOCKED <문제 수> | NOT_READY | SUBMITTED | DRY_RUN_READY | SHA1 <해시> | FAIL
"""
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time

from _common import c, js, parser, tab

ap = parser("Play Console release status / signing SHA-1 / submit", submit=True)
ap.add_argument("action", choices=["status", "sha1", "submit", "upload", "managed", "publish"])
ap.add_argument("--track", help="upload: 트랙 ID (tracks/<ID> 주소의 숫자)")
ap.add_argument("--aab", help="upload: 올릴 .aab 경로")
ap.add_argument("--notes", default="", help="upload: 출시 노트 본문(ko-KR)")
ap.add_argument("--library", action="store_true", help="upload: 파일을 다시 올리지 않고 앱 라이브러리에서 버전 코드가 가장 큰 번들을 추가(이미 올라간 경우)")
ap.add_argument("--dev", required=True)
ap.add_argument("--app", required=True)
a = ap.parse_args()
BASE = f"https://play.google.com/console/u/0/developers/{a.dev}/app/{a.app}"
PNG = os.path.join(tempfile.gettempdir(), "play_release.png")


def out(s):
    print("RESULT:", s)
    sys.exit(0 if s.split()[0] in ("READY", "SUBMITTED", "DRY_RUN_READY", "SHA1", "MANAGED_ON") else 2)


def show(tid, wait=8):
    time.sleep(wait)
    try:
        c.shot(tid, PNG)  # 캡처는 화면을 앞으로 띄우는 용도. 실패해도(탭 색인 오류 등) 이미 누른 동작은 되돌리지 않고 이어 간다
    except Exception as e:
        print(f"shot skipped: {e}", file=sys.stderr)
    time.sleep(3)


def status(tid):
    show(tid)
    r = js(tid, """const x=document.body.innerText; const m=x.match(/문제 (\\d+)개가 모든 변경사항/);
      const b=[...document.querySelectorAll('button')].find(e=>e.offsetParent&&/검토를 위해 변경사항 \\d+개 제출/.test(e.innerText));
      return {issues:m?+m[1]:0, btn:b?b.innerText.trim():'', on:!!(b&&!b.disabled&&b.getAttribute('aria-disabled')!='true')}""")
    print("issues", r["issues"], "| button", r["btn"] or "(none)", "| enabled", r["on"])
    act = js(tid, """const x=document.body.innerText; const i=x.indexOf('제출 활동');
      return i<0?'':x.slice(i,i+600)""") or ""
    r["activity"] = act
    print("ACTIVITY:", " / ".join(l.strip() for l in act.splitlines() if l.strip())[:500] or "(제출 활동 섹션 없음)")
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
      if(d){const b=[...d.querySelectorAll('button')].find(e=>/제출|전송|검토 다시 시작/.test(e.innerText)); if(b)b.click()} return 1""")
    show(tid, 6)
    x = js(tid, "return document.body.innerText")
    # 이미 '검토 중'인 변경이 있으면 '검토를 다시 시작하시겠어요?'(검토 취소 후 대기 재시작)가 뜬다 → 위에서 '검토 다시 시작'을 누른다(2026-11-10)
    out("SUBMITTED" if (re.search(r"검토를 위해 제출|제출됨|검사가 성공적으로 완료되는 즉시", x) and not re.search(r"변경사항이 아직 검토를 위해 제출되지 않음", x)) else "FAIL 제출 후 상태 확인 안 됨 — 재클릭 금지, 화면 확인")


def publish(tid):
    """관리형 게시로 '게시 준비됨'에 머문 승인된 변경을 공개한다(2026-11-14 스레드언팔)."""
    show(tid)
    b = js(tid, """const b=[...document.querySelectorAll('button')].find(e=>e.offsetParent&&/변경사항 \\d+개 게시/.test(e.innerText));
      return b?{t:b.innerText.trim(),on:!b.disabled&&b.getAttribute('aria-disabled')!='true'}:null""")
    print("publish button", b)
    if not b or not b["on"]:
        out("NOT_READY 게시 버튼 없음")
    if not a.submit:
        out("DRY_RUN_READY " + b["t"])
    js(tid, """[...document.querySelectorAll('button')].find(e=>e.offsetParent&&/변경사항 \\d+개 게시/.test(e.innerText)).click(); return 1""")
    show(tid, 3)
    js(tid, """const d=[...document.querySelectorAll('[role=dialog],mat-dialog-container,material-dialog')].find(e=>e.offsetParent);
      if(d){const b=[...d.querySelectorAll('button')].find(e=>/변경사항 출시|^게시$/.test(e.innerText.trim())); if(b)b.click()} return 1""")
    show(tid, 8)
    x = js(tid, "return document.body.innerText")
    print(x[:600])
    out("PUBLISHED" if not re.search(r"변경사항 \d+개 게시", x) else "FAIL 게시 후에도 버튼이 남음 — 재클릭 금지, 화면 확인")


CK = ("const ck=e=>['pointerdown','mousedown','pointerup','mouseup','click'].forEach(k=>e.dispatchEvent(new MouseEvent(k,{bubbles:true,cancelable:true,view:window})));"
      "const bt=s=>[...document.querySelectorAll('button,a[role=button]')].find(x=>x.offsetParent&&x.innerText.includes(s));")



def big_upload(tid, path, N=4_000_000):
    """c.upload_file(300KB 조각)는 90MB AAB에서 조각 400번 중 하나만 늦어도 -1728로 죽는다(2026-11-06).
    4MB 조각으로 보내고 조각마다 5번까지 다시 보낸다. 로컬 서버 fetch는 Play 콘솔이 막는다(요청이 서버에 안 닿음)."""
    import base64
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    def rj(s, t=90):
        for k in range(5):
            try:
                return js(tid, s, t)
            except Exception as e:
                print("retry", k, str(e)[:80]); time.sleep(5)
        out("FAIL 조각 전송 실패")
    rj("window.__cu=[];return 1")
    n = 0
    for i in range(0, len(b64), N):
        rj("window.__cu[%d]=%s;return 1" % (n, json.dumps(b64[i:i+N]))); n += 1
    return rj("""if(window.__cu.length!=%d||window.__cu.some(x=>!x)) return 'missing'; const s=atob(window.__cu.join('')); window.__cu=null;
const u=new Uint8Array(s.length); for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);
const e=[...document.querySelectorAll('input[type=file]')].find(x=>(x.accept||'').includes('.aab'))||document.querySelector('input[type=file]'); if(!e) return 'noinput';
const dt=new DataTransfer(); dt.items.add(new File([u],%s,{type:'application/octet-stream'})); e.files=dt.files;
e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); return 'ok '+u.length""" % (n, json.dumps(os.path.basename(path))))


def lib_add(tid):
    """'버전 코드 이미 사용' 뒤: 실패한 파일 항목을 지우고 '라이브러리에서 추가' 대화상자의 첫 행(가장 최근 업로드)을 추가한다. 추가된 버전 코드를 돌려준다."""
    for _ in range(4):  # 같은 파일이 두 줄(성공 1·'이미 사용' 1)로 붙는 경우가 있어 실패 줄을 전부 지운다(2026-11-14 먹맵)
        if not js(tid, CK + "const b=[...document.querySelectorAll('button')].find(x=>x.offsetParent&&x.innerText.trim()=='clear'); if(b)ck(b); return !!b"):
            break
        time.sleep(2)
    js(tid, CK + "ck(bt('라이브러리에서 추가'));return 1")
    time.sleep(4)
    # 2026-11-14 먹맵: 대화상자 안 querySelectorAll이 비어 나온다(오버레이). 문서 전체에서 버전 코드가 가장 큰 행의 체크박스를 누른다
    js(tid, CK + "const vc=[...document.querySelectorAll('ess-cell[essfield=versionCode]')].filter(e=>e.getClientRects().length&&/^\\d+$/.test(e.innerText.trim())).sort((p,q)=>+q.innerText-+p.innerText)[0];"
       "if(!vc) return 0; const cb=vc.parentElement.querySelector('mat-checkbox'); if(!cb) return 0; ck(cb); return 1")
    time.sleep(2)
    ok = js(tid, CK + "const b=[...document.querySelectorAll('button')].find(x=>x.offsetParent&&x.innerText.trim()=='버전에 추가'); if(!b||b.disabled) return 0; ck(b); return 1")
    print("lib_add", ok)
    time.sleep(6)
    x = js(tid, "return document.body.innerText")
    sec = x.split("App Bundle 업로드", 1)[-1].split("이전 버전", 1)[0]
    m = re.search(r"\n(\d+) \(([^)]+)\)", sec)
    return m.group(1) if (ok and m) else None


def upload(tid):
    import zipfile
    if not a.track or not a.aab or not os.path.exists(a.aab):
        out("FAIL --track·--aab 필요")
    try:  # 버전 코드는 bundletool 없이 알 수 없어 파일명이 아니라 업로드 후 화면에서 읽는다
        zipfile.ZipFile(a.aab).close()
    except Exception:
        out("FAIL aab가 zip이 아님")
    show(tid)
    js(tid, CK + "const b=bt('새 버전 만들기')||bt('버전 수정'); if(b) ck(b); return !!b")  # 임시 출시가 있으면 '버전 수정'
    show(tid, 9)
    if "/prepare" not in js(tid, "return location.href"):
        out("FAIL 새 버전 화면이 안 열림")
    for _ in range(12):  # 첫 출시 화면은 파일 칸이 몇 초 늦게 붙는다(2026-11-10 어디먹 noinput)
        if js(tid, "return document.querySelectorAll('input[type=file]').length"):
            break
        time.sleep(3)
    code = None
    tried_lib = False
    if a.library:  # 2026-11-14 먹맵: 업로드가 같은 파일을 두 번 붙여 '이미 사용' 줄이 남으면 라이브러리 추가도 막힌다 → 깨끗한 새 버전에서 라이브러리로만 추가
        tried_lib = True
        code = lib_add(tid)
    else:
        print(big_upload(tid, os.path.abspath(a.aab)))
    for _ in range(0 if code else 36):
        time.sleep(5)
        x = js(tid, "return document.body.innerText")
        sec = x.split("App Bundle 업로드", 1)[-1].split("이전 버전", 1)[0]  # 아래쪽 '포함되지 않음'의 옛 버전을 잡지 않게 자른다
        m = re.search(r"\n(\d+) \(([^)]+)\)", sec)
        if m:
            code = m.group(1); break
        if re.search(r"이미 사용|already been used", x) and not tried_lib:
            # 같은 AAB가 이미 앱 라이브러리에 있다(앞서 dry-run으로 올렸거나 임시 출시가 날아간 경우): 실패 항목 지우고 라이브러리에서 가장 최근 것을 추가(2026-11-10 나사톡톡)
            tried_lib = True
            code = lib_add(tid)
            if code:
                break
        if re.search(r"이미 사용|already been used|오류", x) and tried_lib:
            out("FAIL 업로드 거부: " + (re.search(r"[^\n]*(이미 사용|already been used|오류)[^\n]*", x).group(0)))
    if not code:
        x = js(tid, "return document.body.innerText")
        print("PAGE:", re.sub(r"\s+", " ", x.split("App Bundle", 1)[-1])[:1500])
        out("FAIL 업로드 후 버전 코드 안 보임")
    print("version_code", code)
    if a.notes:
        js(tid, "const e=[...document.querySelectorAll('textarea')].find(x=>x.offsetParent);const p=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value');"
                "p.set.call(e,%s);['input','change','blur'].forEach(n=>e.dispatchEvent(new Event(n,{bubbles:true})));return 1" % json.dumps("<ko-KR>\n" + a.notes + "\n</ko-KR>"))
    if not a.submit:
        out("DRY_RUN_READY 업로드됨, 저장 안 함 version " + code)
    js(tid, CK + "ck(bt('다음'));return 1")
    show(tid, 9)
    if "/review" not in js(tid, "return location.href"):
        out("FAIL 검토 화면으로 안 넘어감(출시명·노트 확인)")
    js(tid, CK + "const b=[...document.querySelectorAll('button')].find(x=>x.offsetParent&&x.innerText.trim()=='저장');ck(b);return 1")
    show(tid, 4)
    x = js(tid, "return document.body.innerText")
    out(("SUBMITTED 저장됨 version " + code) if "변경사항이 저장되었습니다" in x else "FAIL 저장 확인 안 됨 — 재클릭 금지")


def managed(tid):
    st = lambda: js(tid, """return [...document.querySelectorAll('[debug-id="managed-publishing-dropdown"] .button-text')].map(e=>e.innerText.trim())[0]||''""")
    show(tid)
    cur = st(); print("state", cur)
    if "사용 설정됨" in cur:
        out("MANAGED_ON 이미 켜져 있음")
    if not a.submit:
        out("MANAGED_OFF dry-run(--submit이면 켬)")
    js(tid, CK + "ck(document.querySelector('[debug-id=\"managed-publishing-dropdown\"] [role=button]'));return 1")
    time.sleep(2)
    js(tid, CK + """const e=[...document.querySelectorAll('material-select-dropdown-item')].find(x=>x.getClientRects().length&&x.innerText.includes('관리형 게시가 사용 설정됨')); if(e) ck(e); return !!e""")
    time.sleep(4)
    c.goto(tid, BASE + "/publishing")
    show(tid)
    out("MANAGED_ON 켬" if "사용 설정됨" in st() else "FAIL 켠 뒤 확인 안 됨")


path = {"sha1": "/keymanagement", "upload": f"/tracks/{a.track}"}.get(a.action, "/publishing")
with tab(BASE + path, a) as tid:
    if a.action == "sha1":
        sha1(tid)
    elif a.action == "submit":
        submit(tid)
    elif a.action == "publish":
        publish(tid)
    elif a.action == "managed":
        managed(tid)
    elif a.action == "upload":
        upload(tid)
    else:
        r = status(tid)
        out(f"BLOCKED {r['issues']}" if r["issues"] else (f"READY {r['btn']}" if r["on"] else "NOT_READY"))
