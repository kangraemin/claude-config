#!/usr/bin/env python3
"""[제출] 받은 메일 스레드에 '답장'으로 첨부 회신 (remin1994@gmail.com, 실제 Chrome Profile 1 웹). 기본 dry-run.
주최가 "본 메일에 회신하여 파일 첨부"를 요구할 때 쓴다(SMTP 앱 비밀번호 없을 때). 11/22 6G 본선 영상.

  gmail_reply.py --thread-query 'from:chanyu@ngma.re.kr subject:"예선 합격"' --expect-to chanyu@ngma.re.kr \
      --body-file body.txt --attach 강래민.mp4 --contest-id sixg-scenario-finals --submit

순서: 보낸편지함 중복 확인(in:sent to:<expect-to> filename:<첨부>) → 스레드 열기 → 마지막 메일 '답장' →
본문 넣기 → 첨부(DataTransfer) → 받는 사람이 expect-to 하나뿐인지·첨부 이름 확인 → 잠금(mkdir) → 보내기 →
보낸편지함에서 다시 확인. 검사 하나라도 어긋나면 보내지 않는다(작성 중 답장은 초안으로 남을 수 있음).
"""
import base64
import json
import mimetypes
import time
from pathlib import Path

from _common import ACCOUNT, Blocked, emit, guard_and_lock, js, mark_not_sent, parser, poll, run, tab
from _gmail import check_account, open_row, search, search_url
import chromectl as c

ap = parser(__doc__, submit=True)
ap.add_argument("--thread-query", required=True, help="답장할 스레드를 찾는 Gmail 검색어(결과 1번째를 연다)")
ap.add_argument("--expect-to", required=True, help="답장 받는 사람(이 주소 하나만 있어야 보냄)")
ap.add_argument("--body-file", required=True)
ap.add_argument("--attach", action="append", default=[])
ap.add_argument("--account", default=ACCOUNT)
ap.add_argument("--force-resend", action="store_true", help="보낸편지함에 같은 첨부가 있어도 보냄(사용자 지시 있을 때만)")
a = ap.parse_args()
BODY = Path(a.body_file).read_text().strip()
FILES = [Path(p).resolve() for p in a.attach]
SENTQ = f"in:sent to:{a.expect_to}" + "".join(f' filename:"{f.name}"' for f in FILES[:1])

# 이 스레드 화면에서 '보이는' 답장 작성창(contenteditable 본문)을 품은 가장 가까운 form/table
REPLY = r"""const eds = [...document.querySelectorAll('div[contenteditable=true][role=textbox], div[contenteditable=true][g_editable=true]')].filter(__vis);
const ed = eds[eds.length - 1];
let box = ed; for (let i = 0; box && i < 25; i++) { if (box.querySelector && box.querySelector('input[type=file]') && box.querySelector('div[role=button][data-tooltip]')) break; box = box.parentElement; }
"""


def attach(tid, files):
    js(tid, "window.__f=[]; return 1")
    for f in files:
        b = base64.b64encode(f.read_bytes()).decode()
        js(tid, "window.__b=''; return 1")
        for k in range(0, len(b), 300000):
            js(tid, f"window.__b += {json.dumps(b[k:k+300000])}; return 1", 60)
        mime = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
        js(tid, f"""const s=atob(window.__b),u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);
          const nm={json.dumps(f.name)};window.__f=window.__f.filter(x=>x.name!==nm);
          window.__f.push(new File([u],nm,{{type:{json.dumps(mime)}}}));window.__b='';return 1""", 120)
    n = js(tid, REPLY + """if (!box) return -2; const ins=[...box.querySelectorAll('input[type=file]')]; const i=ins.find(x=>x.multiple)||ins[0]; if(!i) return -1;
      const dt=new DataTransfer(); window.__f.forEach(f=>dt.items.add(f)); i.files=dt.files;
      i.dispatchEvent(new Event('change',{bubbles:true})); return i.files.length""")
    if n != len(files):
        raise RuntimeError(f"DataTransfer 파일 수 불일치: {n}/{len(files)}")
    return poll(tid, REPLY + f"return box && box.querySelectorAll('input[name=attach]').length >= {len(files)} && "
                     "![...box.querySelectorAll('[role=progressbar]')].some(__vis)", 300, 2)


def state(tid):
    """받는 사람(받는사람·참조·숨은참조 칩)·첨부 이름·본문 앞부분. 받는 사람 칸은 본문 TBODY 밖 조상에 있다(11/22)."""
    return js(tid, REPLY + r"""if (!box) return null;
      let top = ed; while (top && !(top.querySelector && top.querySelector('[name=to]'))) top = top.parentElement;
      const chips = n => top ? [...top.querySelectorAll('[name=' + n + '] [role=option][data-hovercard-id]')].map(e => e.getAttribute('data-hovercard-id')) : null;
      const atts = [...box.querySelectorAll('input[name=attach]')].map(e => ((e.parentElement || {}).innerText || '').trim());
      return {to: chips('to'), cc: chips('cc'), bcc: chips('bcc'), attachments: atts, body: (ed.innerText || '').slice(0, 300)};""")


