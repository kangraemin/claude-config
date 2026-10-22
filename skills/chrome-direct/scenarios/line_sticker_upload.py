#!/usr/bin/env python3
"""[제출] LINE Creators Market에 정지 스티커 세트(24개+main+tab)를 등록하고 심사 요청.

  line_sticker_upload.py <png_dir> --en-title T --en-desc D [--ja-title T --ja-desc D] [--zh-title T --zh-desc D] [--areas JP,TW,HK]
                         [--style 6] [--character 14] [--creator "Raemin Kang"] [--submit]

- png_dir: 01.png..24.png(370×320) + main.png(240×240) + tab.png(96×74). drafts/set-kb/line 처럼.
- 새 항목 폼 → 제목·설명(영/일)·저작권·AI 사용=예·카테고리 → 저장 → 수정 화면에서 판매 지역(선택 국가만) → 이미지 ZIP 업로드.
- --submit 이 있을 때만 「Request」(심사 요청, 동의 체크 → OK)를 누른다.
- 멱등: Manage Items 목록에 같은 영어 제목이 있으면 새로 만들지 않고 그 항목의 남은 단계만 한다.
- 사전 조건: Creators 가입 완료. 로그아웃돼 있으면 LINE_EMAIL/LINE_PASSWORD 로 로그인하고,
  화면에 뜬 인증번호(PIN)를 텔레그램으로 보낸 뒤 사용자가 폰 LINE 앱에 넣을 때까지 3분 기다린다.
- 왜 화면 조작인가: LINE Creators Market은 등록 API가 없다. 폼은 Vue라 값은 setter+input 이벤트로 넣는다.
- 함정:
  - 언어 추가는 select 값만 바꾸면 안 되고 [data-test=btn-add-language] 를 눌러야 ja 칸이 생긴다.
  - Creator's Name 은 input이 아니라 [data-test=btn-edit-author] 창(name 입력 → REGISTER).
  - 새 항목 폼에서 area_group=customized 를 골라도 '모든 지역'으로 저장됐다 → 저장 후 /update 에서 지역을 고친다.
    customized 를 누르면 197개국이 전부 체크된 채 나온다. 대륙 체크(name 없는 checkbox)를 꺼서 0으로 만든 뒤 국가만 켠다.
  - 저장·요청 버튼은 확인창(OK)이 뜬다. setTimeout 으로 누르고 창의 OK를 다시 누른다.
  - 「Requests Remaining Today: 0/30」은 '0개 사용'이다(남은 수 아님).
  - 정산 계좌 미등록 경고가 떠도 심사 요청은 된다.
  - 로그인 버튼(input[name=tid]/tpasswd 옆 「로그인」)은 값을 넣어도 disabled 로 남는다 → disabled=false 후 click.
"""
import argparse
import base64
import io
import json
import re
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/.config/claude-accounts/personal/skills/chrome-direct"))
import chromectl as c  # noqa: E402

BASE = "https://creator.line.me/my/"
for _l in Path("~/.claude/.env").expanduser().read_text().splitlines():  # 비밀값은 env 이름으로만 쓴다
    if "=" in _l and not _l.lstrip().startswith("#"):
        _k, _v = _l.split("=", 1)
        os.environ.setdefault(_k.strip().removeprefix("export "), _v.strip().strip('"').strip("'"))


def R(f, *a, **k):
    """chromectl 이 간헐적으로 RuntimeError(-600/-609)를 내서 재시도한다.
    부하가 높으면(load 100+) 페이지 로딩 중 execute가 20초를 넘긴다 → 대기 90초, 타임아웃도 재시도(2026-10-22)."""
    k.setdefault("timeout", 90)
    for _ in range(10):
        try:
            return f(*a, **k)
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            last = e
            time.sleep(1.5)
    raise last


def js(t, code):
    return R(c.run_js, t, code)


def jj(t, code):
    return R(c.js_json, t, code)


