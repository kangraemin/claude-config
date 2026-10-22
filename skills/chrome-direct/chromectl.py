#!/usr/bin/env python3
"""Drive your real Chrome without an LLM: AppleScript `execute javascript` + cliclick.

Chrome '보기 > 개발자 정보 > Apple Events의 자바스크립트 허용': the first time JS is refused, System Events
tries the menu item and retries once (macOS asks once to allow the terminal app). If Chrome ignores the
click (seen 2026-10-22), exit 2 with the menu path for a person to turn on once.
Accessibility for the terminal/tmux and cliclick.

Usage:
  chromectl.py setup                     # 처음 한 번: 필수 권한·설정 점검, 켤 수 있는 건 바로 켬
  chromectl.py tabs
  chromectl.py open <url> [--profile "Profile 1"]
  chromectl.py js   --match <url-or-title substr> "<js expression>"
  chromectl.py fill --match M --sel CSS (--value V | --env VAR)
  chromectl.py click --match M (--sel CSS | --text "다음")
  chromectl.py wait --match M (--text T | --sel CSS) [--timeout 20]
  chromectl.py text --match M            # visible text (first 4000 chars)
  chromectl.py newtab <url> [--profile "Profile 1"]   # prints id:<tab id>; use it as --match
  chromectl.py close --match id:<tab id>
  chromectl.py press --match M (--sel CSS | --text T) # pointer/mouse event sequence click
  chromectl.py shot --match M <out.png|out.pdf>       # screenshot of that tab's window
  chromectl.py rtype (--value V | --env VAR) [--enter] # real keystrokes into the focused field
  chromectl.py run steps.json [--codex-fallback "<prompt>" --out FILE]
Exit 0 = ok, 1 = step failed (caller may fall back to Codex), 2 = macOS permission needed (a person allows it once).
Secrets (--env) never hit argv or stdout: JS goes through a 0600 temp file, rtype text through cliclick's stdin.
"""
import argparse, contextlib, json, os, subprocess, sys, tempfile, time
from pathlib import Path

# 선택 기능: Codex 폴백. CHROME_DIRECT_CODEX_SCRIPT(실행 가능한 래퍼: <prompt파일> <out파일> [cwd])가 있고
# codex·tmux가 PATH에 있을 때만 쓴다. 없으면 폴백을 조용히 건너뛰고 실패를 그대로 보고한다.
_cs = os.environ.get("CHROME_DIRECT_CODEX_SCRIPT", str(Path.home() / ".config/claude-accounts/personal/skills/apps-in-toss-deploy/scripts/codex_console.sh"))
CODEX = Path(_cs).expanduser() if _cs else None


def codex_available():
    import shutil
    return bool(CODEX and CODEX.is_file() and shutil.which("codex") and shutil.which("tmux"))


class NeedsPermission(RuntimeError):
    """macOS 권한이 없어 사람이 한 번 허용해야 함. Codex로 넘기지 않고 종료코드 2로 멈춘다."""


def _terminal_app():
    names = {"Apple_Terminal": "터미널", "iTerm.app": "iTerm", "ghostty": "Ghostty", "vscode": "VS Code", "WezTerm": "WezTerm",
             "com.apple.Terminal": "터미널", "com.googlecode.iterm2": "iTerm", "com.mitchellh.ghostty": "Ghostty",
             "com.microsoft.VSCode": "VS Code", "com.github.wez.wezterm": "WezTerm"}
    # tmux 안에선 TERM_PROGRAM이 tmux라, 터미널 앱이 남긴 번들 id로도 찾는다
    for k in ("TERM_PROGRAM", "__CFBundleIdentifier"):
        if os.environ.get(k) in names:
            return names[os.environ[k]]
    return "이 명령을 실행한 터미널 앱"


def _js_off(err):
    # 한국어판 원문: "AppleScript를 통한 자바스크립트 실행 기능이 꺼져 있습니다 ... Apple Events의 자바스크립트 허용"
    # 영어판도 메뉴 이름에 "Apple Events"와 "JavaScript"가 들어간다고 보고 맞췄다(영어판은 미검증).
    s = str(err)
    return "Apple Events" in s and ("자바스크립트" in s or "JavaScript" in s)