def main():
    for f in FILES:
        if not f.exists():
            raise Blocked(f"NO_FILE {f}")
    size = sum(f.stat().st_size for f in FILES)
    plan = {"from": a.account, "expectTo": a.expect_to, "thread": a.thread_query, "bodyChars": len(BODY),
            "attachments": [f"{f.name} ({f.stat().st_size // 1024}KB)" for f in FILES], "totalMB": round(size / 1e6, 1)}
    if size > 24.5e6:
        raise Blocked(f"TOO_BIG 첨부 {plan['totalMB']}MB > 25MB")
    with tab(search_url(SENTQ, a.account), a) as tid:
        prev = search(tid, SENTQ, a.account, 5)["rows"]
        plan["alreadyInSent"] = [f"{r['date']} {r['subject']}" for r in prev]
        if prev and not a.force_resend:
            emit(plan, "ALREADY_SENT", "보낸편지함에 같은 첨부 — 안 보냄")
            raise Blocked("ALREADY_SENT")
        rows = search(tid, a.thread_query, a.account, 5)["rows"]
        if not rows:
            raise Blocked(f"NO_THREAD {a.thread_query}")
        th = open_row(tid, 1)
        plan["threadSubject"] = th["subject"]
        plan["threadFrom"] = [m["from"] for m in th["messages"]]
        if a.expect_to not in plan["threadFrom"]:
            raise Blocked(f"THREAD_MISMATCH 스레드 보낸 사람 {plan['threadFrom']} 에 {a.expect_to} 없음")
        if not a.submit:
            emit(plan, "DRY_RUN", "--submit 으로 발송")
            return
        # 마지막 메일의 '답장' (전체답장 아님)
        r = js(tid, r"""const bs = [...document.querySelectorAll('span[role=link], div[role=button]')].filter(e => __vis(e) &&
              /^(답장|Reply)$/.test((e.getAttribute('aria-label') || e.getAttribute('data-tooltip') || e.innerText || '').trim()));
            const b = bs[bs.length - 1]; if (!b) return 'NOTFOUND'; __press(b); return 'OK';""")
        if r != "OK":
            raise RuntimeError("답장 버튼 못 찾음")
        poll(tid, REPLY + "return !!(ed && box)", 30)
        # Gmail은 TrustedHTML이라 innerHTML·insertHTML이 안 먹는다(11/22) → 줄마다 div 노드로 넣는다
        js(tid, REPLY + f"""const lines = {json.dumps(BODY.split(chr(10)), ensure_ascii=False)}; while (ed.firstChild) ed.removeChild(ed.firstChild);
          lines.forEach(l => {{ const d = document.createElement('div'); if (l) d.textContent = l; else d.appendChild(document.createElement('br')); ed.appendChild(d); }});
          ed.dispatchEvent(new InputEvent('input', {{bubbles: true}})); return 1""")
        attach(tid, FILES)
        time.sleep(2)
        st = state(tid)
        plan["compose"] = st
        names = [f.name for f in FILES]
        bad = []
        if not st or st["to"] != [a.expect_to] or st["cc"] or st["bcc"]:
            bad.append(f"받는 사람 {st and (st['to'], st['cc'], st['bcc'])} != [{a.expect_to}]")
        if not st or len(st["attachments"]) != len(names) or not all(any(n in x for x in st["attachments"]) for n in names):
            bad.append(f"첨부 {st and st['attachments']} != {names}")
        if not st or BODY.split("\n")[0][:20] not in st["body"]:
            bad.append("본문 안 들어감")
        if bad:
            a.keep_tab = True
            emit(plan, "BLOCKED", "보내기 전 검사 실패(초안·탭 남김): " + " / ".join(bad))
            raise Blocked("PRECHECK " + " / ".join(bad))
        lock = guard_and_lock(a.contest_id)
        try:
            r = js(tid, REPLY + r"""const b = [...box.querySelectorAll('div[role=button]')].filter(e => __vis(e) &&
                /^(보내기|Send)/.test(e.getAttribute('data-tooltip') || e.getAttribute('aria-label') || e.innerText))[0];
              if (!b) return 'NOTFOUND'; __press(b); return 'OK';""")
            if r != "OK":
                raise RuntimeError("보내기 버튼 못 찾음")
        except Exception as e:
            mark_not_sent(lock, f"발송 전 실패: {e}")
            raise
        if lock:
            (lock / "SENT.txt").write_text(f"{time.strftime('%Y-%m-%d %H:%M:%S')} web-reply to={a.expect_to} thread={th['subject']} att={','.join(names)}\n")
        rows = []
        try:
            time.sleep(8)
            c.goto(tid, search_url(SENTQ, a.account))
            time.sleep(3)
            check_account(tid, a.account)
            for _ in range(12):
                rows = search(tid, SENTQ, a.account, 5)["rows"]
                if len(rows) > len(prev):
                    break
                time.sleep(5)
                c.run_js(tid, "location.reload()")
                time.sleep(4)
        except Exception as e:
            plan["verifyError"] = str(e)[:200]
        plan["sentNow"] = [f"{r['date']} {r['subject']} 첨부{r['attachments']}" for r in rows]
        if len(rows) <= len(prev):
            emit(plan, "UNCONFIRMED", "보내기 누름 — 보낸편지함 확인 못 함. 재발송 금지, 몇 분 뒤 gmail_search로 확인")
            raise Blocked("UNCONFIRMED")
        emit(plan, "SENT", a.contest_id or "")


TASK = (f"Gmail 웹({a.account}, 실제 Chrome Profile 1). 먼저 `{SENTQ}` 검색 — 있으면 보내지 말고 STATUS: NEEDS_OWNER ALREADY_SENT. "
        f"`{a.thread_query}` 첫 스레드를 열어 마지막 메일에 '답장'(전체답장 아님), 받는 사람 {a.expect_to} 하나만, 본문은 {Path(a.body_file).resolve()} 내용 그대로, "
        f"첨부 {', '.join(str(f) for f in FILES)} . "
        + ("확인 뒤 보내기 한 번만, 보낸편지함에서 확인." if a.submit else "보내지 말고 보고."))
run(main, a, TASK)
