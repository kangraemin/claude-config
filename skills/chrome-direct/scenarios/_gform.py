"""Google Forms helpers (docs.google.com/forms viewform, real Chrome).
Buttons/radios/checkboxes ignore a bare .click(); they need __press (pointer+mouse sequence)."""
import json
import time

from _common import js, poll

STATE = r"""
const txt = document.body ? document.body.innerText : '';
const btn = [...document.querySelectorAll('[role=button]')].filter(__vis).map(b => b.innerText.trim()).filter(Boolean);
const acct = (txt.match(/([\w.+-]+@[\w-]+\.[\w.]+)\s*(계정 전환|Switch account)/) || [])[1] || '';
const items = [...document.querySelectorAll('div[role=listitem]')].filter(__vis).map((it, i) => {
  const h = it.querySelector('[role=heading]');
  const title = h ? h.innerText.replace(/\s*\*\s*$/, '').trim() : '';
  const req = !!(h && /\*\s*$/.test(h.innerText)) || !!it.querySelector('[aria-required=true]');
  const radios = [...it.querySelectorAll('[role=radio]')], checks = [...it.querySelectorAll('[role=checkbox]')];
  const date = it.querySelector('input[type=date]'), lb = it.querySelector('[role=listbox]');
  const txts = [...it.querySelectorAll('input[type=text],input[type=email],input[type=number],input[type=tel],input[type=url],input:not([type]),textarea')].filter(__vis);
  const file = /파일 추가|Add file/.test(it.innerText);
  const grid = it.querySelectorAll('[role=radiogroup],[role=group]').length > 1;
  const kind = grid ? 'grid' : file ? 'file' : date ? 'date' : radios.length ? 'radio' : checks.length ? 'checkbox' : lb ? 'dropdown'
    : txts.some(e => e.tagName === 'TEXTAREA') ? 'textarea' : txts.length ? 'text' : 'section';
  const opts = radios.length ? radios.map(e => e.getAttribute('data-value') || e.getAttribute('aria-label'))
    : checks.length ? checks.map(e => e.getAttribute('data-answer-value') || e.getAttribute('aria-label'))
    : lb ? [...it.querySelectorAll('[role=option]')].map(e => e.getAttribute('data-value')).filter(Boolean) : [];
  const answered = date ? !!date.value : radios.length ? radios.some(e => e.getAttribute('aria-checked') === 'true')
    : checks.length ? checks.some(e => e.getAttribute('aria-checked') === 'true') : txts.some(e => e.value);
  const err = ([...it.querySelectorAll('[role=alert]')].filter(__vis)[0] || {}).innerText || '';
  return {i, title, required: req, kind, options: opts.slice(0, 30), answered, error: err.trim()};
}).filter(x => x.title || x.kind !== 'section');
return {url: location.href, title: document.title, account: acct, buttons: btn,
  needsLogin: /accounts\.google\.com/.test(location.host) || /로그인해야|Sign in to continue/.test(txt),
  closed: /더 이상 응답을 받지 않습니다|no longer accepting responses/i.test(txt),
  alreadyResponded: /이미 응답했습니다|You've already responded/i.test(txt),
  confirmation: /응답이 기록되었습니다|response has been recorded/i.test(txt),
  editLink: !!document.querySelector('a[href*="edit2="]') || /응답 수정|Edit your response/.test(txt),
  items};"""


def state(tid, timeout=30):
    return poll(tid, "if (!document.body || !/forms|accounts/.test(location.host + location.pathname)) return null;"
                     "if (document.readyState !== 'complete') return null;" + STATE, timeout)


def press_button(tid, label):
    r = js(tid, f"""const b = [...document.querySelectorAll('[role=button]')].filter(e => __vis(e) && e.innerText.trim() === {json.dumps(label)})[0];
      if (!b) return 'NOTFOUND'; __press(b); return 'OK';""")
    if r != "OK":
        raise RuntimeError(f"button {label}: {r}")


