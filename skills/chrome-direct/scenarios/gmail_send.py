#!/usr/bin/env python3
"""[제출] 공모전 메일 접수 (remin1994@gmail.com). 기본 dry-run: 보낸편지함 중복 확인 + 보낼 내용 요약만.
--submit: 중복 기록 확인 → _radar/jobs/<id>.submit.lock → 발송 → 보낸편지함에서 확인 (→ --proof 캡처).

발송 경로 (앞이 되면 뒤는 안 씀):
  1) SMTP smtp.gmail.com:465 — ~/.claude/.env 에 GMAIL_APP_PASSWORD 가 있을 때 (CLAUDE.md '구글 로그인 지키기')
  2) Gmail 웹 작성창 (실제 Chrome Profile 1) — 받는사람·제목·본문은 URL로 채우고, 첨부는 '파일 첨부' 버튼 →
     macOS 파일 창에서 ⌘⇧G + 경로 붙여넣기(cliclick). 실패하면 Codex로 넘김.

  gmail_send.py --to a@b.kr --subject "[공모전접수] ..." --body-file body.txt --attach f1.pdf --attach f2.hwpx --contest-id kead-regulation
  ... --submit --proof _radar/board/pdf/kead-regulation-proof.pdf
  ... --compose-only     # 웹 작성창만 채워 두고 멈춤(보내기 안 누름, 탭 남김) — 사람 눈 확인용
"""
import mimetypes
import os
import smtplib
import subprocess
import time
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlencode

from _common import ACCOUNT, Blocked, emit, guard_and_lock, js, mark_not_sent, parser, poll, run, tab
from _gmail import check_account, search, search_url
import chromectl as c

ap = parser(__doc__, submit=True)
ap.add_argument("--to", required=True, action="append", help="여러 명이면 반복")
ap.add_argument("--cc", action="append", default=[])
ap.add_argument("--subject", required=True)
ap.add_argument("--body-file", required=True)
ap.add_argument("--attach", action="append", default=[])
ap.add_argument("--account", default=ACCOUNT)
ap.add_argument("--proof", help="보낸편지함의 그 메일 화면을 .png/.pdf로 저장")
ap.add_argument("--force-resend", action="store_true", help="보낸편지함에 같은 메일이 있어도 보냄 (사용자 지시 있을 때만)")
ap.add_argument("--compose-only", action="store_true")
ap.add_argument("--web", action="store_true", help="앱 비밀번호가 있어도 웹으로")
a = ap.parse_args()
BODY = Path(a.body_file).read_text()
FILES = [Path(p).resolve() for p in a.attach]
SENTQ = f'in:sent to:{a.to[0]} subject:"{a.subject[:60]}"'


def app_password():
    try:
        return c.secret("GMAIL_APP_PASSWORD")
    except RuntimeError:
        return None


def send_smtp(pw):
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = a.account, ", ".join(a.to), a.subject
    if a.cc:
        m["Cc"] = ", ".join(a.cc)
    m.set_content(BODY)
    for f in FILES:
        mt = (mimetypes.guess_type(f.name)[0] or "application/octet-stream").split("/")
        m.add_attachment(f.read_bytes(), maintype=mt[0], subtype=mt[1], filename=f.name)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        s.login(a.account, pw)
        s.send_message(m)


def attach_via_datatransfer(tid, files):
    """Inject File objects into input[type=file] via DataTransfer (no native dialog). Returns attached count."""
    import base64, json
    js(tid, "window.__f=[]; return 1")
    for f in files:
        b = base64.b64encode(Path(f).read_bytes()).decode()
        js(tid, "window.__b=''; return 1")
        for k in range(0, len(b), 300000):
            js(tid, f"window.__b += {json.dumps(b[k:k+300000])}; return 1", 60)
        mime = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
        js(tid, f"""const s=atob(window.__b),u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);
          window.__f.push(new File([u],{json.dumps(Path(f).name)},{{type:{json.dumps(mime)}}}));window.__b='';return 1""")
    n = js(tid, """const ins=[...document.querySelectorAll('input[type=file]')]; const i=ins.find(x=>x.multiple)||ins[0]; if(!i) return -1;
      const dt=new DataTransfer(); window.__f.forEach(f=>dt.items.add(f)); i.files=dt.files;
      i.dispatchEvent(new Event('change',{bubbles:true})); return i.files.length""")
    if n != len(files):
        raise RuntimeError(f"DataTransfer 파일 수 불일치: {n}/{len(files)}")
    return poll(tid, f"return document.querySelectorAll('input[name=attach]').length >= {len(files)} && "
                     "![...document.querySelectorAll('[role=progressbar]')].some(__vis)", 180, 2)


def attach_via_dialog(tid, f):
    """Click 파일 첨부 → native dialog → ⌘⇧G, paste path, Return, Return."""
    n0 = js(tid, "return document.querySelectorAll('input[name=attach]').length")
    c.rclick(tid, sel='div[command="Files"], [aria-label^="파일 첨부"], [aria-label^="Attach files"]')
    time.sleep(1.5)
    subprocess.run(["pbcopy"], input=str(f).encode(), check=True)
    subprocess.run(["cliclick", "kd:cmd,shift", "t:g", "ku:cmd,shift"], check=True)
    time.sleep(1.0)
    subprocess.run(["cliclick", "kd:cmd", "t:v", "ku:cmd"], check=True)
    time.sleep(0.6)
    subprocess.run(["cliclick", "kp:return"], check=True)
    time.sleep(1.0)
    subprocess.run(["cliclick", "kp:return"], check=True)
    poll(tid, f"return document.querySelectorAll('input[name=attach]').length > {n0} && "
              "![...document.querySelectorAll('[role=progressbar]')].some(__vis)", 120)


