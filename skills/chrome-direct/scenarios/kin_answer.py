#!/usr/bin/env python3
"""[지식iN] 네이버 지식iN 질문 하나에 답변을 붙여 넣고(옵션) 등록한다. 먼저 naver_login.py로 로그인 확인.

  kin_answer.py --url <질문 URL> --text-file a.txt            # dry-run: 상태 확인 + 입력창에 붙여넣기까지
  kin_answer.py --url <질문 URL> --text-file a.txt --submit   # '등록'까지 누르고 내 답변이 보이는지 확인
  kin_answer.py --url <질문 URL> --check                      # 상태만(마감·채택·내 답변 있음)
  --image shot.png                                             # 본문 뒤에 사진 1장 첨부(에디터에 <img>가 들어간 걸 확인한 뒤에만 등록)
  --shot evidence.png                                          # 등록 후 화면 캡처
  --image shot.png --capture <사이트 URL> [--capture-height 555] # 그 URL을 지금 headless로 새로 찍어 shot.png에 덮어쓴 뒤 첨부
                                                                 # (재사용 캡처에 지난 마감일이 남는 걸 막는다. 광고 도메인은 막고 찍는다)

- SmartEditor ONE은 JS 값 넣기·가짜 paste 이벤트를 무시한다 → 실제 클릭(cliclick) + pbcopy + ⌘V.
  (가짜 paste 이벤트는 버퍼에 남았다가 다음 진짜 붙여넣기 때 같이 들어가니 쓰지 않는다.)
- alert/confirm은 막아서 문구를 기록한다(AppleScript가 대화상자에 걸려 멈추지 않게). confirm은 '확인'.
- 캡차·제한·경고 문구가 보이면 BLOCKED(exit 2) — 사람이 볼 때까지 더 올리지 않는다.
Exit 0 = OK/POSTED, 1 = 실패, 2 = BLOCKED(로그아웃·마감·채택·이미 답함·제한).
"""
import subprocess, time
from pathlib import Path

from _common import NO_UNLOAD, Blocked, emit, js, parser, poll, run, tab
import chromectl as c

ap = parser(__doc__)
ap.add_argument("--url", required=True)
ap.add_argument("--text-file")
ap.add_argument("--submit", action="store_true")
ap.add_argument("--check", action="store_true")
ap.add_argument("--shot")
ap.add_argument("--image")
ap.add_argument("--capture")
ap.add_argument("--capture-height", type=int, default=555)
a = ap.parse_args()
if a.capture and not a.image:
    ap.error("--capture needs --image (저장할 경로)")

AD_HOSTS = ("googlesyndication", "doubleclick", "adservice", "googletagservices", "googleadservices", "adsbygoogle")


def capture(url, path, height):
    """폭 450(2배율 → 900px) 첫 화면을 새로 찍는다. 광고 요청은 막는다. 예전 첨부(900×N)와 같은 크기."""
    from urllib.parse import urlsplit, urlunsplit
    from playwright.sync_api import sync_playwright
    u = urlsplit(url)  # 한글 도메인은 punycode로(손으로 옮겨 적다 틀리면 KISA 오류 화면이 찍힌다)
    url = urlunsplit(u._replace(netloc=u.netloc.encode("idna").decode()))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 450, "height": height}, device_scale_factor=2, locale="ko-KR")
        pg.route("**/*", lambda r: r.abort() if any(h in r.request.url for h in AD_HOSTS) else r.continue_())
        r = pg.goto(url, wait_until="networkidle", timeout=60000)
        body = pg.inner_text("body")
        if not r or r.status >= 400 or "KISA" in body or "페이지를 찾을 수" in body:
            b.close()
            raise SystemExit(f"capture FAIL: {url} status={r and r.status} — 오류 화면은 첨부하지 않는다")
        pg.add_style_tag(content="ins.adsbygoogle,.adsbygoogle,[id^=google_ads],iframe[src*=ads]{display:none!important}")
        pg.wait_for_timeout(800)
        pg.screenshot(path=str(Path(path).expanduser()))
        b.close()


