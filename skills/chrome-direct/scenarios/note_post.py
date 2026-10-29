#!/usr/bin/env python3
"""[note.com] 먹맵 계정 가입(이메일) (멱등). Profile 7 "먹맵" 창. 기본 dry-run, --submit 일 때만 제출.

  note_post.py --signup [--submit]   # note.com/signup/form: 이메일+비번 → '下記に同意して登録する' 버튼
- ID/PW: ~/.claude/sns.env MUK_NOTE_ID(이메일)/_PW/_PROFILE. 값 출력 금지. 있으면 RESULT: EXISTS.
- 2026-10-30 확인: 가입 제출 시 "reCAPTCHAの認証を行い" 체크박스 요구 → BLOCKED(사람 손).
tmux -L gh 안에서 실행. 마지막 줄 RESULT:.
"""
import time
from _common import emit, js, parser, run, tab
from _muk import env_get, env_set, fill_js, newpw

ap = parser(__doc__)
ap.set_defaults(profile="Profile 7", no_fallback=True)
ap.add_argument("--signup", action="store_true")
ap.add_argument("--submit", action="store_true")
ap.add_argument("--email", default="remin1994+mukmap@gmail.com")
a = ap.parse_args()
a.no_fallback = True


def signup():
    if env_get("MUK_NOTE_ID"):
        emit({}, "EXISTS", "이미 가입됨"); return
    pw = newpw()
    with tab("https://note.com/signup/form", a) as tid:
        time.sleep(3)
        js(tid, fill_js("input[type=email]", a.email)); js(tid, fill_js("input[type=password]", pw))
        if not a.submit:
            emit({}, "OK", "dry-run 폼 채우기까지"); return
        js(tid, "const b=[...document.querySelectorAll('button')].find(b=>/同意して登録/.test(b.innerText)); b.click(); return 1")
        time.sleep(6)
        st = js(tid, "return {u:location.href,t:document.body.innerText.slice(0,300)}")
        ok = "reCAPTCHA" not in st["t"] and "signup/form" not in st["u"]
        if ok:
            env_set("MUK_NOTE_ID", a.email); env_set("MUK_NOTE_PW", pw); env_set("MUK_NOTE_PROFILE", "Profile 7")
        emit(st, "SUBMITTED" if ok else "BLOCKED", "reCAPTCHA v2 체크박스 필요(2026-10-30) — 사람 손" if not ok else "확인 메일 → gmail_code.py 로 링크")

run(lambda *_: signup(), a, "note")
