#!/usr/bin/env python3
"""[지식iN] 네이버 지식iN 질문 하나에 답변을 붙여 넣고(옵션) 등록한다. 먼저 naver_login.py로 로그인 확인.

  kin_answer.py --url <질문 URL> --text-file a.txt            # dry-run: 상태 확인 + 입력창에 붙여넣기까지
  kin_answer.py --url <질문 URL> --text-file a.txt --submit   # '등록'까지 누르고 내 답변이 보이는지 확인
  kin_answer.py --url <질문 URL> --check                      # 상태만(마감·채택·내 답변 있음)
  --shot evidence.png                                          # 등록 후 화면 캡처

- SmartEditor ONE은 JS 값 넣기·가짜 paste 이벤트를 무시한다 → 실제 클릭(cliclick) + pbcopy + ⌘V.
  (가짜 paste 이벤트는 버퍼에 남았다가 다음 진짜 붙여넣기 때 같이 들어가니 쓰지 않는다.)
- alert/confirm은 막아서 문구를 기록한다(AppleScript가 대화상자에 걸려 멈추지 않게). confirm은 '확인'.
- 캡차·제한·경고 문구가 보이면 BLOCKED(exit 2) — 사람이 볼 때까지 더 올리지 않는다.
Exit 0 = OK/POSTED, 1 = 실패, 2 = BLOCKED(로그아웃·마감·채택·이미 답함·제한).
"""
import subprocess, time
from pathlib import Path

from _common import Blocked, emit, js, parser, poll, run, tab
import chromectl as c

ap = parser(__doc__)
ap.add_argument("--url", required=True)
ap.add_argument("--text-file")
ap.add_argument("--submit", action="store_true")
ap.add_argument("--check", action="store_true")
ap.add_argument("--shot")
a = ap.parse_args()
a.no_fallback = True  # 답변 등록은 Codex로 넘기지 않는다(중복 등록 위험)

STATE = r"""if (document.readyState !== 'complete') return null;
  const t = document.body.innerText;
  const btn = [...document.querySelectorAll('._answerWriteButton')].some(__vis);
  const mine = [...document.querySelectorAll('.answer-content__item, .answerArea, [class*=answer]')]
    .some(e => __vis(e) && [...e.querySelectorAll('button,a')].some(b => __vis(b) && /^(수정|삭제)$/.test((b.innerText || '').trim())));
  return {login: t.includes('내정보 보기'), btn, mine,
    adopted: /질문자\s*채택|질문자가 채택/.test(t), closed: /마감된 질문|답변이 마감|답변 마감/.test(t),
    warn: (t.match(/자동입력 ?방지|보안문자|일시적으로 제한|답변 등록이 제한|이용이 제한/) || [''])[0],
    answers: (t.match(/(\d+)개 답변/) || [0, 0])[1] * 1, title: document.title};"""
GUARD = r"""if (!window.__kinGuard) { window.__kinGuard = 1; window.__kinMsgs = [];
  window.alert = m => { window.__kinMsgs.push('alert:' + m); };
  window.confirm = m => { window.__kinMsgs.push('confirm:' + m); return true; }; } return 1;"""
EDITOR_TEXT = "const e = document.querySelector('.se-content'); return e ? e.innerText : '';"


def key(*k):
    subprocess.run(["cliclick", *k], check=True, capture_output=True)


def main():
    out = {"url": a.url}
    with tab(a.url, a) as tid:
        st = poll(tid, STATE, 30)
        out["state"] = st
        if not st["login"]:
            raise Blocked("LOGGED_OUT naver_login.py --qr 먼저")
        if st["warn"]:
            raise Blocked(f"WARN {st['warn']}")
        if st["mine"]:
            raise Blocked("ALREADY_ANSWERED 내 답변이 이미 있음")
        if st["adopted"] or st["closed"]:
            raise Blocked(f"CLOSED adopted={st['adopted']} closed={st['closed']}")
        if not st["btn"]:
            raise Blocked("NO_ANSWER_BUTTON 이미 내가 답했거나(질문당 1개) 답변 불가")
        if a.check:
            emit(out, "OK", "답변 가능")
            return
        text = Path(a.text_file).read_text().strip()
        c.press(tid, sel="._answerWriteButton")
        poll(tid, "return [...document.querySelectorAll('.se-content .se-text-paragraph')].some(__vis)", 15)
        for _ in range(3):  # 다른 앱·창이 앞으로 오면 ⌘V가 엉뚱한 곳에 들어간다 → 포커스 확인 후에만 붙여넣기
            c.rclick(tid, sel=".se-content .se-text-paragraph")
            time.sleep(0.8)
            front = c.osa('tell application "System Events" to get name of first process whose frontmost is true')
            if front == "Google Chrome" and js(tid, "return document.hasFocus() && /IFRAME|DIV/.test(document.activeElement.tagName)"):
                break
        else:
            raise RuntimeError(f"editor focus failed (frontmost={front})")
        key("kd:cmd", "t:a", "ku:cmd", "kp:delete")
        time.sleep(0.5)
        subprocess.run(["pbcopy"], input=text.encode(), check=True)
        key("kd:cmd", "t:v", "ku:cmd")
        time.sleep(2)
        got = js(tid, EDITOR_TEXT)
        norm = lambda s: "".join(s.split())  # noqa: E731
        if norm(got) != norm(text):
            raise RuntimeError(f"editor mismatch: {len(norm(got))} vs {len(norm(text))} chars: {got[:80]!r}")
        out["pasted"] = len(text)
        if not a.submit:
            emit(out, "OK", "dry-run 붙여넣기까지 (등록 안 함)")
            return
        js(tid, GUARD)
        c.press(tid, sel="._answerRegisterButton")
        time.sleep(4)
        msgs = js(tid, "return window.__kinMsgs || []") or []
        out["dialogs"] = msgs
        bad = [m for m in msgs if not m.startswith("confirm:")]
        if bad:
            raise Blocked("DIALOG " + " / ".join(bad)[:200])
        head = norm(text)[:25]
        ok = poll(tid, f"""if (document.readyState !== 'complete') return null;
          const t = document.body.innerText; const w = (t.match(/자동입력 ?방지|보안문자|일시적으로 제한|답변 등록이 제한/) || [''])[0];
          if (w) return {{warn: w}};
          return [...document.querySelectorAll('[class*=answer]')].some(e => !e.closest('.se-content') && __vis(e)
            && e.innerText.split(/\\s/).join('').includes({c.q(head)})) ? {{posted: true}} : null;""", 30)
        if ok.get("warn"):
            raise Blocked(f"WARN {ok['warn']}")
        out["posted"] = True
        if a.shot:
            c.run_js(tid, f"(() => {{ const e = [...document.querySelectorAll('[class*=answer]')].find(e => e.innerText.split(/\\s/).join('').includes({c.q(head)})); if (e) e.scrollIntoView({{block:'start'}}); return 1; }})()")
            time.sleep(1)
            out["shot"] = c.shot(tid, a.shot)
        emit(out, "POSTED", "")


run(main, a, f"지식iN 답변 등록: {a.url}")
