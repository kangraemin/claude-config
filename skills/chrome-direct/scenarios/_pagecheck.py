"""Shared page scan: keyword lines/links + own-name (full or masked) lines, name replaced by [이름]."""
import re
import time

from _common import js, poll

SCAN = r"""const t = document.body ? document.body.innerText : '';
  const login = /로그인이 필요|로그인 후 이용|로그인해 주세요|회원만/.test(t) && t.length < 3000;
  const lines = t.split('\n').map(s => s.trim()).filter(Boolean);
  const links = [...document.querySelectorAll('a[href]')].filter(__vis).map(a => ({text: a.innerText.trim().slice(0, 120), href: a.href})).filter(l => l.text);
  return {title: document.title, href: location.href, len: t.length, login, lines, links};"""


def name_re(name):
    if not name or len(name) < 2:
        return None
    f, l = re.escape(name[0]), re.escape(name[-1])
    mid = "".join(re.escape(ch) for ch in name[1:-1])
    return re.compile(f"{f}(?:{mid}|[*＊○●OoXx◯□]{{{max(1, len(name) - 2)}}}){l}")


def scan(tid, kws, name=None, wait=20):
    poll(tid, "return document.readyState === 'complete' && document.body && document.body.innerText.length > 50 ? 1 : null", wait)
    time.sleep(1.5)
    d = js(tid, SCAN, 30)
    nre = name_re(name)
    hide = (lambda s: nre.sub("[이름]", s)) if nre else (lambda s: s)
    hits = [hide(s)[:200] for s in d["lines"] if any(k in s for k in kws)][:40]
    links = [{"text": hide(l["text"]), "href": l["href"]} for l in d["links"] if any(k in l["text"] for k in kws)][:30]
    name_hits = [hide(s)[:200] for s in d["lines"] if nre and nre.search(s)][:20]
    return {"title": d["title"], "finalUrl": d["href"], "textLen": d["len"], "login": d["login"],
            "hits": hits, "links": links, "nameHits": name_hits}