if a.capture:
    capture(a.capture, a.image, a.capture_height)
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
IMG_COUNT = "return document.querySelectorAll('.se-content img.se-image-resource, .se-content .se-module-image img').length"
EDITOR_TEXT = "const e = document.querySelector('.se-content'); return e ? e.innerText : '';"


def key(*k):
    subprocess.run(["cliclick", *k], check=True, capture_output=True)


def attach_image(tid, path, out):
    """SE ONE 사진 버튼이 쓰는 숨은 input[type=file]에 base64→File→DataTransfer로 넣고 change 이벤트. 에디터에 img가 늘어야 성공."""
    import base64, mimetypes
    p = Path(path).expanduser()
    b64 = base64.b64encode(p.read_bytes()).decode()
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    before = js(tid, IMG_COUNT) or 0
    # 사진 버튼을 눌러 숨은 file input을 만들게 한다(파일 대화상자가 뜨면 안 되므로 input.click은 막는다)
    js(tid, """if (!window.__kinNoPick) { window.__kinNoPick = 1;
      const o = HTMLInputElement.prototype.click;
      HTMLInputElement.prototype.click = function () { if (this.type === 'file') { window.__kinFile = this; return; } return o.call(this); }; } return 1;""")
    try:
        c.press(tid, sel="button.se-image-toolbar-button")
    except Exception as e:  # 버튼 셀렉터가 다르면 텍스트로
        out["image_btn_err"] = str(e)[:100]
    time.sleep(1.5)
    r = js(tid, f"""const inp = window.__kinFile || document.querySelector('input[type=file]');
      if (!inp) return 'NO_INPUT';
      const bin = atob({c.q(b64)}); const u8 = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      const f = new File([u8], {c.q(p.name)}, {{type: {c.q(mime)}}});
      const dt = new DataTransfer(); dt.items.add(f); inp.files = dt.files;
      inp.dispatchEvent(new Event('input', {{bubbles: true}})); inp.dispatchEvent(new Event('change', {{bubbles: true}}));
      return 'SET';""", timeout=60)
    out["image_set"] = r
    deadline = time.time() + 40
    n = before
    while time.time() < deadline:
        n = js(tid, IMG_COUNT) or 0
        if n > before:
            break
        time.sleep(1.5)
    out["image_count"] = n
    out["image_src"] = (js(tid, "const i = document.querySelector('.se-content img'); return i ? (i.currentSrc || i.src || '').slice(0, 80) : ''") or "")
    if n <= before:
        raise RuntimeError(f"image not in editor (input={r}, imgs {before}->{n})")


def main():
    out = {"url": a.url}
    with tab(a.url, a) as tid:
        st = poll(tid, STATE, 30)
        out["state"] = st
        # 점검 화면엔 로그인 표시가 없어 LOGGED_OUT으로 오판한다(10/22 오후 내내) → 점검이면 따로 알린다
        if js(tid, "return /서비스 점검 중/.test(document.body.innerText.slice(0,500))"):
            raise Blocked("MAINTENANCE 지식iN 서비스 점검 중 — 이번 회차 넘김(로그인 확인·QR 불필요)")
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
        js(tid, NO_UNLOAD)
        c.press(tid, sel="._answerWriteButton")
        poll(tid, "return [...document.querySelectorAll('.se-content .se-text-paragraph')].some(__vis)", 15)
        norm = lambda s: "".join(s.split())  # noqa: E731
        for attempt in range(4):  # 포커스·붙여넣기가 가끔 빗나간다 → 클릭부터 다시(질문 페이지는 그대로)
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
            if norm(got) == norm(text):
                break
            out.setdefault("paste_retries", []).append(len(norm(got)))
            time.sleep(2)
        else:
            raise RuntimeError(f"editor mismatch: {len(norm(got))} vs {len(norm(text))} chars: {got[:80]!r}")
        out["pasted"] = len(text)
        if a.image:
            attach_image(tid, a.image, out)
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
