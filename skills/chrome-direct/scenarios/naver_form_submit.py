"""Naver Form (form.naver.com/response/...) fill & submit, page by page, no login.

answers.json: {"items": [
  {"q": "^1\\.", "choose": "유의사항을 확인"},          # checkbox/radio by option label (regex)
  {"q": "^2\\.", "choose": "^동의합니다"},
  {"q": "^3\\.", "text": "권리나루"},                    # first visible textarea/input in that question
  {"ph": "이름을 입력", "text": "{name}"},               # input by placeholder (respondent fields)
  {"ph": "연락처를 입력", "text": "{phone_digits}"}]}
`q` is matched against each question's title line (the line starting with 'N.'), `{placeholders}`
come from _common.personal_info() and are never printed.

Dry-run by default (fills every page, stops before 제출). --submit presses 제출 and waits for the
completion screen. --marker f: refuse if f exists (already sent), write it after a confirmed submit
— use one marker per entry when sending several responses to the same form.
--lock-held: the contest lock was taken by the caller; check submit evidence but do not mkdir.
--proof x.png: screenshot of the completion screen.
--add-response: the form remembers this browser ('이미 참여한 설문입니다') — press '설문 추가 참여' for the next entry.
"""
import json, re, sys, time
from datetime import datetime
from pathlib import Path

from _common import (Blocked, c, emit, expand, guard_and_lock, parser, personal_info, poll, run,
                     submitted_evidence, tab)
from _common import js as _js


def js(tid, body, timeout=20, tries=3):
    """JXA sometimes fails with -1728 (tab/window lookup) when many tabs are open — retry."""
    for k in range(tries):
        try:
            return _js(tid, body, timeout)
        except RuntimeError as e:
            if "-1728" not in str(e) or k == tries - 1:
                raise
            time.sleep(2)

ap = parser(__doc__.splitlines()[0], submit=True)
ap.add_argument("url")
ap.add_argument("answers")
ap.add_argument("--marker")
ap.add_argument("--lock-held", action="store_true")
ap.add_argument("--proof")
ap.add_argument("--add-response", action="store_true", help="'이미 참여한 설문'이면 '설문 추가 참여'로 새 응답 (여러 건 응모)")
args = ap.parse_args()

HELP = r"""
var __vis=e=>{const b=e.getBoundingClientRect();return b.width>0&&b.height>0};
var __press=e=>{e.scrollIntoView({block:'center'});const b=e.getBoundingClientRect();
 const o={bubbles:true,cancelable:true,view:window,clientX:b.left+b.width/2,clientY:b.top+b.height/2,button:0};
 for(const k of['pointerdown','mousedown','pointerup','mouseup','click'])e.dispatchEvent(new(k.startsWith('pointer')?PointerEvent:MouseEvent)(k,o))};
var __setv=(e,v)=>{e.focus();const p=e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
 Object.getOwnPropertyDescriptor(p,'value').set.call(e,v);e.dispatchEvent(new Event('input',{bubbles:true}));
 e.dispatchEvent(new Event('change',{bubbles:true}));e.dispatchEvent(new Event('keyup',{bubbles:true}));e.blur();return e.value===v};
var __items=()=>[...document.querySelectorAll('.nsv_survey_item')].filter(__vis);
var __title=it=>{const l=(it.innerText||'').split('\n').map(s=>s.trim()).find(s=>/^\d+\.\s/.test(s));return l||''};
"""

def step(msg):
    print(f"STEP {datetime.now():%H:%M:%S} {msg}", file=sys.stderr, flush=True)


DONE_RE = r"제출되었습니다|제출 완료|응답이 (제출|완료)|참여해 주셔서|참여해주셔서|감사합니다"


def fill_page(tid, items, info):
    """Fill what is on the current page in ONE js call (each call costs ~5s with many tabs open).
    Returns list of (key, status) for items present on this page."""
    spec = [{**it, "text": expand(it["text"], info)} if "text" in it else it for it in items]
    r = js(tid, HELP + f"""const spec={json.dumps(spec, ensure_ascii=False)};const res=[];
for(const it of spec){{const key=it.q||it.ph;let r;
 if('text' in it){{let e;
  if(it.q){{const q=__items().find(i=>new RegExp(it.q).test(__title(i)));
   e=q?[...q.querySelectorAll('textarea,input[type=text],input[type=tel],input:not([type])')].filter(__vis)[0]:null;}}
  else e=[...document.querySelectorAll('textarea,input')].filter(x=>__vis(x)&&(x.placeholder||'').includes(it.ph))[0];
  if(!e)continue; r=__setv(e,it.text)?'OK':'MISMATCH:'+e.value.length;}}
 else{{const q=__items().find(i=>new RegExp(it.q).test(__title(i)));if(!q)continue;
  const l=[...q.querySelectorAll('label')].find(l=>new RegExp(it.choose).test(l.innerText.trim()));
  if(!l)r='NOOPT';else{{const inp=document.getElementById(l.htmlFor)||l.querySelector('input');
   if(!(inp&&inp.checked))__press(l);r=(inp&&inp.checked)?'OK':'UNCHECKED';}}}}
 res.push([key,r]);}}
return res;""", 40)
    for key, st in r:
        if st != "OK":
            raise RuntimeError(f"{key}: {st}")
    return r


def page_no(tid):
    return js(tid, "const m=(document.body.innerText.match(/(\\d+)\\/(\\d+)/)||[]);return [m[1]||'',m[2]||'']")