def click_ok(t, text):
    """text 가 보이는 확인창의 OK 를 누른다. 숨은 OK(크기 0)가 같은 상자에 여럿 있어 화면 맨 위에 실제로 보이는 것만 누른다.
    확인창이 늦게 뜰 때가 있어 10초까지 다시 본다. 뒤에 있는 탭에선 확인창이 안 그려져 OK 가 안 먹으므로 먼저 앞으로 띄운다."""
    c.shot(t, "/tmp/line_upload_front.png")
    for _ in range(10):
        if _click_ok(t, text) == 1:
            return 1
        time.sleep(1)
    return 0


def _click_ok(t, text):
    return jj(t, "return " + """(()=>{if(![...document.querySelectorAll('*')].some(e=>e.children.length==0&&e.textContent.includes(%s)&&e.getClientRects().length))return 0;
      const b=[...document.querySelectorAll('button')].find(b=>{if(b.innerText.trim()!='OK')return false;const q=b.getBoundingClientRect();if(!q.width)return false;
        const top=document.elementFromPoint(q.x+q.width/2,q.y+q.height/2);return top===b||b.contains(top)});
      if(!b)return 0;setTimeout(()=>b.click(),10);return 1})()""" % json.dumps(text))


def set_values(t, vals):
    return js(t, """(()=>{const V=%s;for(const[k,v] of Object.entries(V)){const e=document.querySelector(`[name="${k}"]`);if(!e)return 'miss '+k;
      const set=Object.getOwnPropertyDescriptor(e.tagName=='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value').set;set.call(e,v);
      e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));}return 'ok'})()""" % json.dumps(vals, ensure_ascii=False))


def select(t, test, value):
    js(t, """(()=>{const s=document.querySelector('[data-test=%s]');s.value=%s;s.dispatchEvent(new Event('change',{bubbles:true}));return 1})()""" % (test, json.dumps(value)))


def close_notices(t):
    # 공지 팝업은 position:fixed 라 offsetParent 가 null — getClientRects 로 판정. 안 닫으면 저장이 조용히 무시된다
    js(t, "(()=>{[...document.querySelectorAll('button.FnCloseDialogBtn,button')].filter(b=>b.getClientRects().length&&(b.classList.contains('FnCloseDialogBtn')||b.innerText.trim()=='Close')).forEach(b=>b.click());return 1})()")


def my_root(t, wait=30):
    """/my/ → /my/<root>/ 리다이렉트를 기다린다(부하가 높으면 5초 넘게 걸린다, 2026-10-22)."""
    end = time.time() + wait
    while True:
        try:
            href = js(t, "location.href")
        except Exception:  # 페이지 로딩 중엔 execute가 20초 넘게 막힌다
            href = ""
        root = href.split("/my/")[1].split("/")[0] if "/my/" in href else ""
        if root or time.time() > end or (href and jj(t, "return !!document.querySelector('input[name=tid]')")):
            return root or None
        time.sleep(2)


def login(t):
    """access.line.me 로그인. PIN 확인 단계는 사람(폰 앱) 몫이라 텔레그램으로 번호만 보낸다."""
    import re
    import subprocess
    js(t, """(()=>{const f=(n,v)=>{const e=document.querySelector(`input[name=${n}]`);const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
      set.call(e,v);['input','change','keyup','blur'].forEach(k=>e.dispatchEvent(new Event(k,{bubbles:true})))};f('tid',%s);f('tpasswd',%s);
      const b=[...document.querySelectorAll('button[type=submit]')].find(b=>b.innerText.trim()=='로그인'||/log ?in/i.test(b.innerText));
      b.disabled=false;setTimeout(()=>b.click(),10);return 1})()""" % (json.dumps(os.environ["LINE_EMAIL"]), json.dumps(os.environ["LINE_PASSWORD"])))
    time.sleep(8)
    sent = False
    for _ in range(36):
        if my_root(t):
            return True
        body = js(t, "document.body.innerText")
        m = re.search(r"(?<!\d)(\d{4,6})(?!\d)", body)
        if m and not sent:
            subprocess.run(["curl", "-s", "-d", f"chat_id={os.environ.get('CONTEST_TG_CHAT_ID', '')}", "--data-urlencode",
                            f"text=[LINE 로그인] 폰 LINE 앱에 인증번호 {m.group(1)} 입력해주세요(3분)",
                            f"https://api.telegram.org/bot{os.environ.get('CONTEST_TG_TOKEN', '')}/sendMessage"], capture_output=True)
            print("PIN sent to telegram")
            sent = True
        js(t, "(()=>{const b=[...document.querySelectorAll('button')].find(b=>/^(허용|Allow)$/.test(b.innerText.trim()));if(b)b.click();return 1})()")
        time.sleep(5)
    return bool(my_root(t))