# 메뉴 이름이 언어마다 달라서 메뉴바 > 메뉴 > 하위 메뉴를 돌며 "Apple Events"가 든 항목을 찾는다.
# 체크(✓)돼 있으면 누르지 않는다 — 토글이라 누르면 꺼진다.
ENABLE_JS = """
tell application "System Events"
  set p to first process whose unix id is %s
  repeat with mb in menu bar items of menu bar 1 of p
    try
      repeat with mi in menu items of menu 1 of mb
        try
          set nms to name of every menu item of menu 1 of mi
          repeat with i from 1 to count of nms
            set n to item i of nms
            if n is not missing value and n contains "Apple Events" then
              set si to menu item i of menu 1 of mi
              set mk to value of attribute "AXMenuItemMarkChar" of si
              if mk is not missing value and mk is not "" then return "ALREADY"
              click si
              return "CLICKED"
            end if
          end repeat
        end try
      end repeat
    end try
  end repeat
  return "NOTFOUND"
end tell
"""


def enable_apple_events_js():
    """Chrome 메뉴 'Apple Events의 자바스크립트 허용'을 켠다. CLICKED | ALREADY.
    System Events 권한이 없으면 NeedsPermission. 이 권한 창은 아무도 안 누르고 두면 거부로 굳는다."""
    pid = chrome_pid()
    if not pid:
        raise RuntimeError("Chrome 프로세스를 못 찾아 메뉴를 켤 수 없음")
    how = (f"시스템 설정 > 개인정보 보호 및 보안 > 자동화(또는 손쉬운 사용)에서 {_terminal_app()}을 허용한 뒤 다시 실행"
           " — 권한 창이 떠 있으면 '허용'을 누른다")
    try:
        r = osa(ENABLE_JS % pid, timeout=60)
    except subprocess.TimeoutExpired:  # 권한 창이 떠서 대답을 기다리는 중
        raise NeedsPermission(how)
    except RuntimeError as e:
        if any(k in str(e) for k in ("-1743", "-25211", "-1719", "assistive", "보조 접근", "Not authorized", "권한")):
            raise NeedsPermission(how)
        raise
    if r == "NOTFOUND":
        raise NeedsPermission(MANUAL_JS)
    return r


MANUAL_JS = ("Chrome이 자바스크립트 실행을 막고 있고 자동으로 켜지지 않음 — `chromectl.py setup`을 실행하거나, 그 탭이 있는 "
             "Chrome 창에서 메뉴 '보기 > 개발자 정보 > Apple Events의 자바스크립트 허용'을 직접 한 번 켠다"
             " (영어판: View > Developer > Allow JavaScript from Apple Events, 미검증)")

SETTINGS_URL = "x-apple.systempreferences:com.apple.preference.security?Privacy_"

# "Apple Events" 항목이 든 하위 메뉴의 (메뉴바 항목 번호, 메뉴 항목 번호)
JS_MENU_IDX = """
tell application "System Events"
  set p to first process whose unix id is %s
  set mbs to menu bar items of menu bar 1 of p
  repeat with i from 1 to count of mbs
    try
      set mis to menu items of menu 1 of (item i of mbs)
      repeat with j from 1 to count of mis
        try
          set nms to name of every menu item of menu 1 of (item j of mis)
          repeat with n in nms
            set n to contents of n
            if n is not missing value and n contains "Apple Events" then return (i as text) & " " & (j as text)
          end repeat
        end try
      end repeat
    end try
  end repeat
  return ""
end tell
"""

# 화면 좌표는 메뉴가 펼쳐져 있을 때만 맞다(닫혀 있으면 0,1080 같은 값) → 메뉴바를 연 다음에 읽는다
MENU_CENTER = """
tell application "System Events"
  set e to %s of menu bar 1 of (first process whose unix id is %s)
  set {x, y} to position of e
  set {w, h} to size of e
end tell
return ((x + w / 2) as integer as text) & "," & ((y + h / 2) as integer as text)
"""