def main():
    data = json.loads(Path(args.answers).read_text())
    items = data["items"]
    info = personal_info()
    if args.marker and Path(args.marker + ".pressed").exists() and not Path(args.marker).exists():
        raise Blocked(f"UNCONFIRMED earlier press {args.marker}.pressed — check before pressing again")
    if args.marker and Path(args.marker).exists():
        raise Blocked(f"ALREADY_SENT marker {args.marker}: {Path(args.marker).read_text()[:120]}")
    out = {"url": args.url, "pages": []}
    with tab(args.url, args) as tid:
        st = poll(tid, "return document.querySelectorAll('.nsv_survey_item').length>0?'form':(/이미 참여한 설문/.test(document.body.innerText)?'done':'')", 30)
        if st == "done":  # 이 기기(formDid)로 이미 낸 적 있음 → 여러 건 응모일 때만 '설문 추가 참여'
            if not args.add_response:
                raise Blocked("ALREADY_RESPONDED 이미 참여한 설문입니다 (여러 건이면 --add-response + 건마다 --marker)")
            step("이미 참여 → 설문 추가 참여")
            js(tid, HELP + "__press([...document.querySelectorAll('button')].filter(__vis).find(b=>b.innerText.trim()==='설문 추가 참여'));return 1")
            poll(tid, "return document.querySelectorAll('.nsv_survey_item').length>0", 30)
        txt = js(tid, "return document.body.innerText.slice(0,600)")
        if re.search(r"마감되었|마감된 설문|종료된 설문|종료되었|이미 참여|응답을 받지 않", txt):
            raise Blocked(f"FORM_CLOSED_OR_DONE {txt[:120]!r}")
        for _ in range(10):
            cur, total = page_no(tid)
            for _w in range(8):
                if cur:
                    break
                time.sleep(1.5); cur, total = page_no(tid)
            step(f"page {cur}/{total} fill")
            got = fill_page(tid, items, info)
            out["pages"].append({"page": f"{cur}/{total}", "filled": [k for k, _ in got]})
            nxt = js(tid, HELP + "const b=[...document.querySelectorAll('button')].filter(__vis).find(b=>b.innerText.trim()==='다음');return !!b")
            if nxt:
                js(tid, HELP + "__press([...document.querySelectorAll('button')].filter(__vis).find(b=>b.innerText.trim()==='다음'));return 1")
                after = cur
                for _w in range(12):  # 다음 쪽이 그려질 때까지(빈 값·같은 쪽이면 더 기다림)
                    time.sleep(1.5)
                    after, _t = page_no(tid)
                    if after and after != cur:
                        break
                if not after or after == cur:
                    err = js(tid, HELP + "return [...document.querySelectorAll('[class*=error],[class*=alert],[class*=warning]')].filter(__vis).map(e=>e.innerText.trim()).filter(Boolean).join(' | ').slice(0,300)")
                    raise RuntimeError(f"page {cur} did not advance: {err}")
                continue
            break
        sub = js(tid, HELP + "const b=[...document.querySelectorAll('button')].filter(__vis).find(b=>/^제출/.test(b.innerText.trim()));return b?b.innerText.trim():''")
        if not sub:
            raise RuntimeError("no 제출 button on last page")
        # values check on the last page (lengths only — never print personal values)
        out["last_page_check"] = js(tid, HELP + "return [...document.querySelectorAll('textarea,input[type=text],input[type=tel]')].filter(__vis).map(e=>e.value.length)")
        if not args.submit:
            emit(out, "DRY_RUN", f"filled {len(out['pages'])} pages, 제출 not pressed")
            return
        if args.lock_held:
            ev = submitted_evidence(args.contest_id) if args.contest_id else []
            if ev:
                raise Blocked("ALREADY_SUBMITTED " + " / ".join(ev))
        else:
            guard_and_lock(args.contest_id)
        step("PRESS 제출")
        if args.marker:  # 누르기 직전 흔적: 이 파일만 있고 marker가 없으면 '눌렀는지 모름' → 다시 누르지 말고 확인
            Path(args.marker + ".pressed").write_text(f"{datetime.now():%Y-%m-%d %H:%M:%S}\n")
        js(tid, HELP + "__press([...document.querySelectorAll('button')].filter(__vis).find(b=>/^제출/.test(b.innerText.trim())));return 1")
        step("pressed, waiting completion")
        try:
            done = poll(tid, f"const t=document.body.innerText;return /{DONE_RE}/.test(t)?t.slice(0,400):''", 25)
        except Exception as e:
            emit(out, "UNCONFIRMED", f"pressed 제출 but no completion text ({e}) — do NOT press again, check first")
            sys.exit(2)
        step("completion text seen")
        if args.marker:  # 완료 글을 본 즉시 남긴다(뒤 단계가 실패해도 다시 내지 않게)
            Path(args.marker).write_text(f"{datetime.now():%Y-%m-%d %H:%M:%S} SUBMITTED {args.url}\n{done[:200]}\n")
        out["done_text"] = done
        try:
            out["done_url"] = js(tid, "return location.href")
        except Exception as e:
            out["done_url"] = f"? ({str(e)[:80]})"
        if args.proof:
            try:
                c.shot(tid, args.proof)
                out["proof"] = args.proof
            except Exception as e:
                out["proof_err"] = str(e)[:200]
        emit(out, "SUBMITTED", out["done_url"])


run(main, args, f"Open {args.url} in Chrome profile {args.profile} (Naver Form, no login). Fill each page with the answers in "
    f"{args.answers} (personal fields: ask nothing, leave a note). {'Press 제출 once and capture the completion screen.' if getattr(args, 'submit', False) else 'Do NOT press 제출.'}")