def find_item(t, root, title):
    """Manage Items 목록에서 영어 제목이 같은 스티커 id."""
    c.goto(t, f"{BASE}{root}/sticker/")
    time.sleep(5)
    # 카드 제목이 여러 span 으로 쪼개져 줄바꿈이 끼므로 공백을 빼고 비교한다
    return jj(t, """const k=%s.replace(/\\s/g,'');const a=[...document.querySelectorAll('[data-test=product-info-card]')]
      .find(a=>a.innerText.replace(/\\s/g,'').includes(k));return a?a.dataset.productId:null""" % json.dumps(title))


def create(t, root, a):
    c.goto(t, f"{BASE}{root}/sticker/create")
    time.sleep(5)
    close_notices(t)
    vals = {"meta[en][title]": a.en_title, "meta[en][description]": a.en_desc, "copyright": a.creator}
    for lang, ti, de in (("ja", a.ja_title, a.ja_desc), ("zh-Hant", a.zh_title, a.zh_desc)):
        if not ti:
            continue
        # 칸이 늦게 생긴다(값을 먼저 넣으면 'miss'·'2 or more characters'). 칸이 보일 때까지 기다린다
        for _ in range(10):
            if jj(t, "return !!document.querySelector('[name=\"meta[%s][title]\"]')" % lang):
                break
            select(t, "select-language", lang)
            js(t, "setTimeout(()=>document.querySelector('[data-test=btn-add-language]').click(),300);1")
            time.sleep(2)
        vals.update({f"meta[{lang}][title]": ti, f"meta[{lang}][description]": de})
    print("fill", set_values(t, vals))
    jj(t, """for(const[n,v] of [['sticker_type','static'],['is_ai_generated',%s]])document.querySelector(`input[name="${n}"][value="${v}"]`).click();return 1"""
       % json.dumps("true" if a.ai else "false"))
    select(t, "select-style-category", a.style)
    select(t, "select-character-category", a.character)
    js(t, "setTimeout(()=>document.querySelector('[data-test=btn-edit-author]').click(),10);1")
    time.sleep(2)
    js(t, """(()=>{const e=document.querySelector('input[name=name]');if(!e)return 0;const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
      set.call(e,%s);e.dispatchEvent(new Event('input',{bubbles:true}));
      const b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.innerText.trim()=='REGISTER');setTimeout(()=>b.click(),10);return 1})()""" % json.dumps(a.creator))
    time.sleep(2)
    close_notices(t)
    js(t, "setTimeout(()=>document.querySelector('[data-test=btn-save]').click(),300);1")
    time.sleep(3)
    click_ok(t, "Save this form")
    time.sleep(6)
    href = js(t, "location.href")
    # 저장돼도 주소가 /create 로 남을 때가 있다 — 화면의 Sticker ID 로 판정
    sid = jj(t, "const m=document.body.innerText.match(/Sticker ID\\s*(\\d{6,})/);return m?m[1]:null")
    if sid:
        return sid
    if "/create" in href:
        err = jj(t, "return [...document.querySelectorAll('[class*=rror]')].filter(e=>e.offsetParent&&e.innerText.trim()).map(e=>e.innerText.trim())")
        raise SystemExit(f"RESULT: BLOCKED 저장 실패 {err}")
    return href.rstrip("/").split("/")[-1]