def open_js_menu():
    """사람이 한 번만 누르면 되게, 진짜 마우스로 '보기 > 개발자 정보' 하위 메뉴를 펼쳐 둔다."""
    pid = chrome_pid()
    idx = osa(JS_MENU_IDX % pid, timeout=60).split()
    if len(idx) != 2:
        return False
    bar = f"menu bar item {idx[0]}"
    jxa("C.activate()")
    time.sleep(0.5)
    subprocess.run(["cliclick", "c:" + osa(MENU_CENTER % (bar, pid))], check=True, capture_output=True)
    time.sleep(0.6)
    sub = osa(MENU_CENTER % (f"menu item {idx[1]} of menu 1 of {bar}", pid))
    subprocess.run(["cliclick", f"m:{sub}"], check=True, capture_output=True)
    return True


def _js_ok():
    try:
        return jxa("return String(C.windows[0].activeTab().execute({javascript: '1+1'}))", timeout=10) == "2"
    except RuntimeError as e:
        if _js_off(e):
            return False
        raise


def setup():
    """처음 설치한 맥에서 한 번: 필수 설정만 점검하고, 켤 수 있는 건 바로 켠다.
    사람 손이 필요한 것은 그 설정 화면(또는 Chrome 메뉴)을 열어 두고 무엇을 누를지 한 줄로 말한다. 0 = 준비됨, 2 = 사람 몫 남음."""
    import platform, shutil
    app, todo = _terminal_app(), []
    ok = lambda m: print(f"OK    {m}")
    need = lambda m: (todo.append(m), print(f"TODO  {m}"))
    if platform.system() != "Darwin" or not Path(CHROME_BIN).exists():
        print("FAIL  macOS와 Google Chrome(/Applications)이 필요"); return 1
    if not chrome_pid():
        subprocess.run(["open", "-a", "Google Chrome"]); time.sleep(4)
    if not shutil.which("cliclick"):
        if shutil.which("brew"):
            print("...   cliclick 설치 중 (brew install cliclick)")
            subprocess.run(["brew", "install", "cliclick"], capture_output=True)
        if not shutil.which("cliclick"):
            need("cliclick 설치: Homebrew(https://brew.sh) 설치 후 `brew install cliclick`")
    if shutil.which("cliclick"):
        ok("cliclick")
    # 1) Chrome 제어 권한(자동화). 처음이면 macOS 창이 뜬다 — 놔두면 거부로 굳으니 바로 누르라고 먼저 말한다.
    print(f"...   macOS 권한 창이 뜨면 '허용'을 누른다 ({app})")
    try:
        jxa("return C.windows.length", timeout=60); ok("Chrome 제어(자동화)")
    except (RuntimeError, subprocess.TimeoutExpired):
        subprocess.run(["open", SETTINGS_URL + "Automation"])
        need(f"방금 열린 '자동화' 화면에서 {app} 아래 'Google Chrome'·'System Events'를 켠다")
    # 2) 손쉬운 사용(메뉴 읽기·cliclick)
    try:
        osa(f'tell application "System Events" to get name of menu bar item 1 of menu bar 1 of (first process whose unix id is {chrome_pid()})', timeout=60)
        ok("손쉬운 사용")
    except (RuntimeError, subprocess.TimeoutExpired):
        subprocess.run(["open", SETTINGS_URL + "Accessibility"])
        need(f"방금 열린 '손쉬운 사용' 화면에서 {app}을 켠다 (목록에 없으면 + 로 추가)")
    # 3) Chrome 'Apple Events의 자바스크립트 허용'
    if not todo:
        if not _js_ok():
            with contextlib.suppress(Exception):
                enable_apple_events_js(); time.sleep(0.5)
        if _js_ok():
            ok("Chrome 'Apple Events의 자바스크립트 허용'")
        else:
            opened = open_js_menu()
            print("TODO  " + ("지금 펼쳐진 Chrome 메뉴에서 'Apple Events의 자바스크립트 허용'을 누른다" if opened
                              else "Chrome 메뉴 '보기 > 개발자 정보 > Apple Events의 자바스크립트 허용'을 누른다") + " (60초 기다림)")
            end = time.time() + 60
            while time.time() < end and not _js_ok():
                time.sleep(2)
            if _js_ok():
                ok("Chrome 'Apple Events의 자바스크립트 허용'")
            else:
                todo.append("js")
    print("READY" if not todo else "RESULT: BLOCKED 위 TODO를 끝낸 뒤 setup을 다시 실행")
    return 0 if not todo else 2



