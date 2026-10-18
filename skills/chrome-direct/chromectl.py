#!/usr/bin/env python3
"""Drive the owner's real Chrome without an LLM: AppleScript `execute javascript` + cliclick.

Needs once: Chrome '보기 > 개발자 > Apple Events의 자바스크립트 허용' (pref
browser.allow_javascript_apple_events), Accessibility for tmux/cliclick.

Usage:
  chromectl.py tabs
  chromectl.py open <url> [--profile "Profile 4"]
  chromectl.py js   --match <url-or-title substr> "<js expression>"
  chromectl.py fill --match M --sel CSS (--value V | --env VAR)
  chromectl.py click --match M (--sel CSS | --text "다음")
  chromectl.py wait --match M (--text T | --sel CSS) [--timeout 20]
  chromectl.py text --match M            # visible text (first 4000 chars)
  chromectl.py newtab <url> [--profile "Profile 1"]   # prints id:<tab id>; use it as --match
  chromectl.py close --match id:<tab id>
  chromectl.py press --match M (--sel CSS | --text T) # pointer/mouse event sequence click
  chromectl.py shot --match M <out.png|out.pdf>       # screenshot of that tab's window
  chromectl.py run steps.json [--codex-fallback "<prompt>" --out FILE]
Exit 0 = ok, 1 = step failed (caller may fall back to Codex).
Secrets (--env) never hit argv or stdout: the JS goes through a 0600 temp file.
"""
import argparse, json, os, subprocess, sys, tempfile, time
from pathlib import Path

CODEX = Path.home() / ".config/claude-accounts/personal/skills/apps-in-toss-deploy/scripts/codex_console.sh"


def osa(script, timeout=20):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.rstrip("\n")


def tabs(with_id=False):
    out = osa('''set o to ""
tell application "Google Chrome"
  repeat with w from 1 to count windows
    repeat with t from 1 to count tabs of window w
      set o to o & w & "\t" & t & "\t" & (title of tab t of window w) & "\t" & (URL of tab t of window w) & "\t" & (id of tab t of window w) & linefeed
    end repeat
  end repeat
end tell
return o''')
    rows = [l.split("\t") for l in out.splitlines() if l.strip()]
    return rows if with_id else [r[:4] for r in rows]


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
        osa(f'tell application "Google Chrome" to tell window 1 to make new tab with properties {{URL:{q(url)}}}')
    end = time.time() + timeout
    while time.time() < end:
        time.sleep(1)
        new = [r for r in tabs(with_id=True) if r[4] not in before]
        if new:
            return "id:" + new[-1][4]
    raise RuntimeError(f"new tab did not appear for {url}")


def close_tab(match):
    w, t = find_tab(match)
    osa(f'tell application "Google Chrome" to close tab {t} of window {w}')


def goto(match, url):
    w, t = find_tab(match)
    osa(f'tell application "Google Chrome" to set URL of tab {t} of window {w} to {q(url)}')


def js_json(match, body, timeout=20):
    """Run `body` (statements ending in `return <value>`) inside an IIFE with the FIND helpers;
    returns the JSON-decoded value. Never declares page globals, so it is safe to re-run."""
    code = "(() => {" + FIND + "const __r = (() => {" + body + "})(); return JSON.stringify(__r === undefined ? null : __r);})()"
    out = run_js(match, code, timeout)
    return json.loads(out) if out not in ("", "missing value") else None


def run_js(match, code, timeout=20):
    w, t = find_tab(match)
    if code.startswith(FIND):  # keep helpers out of page globals (re-runs would redeclare)
        code = "(() => {" + FIND + "return " + code[len(FIND):] + ";})()"
    fd, path = tempfile.mkstemp(suffix=".js")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(code)
        os.chmod(path, 0o600)
        return osa(f'''set js to read POSIX file "{path}" as «class utf8»
tell application "Google Chrome" to execute tab {t} of window {w} javascript js''', timeout)
    finally:
        os.unlink(path)


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
    w, _ = find_tab(match)
    r = run_js(match, js)
    if r == "NOTFOUND":
        raise RuntimeError(f"rclick {sel or text}: NOTFOUND")
    osa(f'tell application "Google Chrome" to set index of window {w} to 1\ntell application "Google Chrome" to activate')
    time.sleep(0.4)
    subprocess.run(["cliclick", f"c:{r}"], check=True, capture_output=True)


def press(match, sel=None, text=None):
    """Synthetic pointer+mouse sequence (pointerdown..click) — for widgets that ignore a bare
    .click() (Google Forms '다음'/radio/checkbox, Toss console buttons)."""
    pick = f"__all(document, {q(sel)}).filter(__vis)[0]" if sel else f"__byText({q(text)})"
    r = run_js(match, FIND + f"(() => {{ const e = {pick}; if (!e) return 'NOTFOUND'; __press(e); return 'OK'; }})()")
    if r != "OK":
        raise RuntimeError(f"press {sel or text}: {r}")


def shot(match, path):
    """Screenshot the window showing this tab (brings it to front). path .png or .pdf.
    Needs Screen Recording permission for the terminal/tmux."""
    w, t = find_tab(match)
    osa(f'''tell application "Google Chrome"
  set active tab index of window {w} to {t}
  set index of window {w} to 1
  activate
end tell''')
    time.sleep(1.0)
    x1, y1, x2, y2 = [int(v) for v in osa('tell application "Google Chrome" to get bounds of window 1').split(", ")]
    path = str(path)
    png = path if path.endswith(".png") else path + ".png"
    subprocess.run(["screencapture", "-x", "-R", f"{x1},{y1},{x2 - x1},{y2 - y1}", png], check=True)
    if png != path:
        subprocess.run(["sips", "-s", "format", "pdf", png, "--out", path], check=True, capture_output=True)
        os.unlink(png)
    return path


def rtype(env=None, value=None, enter=False):
    """Type into whatever has focus with real keystrokes (fields that reject JS values)."""
    v = secret(env) if env else value
    subprocess.run(["cliclick", "-w", "40", f"t:{v}"], check=True, capture_output=True)
    if enter:
        subprocess.run(["cliclick", "kp:return"], check=True, capture_output=True)


def wait(match, text=None, sel=None, timeout=20):
    cond = (f"document.body && document.body.innerText.includes({q(text)})" if text
            else f"__all(document, {q(sel)}).filter(__vis).length > 0")
    js = FIND + f"(() => ({cond}) ? 'Y' : 'N')()"
    end = time.time() + timeout
    while time.time() < end:
        try:
            if run_js(match, js) == "Y":
                return
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
        osa(f'tell application "Google Chrome" to open location {q(url)}')
    time.sleep(3)


def secret(name):
    v = os.environ.get(name)
    if v is None:
        for f in (Path(".env"), Path.home() / ".claude/.env"):
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
    ap.add_argument("--timeout", type=int, default=20); ap.add_argument("--profile")
    ap.add_argument("--codex-fallback"); ap.add_argument("--out")
    a = ap.parse_args()
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
            rtype(a.env, a.value, enter=True)
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
                    if a.codex_fallback:
                        print("FALLBACK codex")
                        out = a.out or "/tmp/chromectl-codex.out"
                        prompt = f"{a.codex_fallback}\n(스크립트가 {i}번 단계 {json.dumps(s, ensure_ascii=False) if 'env' not in s else s['op']}에서 실패: {e}. 거기서부터 이어서 해라.)"
                        pf = out + ".prompt"
                        Path(pf).write_text(prompt)
                        sys.exit(subprocess.run(["bash", str(CODEX), pf, out]).returncode)
                    sys.exit(1)
        else:
            raise RuntimeError("unknown cmd")
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