def fix_areas(t, root, sid, areas):
    c.goto(t, f"{BASE}{root}/sticker/{sid}/update")
    time.sleep(5)
    close_notices(t)
    js(t, "document.querySelector('[data-test=customized-area-group] label').click();1")
    time.sleep(1.5)
    js(t, "(()=>{[...document.querySelectorAll('input[type=checkbox]:not([name])')].filter(e=>e.offsetParent&&e.checked).forEach(e=>e.click());return 1})()")
    time.sleep(1)
    js(t, """(()=>{const keep=%s;document.querySelectorAll('input[name="areas[]"]').forEach(e=>{if(e.checked!==keep.includes(e.value))e.click()});return 1})()""" % json.dumps(areas))
    time.sleep(1)
    js(t, "document.querySelector('input[name=is_auto_release][value=true]').click();1")  # 심사 통과 즉시 판매(1탄과 같게)
    got = jj(t, """return [...document.querySelectorAll('input[name="areas[]"]:checked')].map(e=>e.value)""")
    if sorted(got) != sorted(areas):
        raise SystemExit(f"RESULT: BLOCKED 지역 선택 불일치 {got}")
    js(t, "setTimeout(()=>document.querySelector('[data-test=btn-save]').click(),300);1")
    time.sleep(3)
    ok = click_ok(t, "Save this form")
    for _ in range(10):  # 저장 후 상세 화면으로 넘어가는 데 6초 넘게 걸릴 때가 있다
        time.sleep(2)
        if not js(t, "location.href").endswith("/update"):
            return
    raise SystemExit(f"RESULT: BLOCKED 지역 저장 안 됨(수정 화면에 머묾, OK={ok})")


def upload(t, root, sid, files):
    c.goto(t, f"{BASE}{root}/sticker/{sid}/image")
    time.sleep(5)
    c.shot(t, "/tmp/line_upload_front.png")  # 뒤 탭에선 개수 칸·확인창이 안 그려진다
    close_notices(t)
    # 개수 칸은 한 번도 심사 요청 안 한 항목에만 있다. 8개로 요청되면 고칠 수 없어 항목을 지우고 새로 만들어야 한다
    n = jj(t, """const s=document.querySelector('[data-test=select-image-amount]');if(!s)return null;const o=[...s.options].find(o=>o.text.trim()=='24');
      if(s.value==o.value)return 'same';s.value=o.value;s.dispatchEvent(new Event('change',{bubbles:true}));return 'set'""")
    if n is None:
        raise SystemExit(f"RESULT: BLOCKED 개수 선택 칸 없음(이미 심사 요청된 적 있는 항목) {sid}")
    if n == "set":
        time.sleep(2)
        click_ok(t, "number of stickers")
        time.sleep(4)
    got = jj(t, "const s=document.querySelector('[data-test=select-image-amount]');return s?s.selectedOptions[0].text.trim():null")
    if got != "24":
        raise SystemExit(f"RESULT: BLOCKED 개수 24 설정 실패({got}) {sid}")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for p in files:
            z.write(p, p.name)
    b = base64.b64encode(buf.getvalue()).decode()
    js(t, "window.__b='';1")
    for i in range(0, len(b), 400000):
        js(t, f"window.__b+={json.dumps(b[i:i + 400000])};1")
    js(t, """(()=>{const s=atob(window.__b),u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);
      const e=document.querySelector('input[name=file]'),dt=new DataTransfer();dt.items.add(new File([u],'stickers.zip',{type:'application/zip'}));
      e.files=dt.files;e.dispatchEvent(new Event('change',{bubbles:true}));return 1})()""")
    time.sleep(25)
    return jj(t, "return document.querySelectorAll('[data-test=no-product-image]').length")