def osa(script, timeout=20):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.rstrip("\n")


def chrome_pid():
    """진짜 Chrome(사용자 프로필) 메인 프로세스 pid. 다른 세션의 Playwright가 같은 Google Chrome.app을
    --user-data-dir로 띄우면 AppleScript `tell application "Google Chrome"`이 그쪽을 잡는다(2026-10-22).
    그래서 Chrome 명령은 전부 JXA `Application(pid)`로 보낸다. 못 찾으면 None(이름으로 보냄)."""
    # 새 탭을 여는 `Google Chrome --profile-directory=…`도 잠깐 메인처럼 보인다 → 가장 오래 돈 것을 고른다
    r = subprocess.run(["ps", "-axo", "pid=,etime=,args="], capture_output=True, text=True)
    best = None
    for line in r.stdout.splitlines():
        pid, et, args = (line.split(None, 2) + ["", ""])[:3]
        if args.startswith(CHROME_BIN) and "--type=" not in args and "--user-data-dir" not in args:
            d, _, hms = et.rpartition("-")
            secs = int(d or 0) * 86400 + sum(int(x) * 60 ** i for i, x in enumerate(reversed(hms.split(":"))))
            if best is None or secs > best[0]:
                best = (secs, int(pid))
    return best and best[1]


def jxa(body, timeout=20):
    """JXA로 진짜 Chrome에 명령. body는 `C`(Chrome 앱 객체)를 쓰고 return으로 값을 돌려준다."""
    pid = chrome_pid()
    app = str(pid) if pid else '"Google Chrome"'
    script = f"ObjC.import('Foundation'); var C = Application({app}); (function(){{ {body} }})()"
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", script], capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    out = r.stdout.rstrip("\n")
    return "" if out == "undefined" else out


def tabs(with_id=False):
    # Retry when another session closes a tab mid-loop (-1719 invalid index)
    for i in range(5):
        try:
            out = _tabs_raw(); break
        except RuntimeError as e:
            if "-1719" not in str(e) or i == 4: raise
            time.sleep(0.5)
    rows = [l.split("\t") for l in out.splitlines() if l.strip()]
    return [r[:5] for r in rows] if with_id == True else rows if with_id == "full" else [r[:4] for r in rows]


def _tabs_raw():
    return jxa("""var w = C.windows.id(), ti = C.windows.tabs.title(), u = C.windows.tabs.url(), t = C.windows.tabs.id(), o = "";
for (var i = 0; i < w.length; i++) for (var j = 0; j < t[i].length; j++)
  o += [i + 1, j + 1, String(ti[i][j]).replace(/[\\t\\n]/g, " "), u[i][j], t[i][j], w[i]].join("\\t") + "\\n";
return o;""")


def ref(match):
    """JXA specifier by ids (C.windows.byId(W).tabs.byId(T)). Indexes shift when other sessions open/close
    tabs or raise windows, so every action resolves to ids right before it runs."""
    for w, t, title, url, tid, wid in tabs(with_id="full"):
        if (match[3:] == tid) if match.startswith("id:") else (match in url or match in title):
            win = f"C.windows.byId({int(wid)})"
            return f"{win}.tabs.byId({int(tid)})", win
    raise RuntimeError(f"no tab matches {match!r}")


def find_tab(match):
    """match = URL/title substring, or "id:<tab id>" (from new_tab) for an exact tab."""
    for w, t, title, url, tid in tabs(with_id=True):
        if (match[3:] == tid) if match.startswith("id:") else (match in url or match in title):
            return int(w), int(t)
    raise RuntimeError(f"no tab matches {match!r}")


CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def new_tab(url, profile=None, timeout=15):
    """Open url in a NEW tab (in the given profile's window) and return "id:<tab id>".
    Uses the Chrome binary, which hands the URL to the running instance (no 2nd instance)."""
    before = {r[4] for r in tabs(with_id=True)}
    if profile:
        subprocess.Popen([CHROME_BIN, f"--profile-directory={profile}", url],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        jxa(f"C.windows[0].tabs.push(C.Tab({{url: {q(url)}}}))")
    end = time.time() + timeout
    while time.time() < end:
        time.sleep(1)
        new = [r for r in tabs(with_id=True) if r[4] not in before]
        if new:
            return "id:" + new[-1][4]
    raise RuntimeError(f"new tab did not appear for {url}")


def close_tab(match):
    tab, _w = ref(match)
    jxa(f"{tab}.close()")


def goto(match, url):
    tab, _w = ref(match)
    jxa(f"{tab}.url = {q(url)}")


def js_json(match, body, timeout=20):
    """Run `body` (statements ending in `return <value>`) inside an IIFE with the FIND helpers;
    returns the JSON-decoded value. Never declares page globals, so it is safe to re-run."""
    code = "(() => {" + FIND + "const __r = (() => {" + body + "})(); return JSON.stringify(__r === undefined ? null : __r);})()"
    out = run_js(match, code, timeout)
    return json.loads(out) if out not in ("", "missing value") else None


def run_js(match, code, timeout=20):
    tab, _w = ref(match)
    if code.startswith(FIND):  # keep helpers out of page globals (re-runs would redeclare)
        code = "(() => {" + FIND + "return " + code[len(FIND):] + ";})()"
    fd, path = tempfile.mkstemp(suffix=".js")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(code)
        os.chmod(path, 0o600)
        body = (f"var js = $.NSString.stringWithContentsOfFileEncodingError({q(path)}, $.NSUTF8StringEncoding, null).js;"
                f" var r = {tab}.execute({{javascript: js}}); return r === undefined || r === null ? 'missing value' : String(r);")
        try:
            return jxa(body, timeout)
        except RuntimeError as e:
            if not _js_off(e):
                raise
            # 처음 설치한 사람: 메뉴를 자동으로 켜고 한 번만 다시 시도. 설정은 프로필마다라 그 탭의 창을 앞으로 둔다.
            jxa(f"{_w}.index = 1; C.activate()")
            time.sleep(0.5)
            enable_apple_events_js()
            time.sleep(0.5)
            try:
                return jxa(body, timeout)
            except RuntimeError as e2:
                if _js_off(e2):  # 2026-10-22 실측: 이 항목만 System Events·cliclick 클릭을 Chrome이 무시했다
                    raise NeedsPermission(MANUAL_JS)
                raise
    finally:
        os.unlink(path)


def window_bounds():
    """맨 앞 창의 (x1, y1, x2, y2)."""
    return [int(v) for v in jxa("var b = C.windows[0].bounds(); return [b.x, b.y, b.x + b.width, b.y + b.height].join(',')").split(",")]


def q(s):
    return json.dumps(s, ensure_ascii=False)


# Finds elements in the page and in open shadow roots / same-origin iframes.
FIND = r"""
var __all = (root, sel) => { let r = [...root.querySelectorAll(sel)];
  root.querySelectorAll('*').forEach(e => { if (e.shadowRoot) r = r.concat(__all(e.shadowRoot, sel)); });
  root.querySelectorAll('iframe').forEach(f => { try { r = r.concat(__all(f.contentDocument, sel)); } catch (e) {} });
  return r; };
var __vis = e => { const b = e.getBoundingClientRect(); return b.width > 0 && b.height > 0; };
var __byText = t => __all(document, 'button,a,[role=button],input[type=submit],span,div,label')
  .filter(e => __vis(e) && (e.innerText || e.value || '').trim() === t)
  .sort((a, b) => (a.innerText || '').length - (b.innerText || '').length)[0]
  || __all(document, 'button,a,[role=button]').filter(e => __vis(e) && (e.innerText || '').includes(t))[0];
var __press = e => { e.scrollIntoView({block: 'center'}); const b = e.getBoundingClientRect();
  const o = {bubbles: true, cancelable: true, view: window, clientX: b.left + b.width / 2, clientY: b.top + b.height / 2, button: 0};
  for (const k of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'])
    e.dispatchEvent(new (k.startsWith('pointer') ? PointerEvent : MouseEvent)(k, o)); };
var __setv = (e, v) => { e.focus(); const p = e.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(p, 'value').set.call(e, v);
  e.dispatchEvent(new Event('input', {bubbles: true})); e.dispatchEvent(new Event('change', {bubbles: true})); e.blur(); return e.value === v; };
"""


def fill(match, sel, value):
    js = FIND + f"""(() => {{ const e = __all(document, {q(sel)}).filter(__vis)[0]; if (!e) return 'NOTFOUND';
  e.focus(); const proto = e.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(e, {q(value)});
  e.dispatchEvent(new Event('input', {{bubbles: true}})); e.dispatchEvent(new Event('change', {{bubbles: true}}));
  return e.value.length === {len(value)} ? 'OK' : 'MISMATCH'; }})()"""
    r = run_js(match, js)
    if r != "OK":
        raise RuntimeError(f"fill {sel}: {r}")


def click(match, sel=None, text=None):
    pick = f"__all(document, {q(sel)}).filter(__vis)[0]" if sel else f"__byText({q(text)})"
    js = FIND + f"(() => {{ const e = {pick}; if (!e) return 'NOTFOUND'; e.scrollIntoView({{block:'center'}}); e.click(); return 'OK'; }})()"
    r = run_js(match, js)
    if r != "OK":
        raise RuntimeError(f"click {sel or text}: {r}")


def rclick(match, sel=None, text=None):
    """Real mouse click (cliclick) at the element's screen position — for cross-origin
    iframes (Google sign-in button) and pages that ignore synthetic clicks."""
    pick = f"__all(document, {q(sel)}).filter(__vis)[0]" if sel else f"__byText({q(text)})"
    js = FIND + f"""(() => {{ const e = {pick}; if (!e) return 'NOTFOUND'; e.scrollIntoView({{block:'center'}});
  const b = e.getBoundingClientRect(); const top = window.outerHeight - window.innerHeight;
  return Math.round(window.screenX + b.left + b.width / 2) + ',' + Math.round(window.screenY + top + b.top + b.height / 2); }})()"""
    _t, win = ref(match)
    r = run_js(match, js)
    if r == "NOTFOUND":
        raise RuntimeError(f"rclick {sel or text}: NOTFOUND")
    jxa(f"{win}.index = 1; C.activate()")
    time.sleep(0.4)
    subprocess.run(["cliclick", f"c:{r}"], check=True, capture_output=True)


def press(match, sel=None, text=None):
    """Synthetic pointer+mouse sequence (pointerdown..click) — for widgets that ignore a bare
    .click() (Google Forms '다음'/radio/checkbox)."""
    pick = f"__all(document, {q(sel)}).filter(__vis)[0]" if sel else f"__byText({q(text)})"
    r = run_js(match, FIND + f"(() => {{ const e = {pick}; if (!e) return 'NOTFOUND'; __press(e); return 'OK'; }})()")
    if r != "OK":
        raise RuntimeError(f"press {sel or text}: {r}")


def shot(match, path):
    """Screenshot the window showing this tab (brings it to front). path .png or .pdf.
    Needs Screen Recording permission for the terminal/tmux."""
    w, t = find_tab(match)
    _t, win = ref(match)
    jxa(f"{win}.activeTabIndex = {t}; {win}.index = 1; C.activate()")
    time.sleep(1.0)
    x1, y1, x2, y2 = window_bounds()
    path = str(path)
    png = path if path.endswith(".png") else path + ".png"
    subprocess.run(["screencapture", "-x", "-R", f"{x1},{y1},{x2 - x1},{y2 - y1}", png], check=True)
    if png != path:
        subprocess.run(["sips", "-s", "format", "pdf", png, "--out", path], check=True, capture_output=True)
        os.unlink(png)
    return path


def google_relogin(match, email=None, tries=3):
    """Google 계정이 '로그아웃됨'이면 다시 로그인한다(사용자 손 불필요). 이미 로그인 상태면 바로 True.
    계정 선택 → 페이지 '계속' → macOS 패스키 시트 '계속'(지문 없이 통과). 시트는 DOM·AX 밖이라 cliclick 좌표로 누른다:
    시트는 창 가운데에 뜨고 '계속'은 중심에서 (+197, +117)pt. 1분쯤 지나면 '요청 제한 시간 초과' 창이 따로 뜨는데 그 '닫기'는 창 좌상단 (+395, +262)pt."""
    email = email or os.environ.get("CHROME_DIRECT_GOOGLE_ACCOUNT") or "remin1994@gmail.com"
    if not email:
        raise RuntimeError("google_relogin: email 인자 또는 CHROME_DIRECT_GOOGLE_ACCOUNT 필요")
    url = lambda: js_json(match, "return location.href")
    for _ in range(tries):
        if "accounts.google.com" not in url():
            return True
        js_json(match, f"const a=document.querySelector('[data-identifier=\"{email}\"]');if(a)a.click();return !!a"); time.sleep(5)
        run_js(match, "setTimeout(()=>{const b=[...document.querySelectorAll('button')].find(b=>/^(계속|다시 시도)$/.test(b.innerText.trim()));b&&b.click()},10);'ok'"); time.sleep(3)
        _t, win = ref(match)
        jxa(f"{win}.index = 1; C.activate()"); time.sleep(0.5)
        x1, y1, x2, y2 = window_bounds()
        subprocess.run(["cliclick", f"c:{(x1 + x2) // 2 + 197},{(y1 + y2) // 2 + 117}"], check=True); time.sleep(8)
        try:  # 시간 초과 창이 떠 있으면 닫는다
            ex, ey = [int(v) for v in osa('tell application "System Events" to tell process "Google Chrome" to get position of window "문제가 발생했습니다"').split(", ")]
            subprocess.run(["cliclick", f"c:{ex + 395},{ey + 262}"], check=True); time.sleep(2)
        except RuntimeError:
            pass
    return "accounts.google.com" not in url()


# 입력 소스를 argv[0](없으면 ASCII 자판, 보통 ABC)로 바꾸고 바꾸기 전 id를 돌려준다
INPUT_SRC = r"""ObjC.import("Carbon");
function idOf(s) { return ObjC.castRefToObject($.TISGetInputSourceProperty(s, $.kTISPropertyInputSourceID)).js; }
function run(argv) {
  var cur = idOf($.TISCopyCurrentKeyboardInputSource());
  var want = argv[0] || idOf($.TISCopyCurrentASCIICapableKeyboardLayoutInputSource());
  if (want === cur) return cur;
  var l = ObjC.castRefToObject($.TISCreateInputSourceList(null, false));
  for (var i = 0; i < l.count; i++) if (idOf(l.objectAtIndex(i)) === want) { $.TISSelectInputSource(l.objectAtIndex(i)); delay(0.2); break; }
  return cur;
}"""


def input_source(want=""):
    """Select an input source (default: the ASCII layout) and return the previous id, or None."""
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", INPUT_SRC] + ([want] if want else []),
                       capture_output=True, text=True, timeout=10)
    return r.stdout.strip() or None if r.returncode == 0 else None


