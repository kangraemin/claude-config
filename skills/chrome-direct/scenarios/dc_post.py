#!/usr/bin/env python3
"""[디시인사이드] 마이너 갤러리에 유동(비로그인)으로 글을 쓴다. 기본 dry-run, --submit일 때만 등록.

  dc_post.py --gall mukbang --title "..." --body-file body.txt [--profile "Profile 7"]            # dry-run: 중복 확인 + 폼 채우기까지
  dc_post.py ... --submit                      # '등록' 클릭. 보안문자가 뜨면 화면을 --shot png 로 저장하고 BLOCKED(재시도 없음, 텔레그램 안 보냄)
  dc_post.py ... --submit --captcha 'abc12'    # 보안문자 입력칸에 값을 넣고 등록(한 번만)

- 비밀번호는 ~/.claude/sns.env 의 MUK_DC_PW (--pw-env 로 바꿀 수 있음). 출력하지 않는다.
- 닉네임은 폼 기본값(유동 기본 닉)을 그대로 쓴다. --nick 으로 바꿀 수 있다.
- 멱등: 같은 제목이 갤러리 목록 1~2쪽에 있거나 ~/.claude/skills/chrome-direct/scenarios/.dc_posted.json 에 있으면 올리지 않는다(RESULT: DUPLICATE).
- 에디터는 Summernote(.note-editable) → innerHTML 로 줄마다 <p> 를 넣고 input 이벤트를 쏜다.
Exit 0 = OK/POSTED, 1 = 실패, 2 = BLOCKED(보안문자·중복·제한). 마지막 줄 RESULT:.
실제 chromectl 은 tmux -L gh 안에서 돌려야 Apple 이벤트가 막히지 않는다.
"""
import html, json, re, subprocess, time, urllib.request
from pathlib import Path

from _common import Blocked, emit, js, parser, poll, run, tab
import chromectl as c

ap = parser(__doc__)
ap.set_defaults(profile="Profile 7", no_fallback=True)
ap.add_argument("--gall", default="mukbang")
ap.add_argument("--title", required=True)
ap.add_argument("--body-file", required=True)
ap.add_argument("--nick")
ap.add_argument("--pw-env", default="MUK_DC_PW")
ap.add_argument("--captcha")
ap.add_argument("--submit", action="store_true")
ap.add_argument("--shot", default="/tmp/dc_post_cap.png")
a = ap.parse_args()
a.no_fallback = True  # 게시물 중복 위험 → Codex로 넘기지 않는다
STATE = Path(__file__).with_name(".dc_posted.json")
LIST = f"https://gall.dcinside.com/mgallery/board/lists/?id={a.gall}"


def secret(name):
    import os
    if os.environ.get(name):
        return os.environ[name]
    for f in (Path.home() / ".claude/sns.env", Path.home() / ".claude/.env"):
        if f.exists():
            for line in f.read_text().splitlines():
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(f"env {name} not found")


def norm(s):
    return re.sub(r"\s+", "", html.unescape(s))


def dup_in_list():
    for page in (1, 2):
        req = urllib.request.Request(f"{LIST}&page={page}", headers={"User-Agent": "Mozilla/5.0"})
        h = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
        for m in re.finditer(r'class="gall_tit[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', h, flags=re.S):
            if norm(re.sub("<[^>]+>", "", m.group(2))) == norm(a.title):
                return "https://gall.dcinside.com" + html.unescape(m.group(1))
    return None


def main():
    body = Path(a.body_file).expanduser().read_text().strip()
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    key = f"{a.gall}:{norm(a.title)}"
    if key in st:
        emit({"url": st[key]}, "DUPLICATE", "이미 올림(.dc_posted.json)")
        raise SystemExit(2)
    u = dup_in_list()
    if u:
        emit({"url": u}, "DUPLICATE", "같은 제목이 갤에 이미 있음")
        raise SystemExit(2)
    pw = secret(a.pw_env)
    out = {"gall": a.gall, "title": a.title}
    with tab(f"https://gall.dcinside.com/mgallery/board/write/?id={a.gall}", a) as tid:
        poll(tid, "return document.querySelector('.note-editable') && document.querySelector('#subject') ? 1 : null", 30)
        if a.nick:
            c.fill(tid, "#gall_nick_name", a.nick)
        c.fill(tid, "#password", pw)
        c.fill(tid, "#subject", a.title)
        paras = "".join("<p>" + (html.escape(l) if l.strip() else "<br>") + "</p>" for l in body.split("\n"))
        js(tid, f"""const e = document.querySelector('.note-editable'); e.focus(); e.innerHTML = {json.dumps(paras)};
          e.dispatchEvent(new Event('input', {{bubbles: true}})); return 1;""")
        time.sleep(1)
        chk = js(tid, "return {nick: document.querySelector('#gall_nick_name').value, subj: document.querySelector('#subject').value, len: document.querySelector('.note-editable').innerText.length, pw: document.querySelector('#password').value.length > 0}")
        out["form"] = chk
        if not chk or chk["subj"] != a.title or chk["len"] < 50 or not chk["pw"]:
            raise RuntimeError(f"폼 입력 확인 실패 {chk}")
        if not a.submit:
            emit(out, "OK", "dry-run 폼 채우기까지 (등록 안 함)")
            return
        if a.captcha:
            r = js(tid, f"""const i = [...document.querySelectorAll('input')].find(i => i.offsetParent && /user_code|captcha|code/i.test(i.name + i.id + i.className) && i.type === 'text');
              if (!i) return false; i.value = {json.dumps(a.captcha)}; i.dispatchEvent(new Event('input', {{bubbles: true}})); return true;""")
            if not r:
                raise Blocked("보안문자 입력칸을 못 찾음")
        js(tid, "window.alert = m => { window.__dcMsg = 'alert:' + m; }; window.confirm = m => { window.__dcMsg = 'confirm:' + m; return true; }; return 1")
        c.press(tid, sel="button.btn_svc.write")
        end = time.time() + 20
        while time.time() < end:
            time.sleep(1.5)
            url = c.js_json(tid, "return location.href") or ""
            posted = url if "/board/view" in url else (dup_in_list() if "/board/write" not in url else None)
            if posted:
                url = posted
                st[key] = url
                STATE.write_text(json.dumps(st, ensure_ascii=False))
                out["url"] = url
                emit(out, "POSTED", url)
                return
            cap = js(tid, """const w = document.querySelector('#captcha_wrapper, .captcha_wrapper, [id*=kcaptcha], img[src*=captcha], img[src*=kcap]');
              return {msg: window.__dcMsg || '', cap: !!(w && w.offsetParent && (w.querySelector('img') || w.tagName === 'IMG'))}""") or {}
            if cap.get("cap") or "보안" in cap.get("msg", "") or "자동" in cap.get("msg", ""):
                c.shot(tid, a.shot)  # 호출한 Claude가 이 png 를 Read 로 보고 판독 → --captcha 로 한 번만 재호출 (텔레그램·사용자에게 보내지 않는다)
                out["shot"] = a.shot
                out["msg"] = cap.get("msg")
                emit(out, "BLOCKED", "CAPTCHA — shot png 를 읽고 --captcha 로 한 번만 다시 시도")
                raise SystemExit(2)
            if cap.get("msg"):
                raise Blocked("DIALOG " + cap["msg"][:150])
        raise Blocked("등록 후 글 화면으로 안 넘어감")


run(main, a, "디시 글쓰기")