def status(t, root, sid):
    c.goto(t, f"{BASE}{root}/sticker/{sid}")
    for _ in range(10):  # 늦게 그려지면 빈 상태를 '이미 끝남'으로 오판한다
        time.sleep(3)
        body = js(t, "document.body.innerText")
        i = body.find("Status")
        st = [x for x in body[i:i + 80].split("\n")[1:4] if x.strip()][:2] if i >= 0 else []
        if st:
            return st, body
    return st, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png_dir")
    ap.add_argument("--en-title", required=True)
    ap.add_argument("--en-desc", required=True)
    ap.add_argument("--ja-title")
    ap.add_argument("--ja-desc")
    ap.add_argument("--zh-title", help="번체(zh-Hant) — TW·HK 검색용")
    ap.add_argument("--zh-desc")
    ap.add_argument("--areas", default="JP,TW,HK")
    ap.add_argument("--style", default="1", help="1 Cute, 6 Humorous, 22 Greetings, 23 Polite Language")
    ap.add_argument("--character", default="16", help="14 Birds, 16 Other, 10 Cats ...")
    ap.add_argument("--creator", default="Raemin Kang")
    ap.add_argument("--no-ai", dest="ai", action="store_false")
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    D = Path(a.png_dir).expanduser()
    files = [D / f"{i:02d}.png" for i in range(1, 25)] + [D / "main.png", D / "tab.png"]
    miss = [p.name for p in files if not p.exists()]
    if miss:
        print("RESULT: BLOCKED 파일 없음", miss)
        return
    t = c.new_tab("https://creator.line.me/my/", profile="Profile 1")
    try:
        time.sleep(5)
        root = my_root(t)
        if not root and jj(t, "return !!document.querySelector('input[name=tid]')"):
            login(t)
            c.goto(t, "https://creator.line.me/my/")
            time.sleep(5)
            root = my_root(t)
        if not root:
            print("RESULT: BLOCKED LINE 로그아웃 — creator.line.me 로그인 필요")
            return
        sid = find_item(t, root, a.en_title)
        if sid:
            st, _ = status(t, root, sid)
            print("existing", sid, st)
            if "Editing" not in " ".join(st):
                print("RESULT: ALREADY", sid, " ".join(st))
                return
        else:
            sid = create(t, root, a)
            print("created", sid)
        fix_areas(t, root, sid, a.areas.split(","))
        empty = upload(t, root, sid, files)
        st, body = status(t, root, sid)
        print("empty slots", empty, "status", st)
        if "required images have not been uploaded" in body:
            print("RESULT: BLOCKED 이미지 업로드 미완료", sid)
            return
        m = re.search(r"No\. of Stickers per Set\s*(\d+)", body)
        if not m or m.group(1) != "24":
            print("RESULT: BLOCKED 세트 개수가 24가 아님", m and m.group(1), sid)
            return
        if not a.submit:
            print("RESULT: FILLED", sid, "(--submit 없음, Request 안 누름)")
            return
        js(t, """(()=>{const a=[...document.querySelectorAll('a')].find(b=>b.innerText.trim()=='Request');
          setTimeout(()=>a.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true})),10);return 1})()""")
        time.sleep(5)
        js(t, """(()=>{const cb=[...document.querySelectorAll('input[type=checkbox]')].find(e=>(e.closest('label')||e.parentElement).innerText.trim()=='I Agree');
          if(!cb.checked)cb.click();let d=cb;while(d.parentElement&&!d.querySelector('button'))d=d.parentElement;
          const b=[...d.querySelectorAll('button')].find(b=>b.innerText.trim()=='OK');setTimeout(()=>b.click(),10);return 1})()""")
        time.sleep(6)
        st, body = status(t, root, sid)
        print("RESULT:", "SUBMITTED " + sid if "Waiting for Review" in " ".join(st) else f"UNKNOWN {sid} {st}")
    finally:
        if not a.keep:
            c.close_tab(t)


if __name__ == "__main__":
    main()