def rtype(env=None, value=None, enter=False):
    """Type into whatever has focus with real keystrokes (fields that reject JS values).
    The text goes to cliclick on stdin (-f -), so a secret never shows up in `ps` argv."""
    v = secret(env) if env else value
    if v is None or "\n" in v:
        raise RuntimeError("rtype: --value 또는 --env 가 필요하고, 줄바꿈은 넣을 수 없음")
    cmds = f"t:{v}\n" + ("kp:return\n" if enter else "")
    # 한글 입력기가 켜져 있으면 cliclick이 "hello"를 "ㅗ디ㅣㅐ"로 친다(2026-10-22 실측) → 잠깐 ASCII 자판으로
    prev = input_source() if v.isascii() else None
    try:
        subprocess.run(["cliclick", "-w", "40", "-f", "-"], input=cmds, text=True, check=True, capture_output=True)
    finally:
        if prev:
            input_source(prev)


def wait(match, text=None, sel=None, timeout=20):
    cond = (f"document.body && document.body.innerText.includes({q(text)})" if text
            else f"__all(document, {q(sel)}).filter(__vis).length > 0")
    js = FIND + f"(() => ({cond}) ? 'Y' : 'N')()"
    end = time.time() + timeout
    while time.time() < end:
        try:
            if run_js(match, js) == "Y":
                return
        except NeedsPermission:
            raise
        except RuntimeError:
            pass
        time.sleep(1)
    raise RuntimeError(f"wait timeout: {text or sel}")


