"""Apps-in-Toss console helpers (apps-in-toss.toss.im, logged in on Chrome Profile 1, workspace 35273)."""
import time

from _common import Blocked, js, poll
import chromectl as c

BASE = "https://apps-in-toss.toss.im/workspace/{ws}/mini-app"


def url(ws, app=None, path=""):
    return BASE.format(ws=ws) + (f"/{app}" if app else "") + (f"/{path}" if path else "")


def wait_page(tid, must, timeout=30):
    """Wait until body text contains `must`; Blocked if a login screen shows."""
    st = poll(tid, f"""const t = document.body ? document.body.innerText : '';
      if (/login|signin|auth/.test(location.pathname + location.host) && !/apps-in-toss\\.toss\\.im\\/workspace/.test(location.href)) return {{login: location.href}};
      if (/로그인하고|토스 비즈니스 로그인|QR 코드로 로그인/.test(t)) return {{login: location.href}};
      return t.includes({must!r}) ? {{ok: 1}} : null;""", timeout)
    if "login" in st:
        raise Blocked(f"LOGIN_REQUIRED 토스 비즈니스 로그인 필요 ({st['login'][:80]}) — 폰 승인형 로그인은 Codex/사람")
    time.sleep(1.0)


def table(tid, wait=10):
    """Rows of the first visible table; waits up to `wait` s for rows to render."""
    for _ in range(wait):
        rows = _table(tid)
        if rows:
            return rows
        time.sleep(1)
    return []


def _table(tid):
    return js(tid, r"""return [...document.querySelectorAll('table tbody tr')].filter(__vis).map((r, i) => ({i,
      cells: [...r.children].map(td => td.innerText.trim().replace(/\s*\n+\s*/g, ' / ')),
      buttons: [...r.querySelectorAll('button')].map(b => ({text: b.innerText.trim(), disabled: b.disabled || b.getAttribute('aria-disabled') === 'true'}))}))""") or []


def goto(tid, u, must):
    c.goto(tid, u)
    time.sleep(2)
    wait_page(tid, must)