def compose_web(tid):
    q = {"authuser": a.account, "view": "cm", "fs": "1", "to": ",".join(a.to), "su": a.subject, "body": BODY}
    if a.cc:
        q["cc"] = ",".join(a.cc)
    c.goto(tid, "https://mail.google.com/mail/?" + urlencode(q))
    poll(tid, "return !!document.querySelector('input[name=subjectbox]') && [...document.querySelectorAll('div[aria-label][contenteditable=true]')].some(__vis)", 40)
    got = js(tid, "return document.querySelector('input[name=subjectbox]').value")
    if got != a.subject:
        raise RuntimeError(f"제목 채움 불일치: {got!r}")
    # 2026-10-22: native dialog + cliclick hung ("timeout waiting"); DataTransfer injection attached 11 files fine.
    try:
        attach_via_datatransfer(tid, FILES)
    except Exception as e:
        print(f"[attach] DataTransfer failed ({e}); falling back to native dialog", flush=True)
        for f in FILES:
            attach_via_dialog(tid, f)
    names = js(tid, "return [...document.querySelectorAll('input[name=attach]')].map(e => (e.parentElement||{}).innerText || '')") or []
    if len(names) != len(FILES):
        raise RuntimeError(f"첨부 수 불일치: {len(names)}/{len(FILES)}")


def main():
    for f in FILES:
        if not f.exists():
            raise Blocked(f"NO_FILE {f}")
    size = sum(f.stat().st_size for f in FILES)
    pw = None if a.web else app_password()
    plan = {"from": a.account, "to": a.to, "cc": a.cc, "subject": a.subject, "bodyChars": len(BODY),
            "attachments": [f"{f.name} ({f.stat().st_size // 1024}KB)" for f in FILES], "totalMB": round(size / 1e6, 1),
            "route": "smtp" if pw else "web"}
    if size > 24.5e6:
        raise Blocked(f"TOO_BIG 첨부 {plan['totalMB']}MB > 25MB — 드라이브 링크로")
    with tab(search_url(SENTQ, a.account), a) as tid:
        prev = search(tid, SENTQ, a.account, 5)["rows"]
        plan["alreadyInSent"] = [f"{r['date']} {r['subject']}" for r in prev]
        if prev and not a.force_resend:
            emit(plan, "ALREADY_SENT", "보낸편지함에 같은 제목 — 안 보냄")
            raise Blocked("ALREADY_SENT")
        if a.compose_only:
            a.keep_tab = True
            compose_web(tid)
            emit(plan, "COMPOSED", "작성창 채움 — 보내기 안 누름, 탭 남김")
            return
        if not a.submit:
            emit(plan, "DRY_RUN", "--submit 으로 발송")
            return
        lock = guard_and_lock(a.contest_id)
        try:
            if pw:
                send_smtp(pw)
            else:
                compose_web(tid)
                r = js(tid, """const b = [...document.querySelectorAll('div[role=button]')].filter(e => __vis(e) &&
                    /^(보내기|Send)/.test(e.getAttribute('data-tooltip') || e.getAttribute('aria-label') || e.innerText))[0];
                  if (!b) return 'NOTFOUND'; __press(b); return 'OK';""")
                if r != "OK":
                    raise RuntimeError("보내기 버튼 못 찾음")
        except Exception as e:
            mark_not_sent(lock, f"발송 전 실패: {e}")
            raise
        if lock:
            (lock / "SENT.txt").write_text(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {plan['route']} to={','.join(a.to)}\n")
        # verify in Sent (search again from a fresh Gmail view)
        c.goto(tid, search_url(SENTQ, a.account))
        time.sleep(3)
        check_account(tid, a.account)
        rows = []
        for _ in range(10):
            rows = search(tid, SENTQ, a.account, 5)["rows"]
            if len(rows) > len(prev):
                break
            time.sleep(3)
            c.run_js(tid, "location.reload()")
            time.sleep(4)
        plan["sentNow"] = [f"{r['date']} {r['subject']} 첨부{len(r['attachments'])}" for r in rows]
        if len(rows) <= len(prev):
            emit(plan, "UNCONFIRMED", "발송했으나 보낸편지함에서 아직 안 보임 — 재발송 금지, 잠시 뒤 gmail_search로 확인")
            raise Blocked("UNCONFIRMED")
        if a.proof:
            from _gmail import open_row
            open_row(tid, 1)
            plan["proof"] = c.shot(tid, a.proof)
        emit(plan, "SENT", a.contest_id or "")


TASK = (f"Gmail 웹({a.account}, 실제 Chrome Profile 1)으로 메일 1통. 먼저 보낸편지함에서 `{SENTQ}` 검색 — 이미 있으면 보내지 말고 STATUS: NEEDS_OWNER ALREADY_SENT. "
        f"받는사람 {', '.join(a.to)}" + (f", 참조 {', '.join(a.cc)}" if a.cc else "") + f", 제목 `{a.subject}`, 본문은 파일 {Path(a.body_file).resolve()} 내용 그대로, "
        f"첨부 {', '.join(str(f) for f in FILES) or '없음'} (Chrome 플러그인 tab.playwright setInputFiles 허용). "
        + ("모두 넣은 뒤 보내기를 한 번만 누르고 보낸편지함에서 확인" + (f", 그 메일 화면을 {a.proof} 로 캡처" if a.proof else "") + "."
           if a.submit else "보내기는 누르지 말고 작성창만 채워 두고 보고."))
run(main, a, TASK)