def next_page(tid, timeout=15):
    """Press 다음; return new state, or raise with the validation errors."""
    before = state(tid)
    sig = [x["title"] for x in before["items"]]
    press_button(tid, "다음" if "다음" in before["buttons"] else "Next")
    end = time.time() + timeout
    while time.time() < end:
        time.sleep(1)
        st = state(tid)
        if [x["title"] for x in st["items"]] != sig:
            return st
        errs = [f"{x['title']}: {x['error']}" for x in st["items"] if x["error"]]
        if errs:
            raise RuntimeError("다음 막힘 — " + "; ".join(errs)[:300])
    raise RuntimeError("다음 눌러도 페이지가 안 바뀜")


FILL = r"""
const A = %s, norm = s => (s || '').replace(/[\s*:·()\[\]]/g, '').toLowerCase();
const out = [];
[...document.querySelectorAll('div[role=listitem]')].filter(__vis).forEach(it => {
  const h = it.querySelector('[role=heading]'); if (!h) return;
  const t = norm(h.innerText); const key = Object.keys(A).find(k => t === norm(k)) || Object.keys(A).find(k => t.includes(norm(k)));
  if (!key) return;
  let v = A[key], st = 'filled';
  const radios = [...it.querySelectorAll('[role=radio]')], checks = [...it.querySelectorAll('[role=checkbox]')];
  const date = it.querySelector('input[type=date]');
  const txts = [...it.querySelectorAll('input[type=text],input[type=email],input[type=number],input[type=tel],input[type=url],input:not([type]),textarea')].filter(__vis);
  const lab = e => (e.getAttribute('data-value') || e.getAttribute('data-answer-value') || e.getAttribute('aria-label') || '').trim();
  if (v && typeof v === 'object' && !Array.isArray(v) && v.file) st = 'file';
  else if (/파일 추가|Add file/.test(it.innerText)) st = 'file';
  else if (date) st = __setv(date, String(v)) ? 'filled' : 'mismatch';
  else if (radios.length) { const r = radios.find(e => lab(e) === String(v)) || radios.find(e => lab(e).includes(String(v)));
    if (!r) st = 'no-option'; else if (r.getAttribute('aria-checked') !== 'true') __press(r); }
  else if (checks.length) { const want = Array.isArray(v) ? v.map(String) : [String(v)];
    for (const w of want) { const cbx = checks.find(e => lab(e) === w) || checks.find(e => lab(e).includes(w));
      if (!cbx) { st = 'no-option'; continue; } if (cbx.getAttribute('aria-checked') !== 'true') __press(cbx); } }
  else if (it.querySelector('[role=listbox]')) st = 'dropdown';
  else if (txts.length === 3 && /^\d{4}-\d{2}-\d{2}$/.test(String(v))) { const p = String(v).split('-'); txts.forEach((e, i) => __setv(e, p[i])); }
  else if (txts.length) st = __setv(txts[0], String(v)) ? 'filled' : 'mismatch';
  else st = 'no-input';
  out.push({key, title: h.innerText.replace(/\s*\*\s*$/, '').trim(), status: st});
});
return out;"""


def fill_page(tid, answers):
    """Fill visible items whose title matches an answers key (exact, then substring)."""
    res = js(tid, FILL % json.dumps(answers, ensure_ascii=False)) or []
    for r in res:  # dropdowns need open → wait → choose
        if r["status"] == "dropdown":
            v = answers[r["key"]]
            js(tid, f"""const it = [...document.querySelectorAll('div[role=listitem]')].filter(e => __vis(e) && e.innerText.includes({json.dumps(r['title'])}))[0];
              __press(it.querySelector('[role=listbox]')); return 1;""")
            time.sleep(0.8)
            ok = js(tid, f"""const o = [...document.querySelectorAll('[role=option]')].filter(e => __vis(e) && (e.getAttribute('data-value') === {json.dumps(v)}))[0];
              if (!o) return false; __press(o); return true;""")
            time.sleep(0.5)
            r["status"] = "filled" if ok else "no-option"
    return res
