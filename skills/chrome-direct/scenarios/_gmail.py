"""Gmail web helpers (real Chrome, already signed in). Read-only except open_row (marks read)."""
import json
import time
from urllib.parse import quote

from _common import Blocked, js, poll

ROWS = r"""const main = [...document.querySelectorAll('div[role=main]')].filter(__vis)[0] || document;
const rows = [...main.querySelectorAll('tr.zA')].filter(__vis);"""


def search_url(query, account):
    return f"https://mail.google.com/mail/?authuser={account}#search/{quote(query, safe='')}"


def check_account(tid, account, timeout=30):
    """Wait for Gmail to load; raise Blocked if logged out or another account."""
    st = poll(tid, r"""if (/accounts\.google\.com/.test(location.host)) return {login: location.href};
      if (!/@/.test(document.title) || !document.querySelector('div[role=main]')) return null;  // Workspace 계정은 제목에 'Gmail'이 없다 return {title: document.title};""", timeout)
    if "login" in st:
        raise Blocked(f"LOGIN_REQUIRED Gmail 로그아웃 상태 ({st['login'][:80]}) — Chrome에서 직접 로그인 필요")
    if account not in st["title"]:
        raise Blocked(f"WRONG_ACCOUNT 열린 계정: {st['title']}")
    return st["title"]


def list_rows(tid, limit=50, timeout=25):
    """Rows of the current search/list view. Waits until rows or the empty notice show."""
    return poll(tid, ROWS + r"""
      const empty = [...document.querySelectorAll('td.TC')].filter(__vis).map(e => e.innerText.trim()).join(' ');
      if (!rows.length && !empty) return null;
      return {empty: empty, pager: ([...document.querySelectorAll('.Dj')].filter(__vis)[0] || {}).innerText || '',
        rows: rows.slice(0, %d).map(r => ({
          from: [...r.querySelectorAll('.yX [email], .yW [email]')].map(e => e.getAttribute('email') + (e.getAttribute('name') ? ' (' + e.getAttribute('name') + ')' : '')).filter((v, i, a) => a.indexOf(v) === i),
          who: ((r.querySelector('.yX') || {}).innerText || '').trim(),
          subject: ((r.querySelector('.bog') || {}).innerText || '').trim(),
          snippet: ((r.querySelector('.y2') || {}).innerText || '').replace(/^\s*-\s*/, '').trim().slice(0, 300),
          date: (r.querySelector('.xW span[title], .apt span[title]') || {}).title || '',
          attachments: [...r.querySelectorAll('.brg')].map(e => e.innerText.trim()),
          hasAttachment: !!r.querySelector('[aria-label="첨부파일 있음"], img.yE'),
          unread: r.classList.contains('zE')}))};""" % limit, timeout)


def search(tid, query, account, limit=50):
    """Run a search in an already-open Gmail tab (tab opened with search_url is fine too)."""
    check_account(tid, account)
    h = "#search/" + quote(query, safe="").replace("%20", "+")
    same = f"const cur = location.hash.startsWith('#search/') ? decodeURIComponent(location.hash.slice(8).replace(/\\+/g, ' ')) : ''; const same = cur === {json.dumps(query)};"
    if js(tid, same + f"if (!same) {{ location.hash = {json.dumps(h)}; return 'MOVED'; }} return 'SAME';") == "MOVED":
        time.sleep(2)
    poll(tid, same + "return same && /^(검색결과|Search results)/.test(document.title)", 20)
    time.sleep(0.5)
    return list_rows(tid, limit)


def open_row(tid, n=1, timeout=20):
    """Open the n-th (1-based) visible row and read the thread. Opening marks it read."""
    r = js(tid, ROWS + f"const r = rows[{n - 1}]; if (!r) return 'NOTFOUND'; r.click(); return 'OK';")
    if r != "OK":
        raise RuntimeError(f"row {n} not found")
    return poll(tid, r"""const h = [...document.querySelectorAll('h2.hP')].filter(__vis)[0]; if (!h) return null;
      const msgs = [...document.querySelectorAll('div.adn')].filter(__vis);
      return {url: location.href, subject: h.innerText.trim(),
        messages: msgs.map(m => ({
          from: [...m.querySelectorAll('.gD')].map(e => e.getAttribute('email'))[0] || '',
          to: [...m.querySelectorAll('.g2')].map(e => e.getAttribute('email')),
          date: (m.querySelector('.g3') || {}).title || '',
          body: [...m.querySelectorAll('.a3s')].map(e => e.innerText).join('\n').trim().slice(0, 4000),
          attachments: [...m.querySelectorAll('.aV3')].map(e => e.innerText.trim())}))};""", timeout)