def page_text(match):
    return run_js(match, "document.body.innerText.slice(0, 4000)")


def open_url(url, profile=None):
    if profile:
        subprocess.run(["open", "-na", "/Applications/Google Chrome.app", "--args", f"--profile-directory={profile}", url], check=True)
    else:
        jxa(f"C.openLocation({q(url)})")
    time.sleep(3)


def secret(name):
    v = os.environ.get(name)
    if v is None:
        for f in (Path(".env"), Path.home() / ".claude/.env", Path.home() / ".chrome-direct/.env"):
            if f.exists():
                for line in f.read_text().splitlines():
                    if line.startswith(name + "="):
                        v = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
            if v is not None:
                break
    if v is None:
        raise RuntimeError(f"env {name} not found")
    return v


def step(s):
    op, m = s["op"], s.get("match", "")
    if op == "open":
        open_url(s["url"], s.get("profile"))
    elif op == "fill":
        fill(m, s["sel"], secret(s["env"]) if "env" in s else s["value"])
    elif op == "click":
        click(m, s.get("sel"), s.get("text"))
    elif op == "rclick":
        rclick(m, s.get("sel"), s.get("text"))
    elif op == "press":
        press(m, s.get("sel"), s.get("text"))
    elif op == "rtype":
        rtype(s.get("env"), s.get("value"), s.get("enter", False))
    elif op == "wait":
        wait(m, s.get("text"), s.get("sel"), s.get("timeout", 20))
    elif op == "js":
        print(run_js(m, s["code"]))
    elif op == "sleep":
        time.sleep(s["sec"])
    else:
        raise RuntimeError(f"unknown op {op}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--match", default="")
    ap.add_argument("--sel"); ap.add_argument("--text"); ap.add_argument("--value"); ap.add_argument("--env")
    ap.add_argument("--enter", action="store_true", help="rtype 뒤 Enter")
    ap.add_argument("--timeout", type=int, default=20); ap.add_argument("--profile")
    ap.add_argument("--codex-fallback"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "setup":
        sys.exit(setup())
    try:
        if a.cmd == "tabs":
            for row in tabs():
                print("\t".join(row))
        elif a.cmd == "open":
            open_url(a.arg, a.profile)
        elif a.cmd == "js":
            print(run_js(a.match, a.arg))
        elif a.cmd == "fill":
            fill(a.match, a.sel, secret(a.env) if a.env else a.value)
        elif a.cmd == "click":
            click(a.match, a.sel, a.text)
        elif a.cmd == "rclick":
            rclick(a.match, a.sel, a.text)
        elif a.cmd == "press":
            press(a.match, a.sel, a.text)
        elif a.cmd == "shot":
            print(shot(a.match, a.arg))
        elif a.cmd == "newtab":
            print(new_tab(a.arg, a.profile))
        elif a.cmd == "close":
            close_tab(a.match)
        elif a.cmd == "rtype":
            rtype(a.env, a.value, enter=a.enter)
        elif a.cmd == "wait":
            wait(a.match, a.text, a.sel, a.timeout)
        elif a.cmd == "text":
            print(page_text(a.match))
        elif a.cmd == "run":
            steps = json.loads(Path(a.arg).read_text())
            for i, s in enumerate(steps):
                try:
                    step(s)
                    print(f"STEP {i} {s['op']} OK")
                except Exception as e:
                    print(f"STEP {i} {s['op']} FAIL: {e}")
                    if a.codex_fallback and codex_available():
                        print("FALLBACK codex")
                        out = a.out or "/tmp/chromectl-codex.out"
                        prompt = f"{a.codex_fallback}\n(스크립트가 {i}번 단계 {json.dumps(s, ensure_ascii=False) if 'env' not in s else s['op']}에서 실패: {e}. 거기서부터 이어서 해라.)"
                        pf = out + ".prompt"
                        Path(pf).write_text(prompt)
                        sys.exit(subprocess.run(["bash", str(CODEX), pf, out]).returncode)
                    sys.exit(1)
        else:
            raise RuntimeError("unknown cmd")
    except NeedsPermission as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
