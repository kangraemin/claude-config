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
    : checks.length ? checks.some(e => e.getAttribute('aria-checked') === 'true')
    : lb ? [...lb.querySelectorAll('[role=option][aria-selected=true]')].some(e => e.getAttribute('data-value')) || txts.some(e => e.value)
    : !!it.querySelector('[role=list] [role=listitem][data-tooltip]') || txts.some(e => e.value);  // 파일 칸: 이미 올린 파일 칩(응답 수정)
  const err = ([...it.querySelectorAll('[role=alert]')].filter(__vis)[0] || {}).innerText || '';
  return {i, title, required: req, kind, options: opts.slice(0, 30), answered, error: err.trim()};
}).filter(x => x.title || x.kind !== 'section');
return {url: location.href, title: document.title, account: acct, buttons: btn,
  needsLogin: /accounts\.google\.com/.test(location.host) || /로그인해야|Sign in to continue/.test(txt),
  closed: /더 이상 응답을 받지 않습니다|no longer accepting responses/i.test(txt),
  alreadyResponded: /이미 응답했습니다|You've already responded/i.test(txt),
  confirmation: /응답이 기록되었습니다|response has been recorded/i.test(txt) || /formResponse/.test(location.href),
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
// 11/10 도서관의 날: '…을(를) 내 응답에 포함할 이메일로 기록합니다.' 필수 체크박스는 listitem 밖에 있어 '다음'이 조용히 막힌다
[...document.querySelectorAll('[role=checkbox]')].filter(e => __vis(e) && !e.closest('div[role=listitem]')
  && /이메일로 기록|as the email to be included|Record .* as the email/i.test(e.getAttribute('aria-label') || '')).forEach(e => {
  if (e.getAttribute('aria-checked') !== 'true') __press(e);
  out.push({key: '__record_email', title: e.getAttribute('aria-label'), status: 'filled'});
});
[...document.querySelectorAll('div[role=listitem]')].filter(__vis).forEach(it => {
  const h = it.querySelector('[role=heading]'); if (!h) return;
  const t = norm(h.innerText); const key = Object.keys(A).find(k => t === norm(k)) || Object.keys(A).filter(k => t.includes(norm(k))).sort((a, b) => norm(b).length - norm(a).length)[0];
  if (!key) return;
  let v = A[key], st = 'filled';
  const radios = [...it.querySelectorAll('[role=radio]')], checks = [...it.querySelectorAll('[role=checkbox]')];
  const date = it.querySelector('input[type=date]');
  const txts = [...it.querySelectorAll('input[type=text],input[type=email],input[type=number],input[type=tel],input[type=url],input:not([type]),textarea')].filter(__vis);
  const lab = e => (e.getAttribute('data-value') || e.getAttribute('data-answer-value') || e.getAttribute('aria-label') || '').trim();
  if (v && typeof v === 'object' && !Array.isArray(v) && v.grid !== undefined) {  // 11/20 Nitto: 객관식 그리드 {"grid": "열"} 또는 {"grid": {"행 일부": "열"}}
    st = 'grid';
    for (const g of it.querySelectorAll('[role=radiogroup]')) { const row = g.getAttribute('aria-label') || '';
      const col = typeof v.grid === 'string' ? v.grid : (Object.entries(v.grid).find(([k]) => row.includes(k)) || [])[1];
      const r = col && [...g.querySelectorAll('[role=radio]')].find(e => e.getAttribute('data-value') === col);
      if (!r) { st = 'no-option'; continue; } if (r.getAttribute('aria-checked') !== 'true') __press(r); } }
  else if (v && typeof v === 'object' && !Array.isArray(v) && v.file) st = 'file';
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
            ok = False
            for _ in range(4):  # 펼친 목록이 늦게 뜨거나 __vis가 false로 나오는 일이 있다(10/28 제주 거주지역) → 글자로도 찾고 몇 번 더 본다
                time.sleep(0.8)
                ok = js(tid, f"""const os = [...document.querySelectorAll('[role=option]')].filter(e => e.getAttribute('data-value') === {json.dumps(v)} || e.innerText.trim() === {json.dumps(v)});
                  const o = os.filter(__vis)[0] || os[os.length - 1]; if (!o) return false; __press(o); return true;""")
                if ok:
                    break
            time.sleep(0.5)
            chosen = f"""const it = [...document.querySelectorAll('div[role=listitem]')].filter(e => __vis(e) && e.innerText.includes({json.dumps(r['title'])}))[0];
              const s = it && it.querySelector('[role=listbox] [aria-selected=true]'); return !!s && (s.getAttribute('data-value') === {json.dumps(v)} || s.innerText.trim() === {json.dumps(v)});"""
            if ok and not js(tid, chosen):
                # 11/13 산림복지 수상자 폼: 숨은 탭에서 합성 클릭이 선택을 못 남김 → 탭을 앞으로 올려 실제 마우스 클릭
                import chromectl as c
                for _ in range(3):
                    # 목록을 합성 press로 열면 옵션 클릭이 안 먹는다 → 목록 자체도 실제 클릭으로 연다(11/13 확인)
                    closed = js(tid, f"""document.querySelectorAll('[data-cdlb]').forEach(e => e.removeAttribute('data-cdlb'));
                      const it = [...document.querySelectorAll('div[role=listitem]')].filter(e => __vis(e) && e.innerText.includes({json.dumps(r['title'])}))[0];
                      const lb = it.querySelector('[role=listbox]'); lb.setAttribute('data-cdlb', '1'); return lb.getAttribute('aria-expanded') !== 'true';""")
                    if closed:
                        try:
                            c.rclick(tid, sel="[data-cdlb='1']")
                        except RuntimeError:
                            pass
                    time.sleep(1.5)
                    try:
                        c.rclick(tid, sel=f"[role=option][data-value={json.dumps(v)}]")
                    except RuntimeError:
                        pass
                    time.sleep(0.8)
                    if js(tid, chosen):
                        break
                ok = bool(js(tid, chosen))
            r["status"] = "filled" if ok else "no-option"
    # 11/14 산림복지 국민제안(Profile 15): 숨은 탭에서 라디오·체크박스 합성 press가 선택으로 안 남음 → 안 켜진 선택지만 실제 마우스 클릭
    TAG = r"""const A = %s, norm = s => (s || '').replace(/[\s*:·()\[\]]/g, '').toLowerCase();
      const lab = e => (e.getAttribute('data-value') || e.getAttribute('data-answer-value') || e.getAttribute('aria-label') || '').trim();
      document.querySelectorAll('[data-cdrc]').forEach(e => e.removeAttribute('data-cdrc')); let n = 0;
      [...document.querySelectorAll('div[role=listitem]')].filter(__vis).forEach(it => {
        const h = it.querySelector('[role=heading]'); if (!h) return; const t = norm(h.innerText);
        const key = Object.keys(A).find(k => t === norm(k)) || Object.keys(A).filter(k => t.includes(norm(k))).sort((a, b) => norm(b).length - norm(a).length)[0]; if (!key) return;
        const opts = [...it.querySelectorAll('[role=radio],[role=checkbox]')]; if (!opts.length) return;
        const gv = A[key]; if (gv && typeof gv === 'object' && !Array.isArray(gv) && gv.grid !== undefined) {
          for (const g of it.querySelectorAll('[role=radiogroup]')) { const row = g.getAttribute('aria-label') || '';
            const col = typeof gv.grid === 'string' ? gv.grid : (Object.entries(gv.grid).find(([k]) => row.includes(k)) || [])[1];
            const o = col && [...g.querySelectorAll('[role=radio]')].find(e => e.getAttribute('data-value') === col);
            if (o && o.getAttribute('aria-checked') !== 'true') o.setAttribute('data-cdrc', String(n++)); }
          return; }
        if (gv && typeof gv === 'object' && !Array.isArray(gv)) return;
        const want = Array.isArray(A[key]) ? A[key].map(String) : [String(A[key])];
        for (const w of want) { const o = opts.find(e => lab(e) === w) || opts.find(e => lab(e).includes(w));
          if (o && o.getAttribute('aria-checked') !== 'true') { o.setAttribute('data-cdrc', String(n++)); } }
      }); return n;"""
    for _ in range(3):
        time.sleep(0.6)
        n = js(tid, TAG % json.dumps(answers, ensure_ascii=False)) or 0
        if not n:
            break
        import chromectl as c
        for i in range(n):
            try:
                c.rclick(tid, sel=f"[data-cdrc='{i}']")
            except RuntimeError:
                pass
            time.sleep(0.5)
    for r in res:  # 그리드: 모든 행이 켜졌는지 확인
        if r["status"] == "grid":
            done = js(tid, f"""const it = [...document.querySelectorAll('div[role=listitem]')].filter(e => __vis(e) && e.innerText.includes({json.dumps(r['title'])}))[0];
              return !!it && [...it.querySelectorAll('[role=radiogroup]')].every(g => g.querySelector('[role=radio][aria-checked=true]'));""")
            r["status"] = "filled" if done else "mismatch"
    if any(r["key"] == "__record_email" for r in res):
        # 11/10 도서관의 날: 숨은 탭에서는 이 체크박스가 합성 이벤트로 안 켜진다 → 탭을 앞으로 올려 실제 마우스 클릭
        sel = "[role=checkbox][aria-label*='이메일로 기록']"
        chk = "return [...document.querySelectorAll(\"[role=checkbox]\")].filter(e => /이메일로 기록|as the email/i.test(e.getAttribute('aria-label') || '')).every(e => e.getAttribute('aria-checked') === 'true')"
        for _ in range(3):
            time.sleep(0.8)
            if js(tid, chk):
                break
            import chromectl as c
            c.rclick(tid, sel=sel)
        else:
            time.sleep(0.8)
        for r in res:
            if r["key"] == "__record_email" and not js(tid, chk):
                r["status"] = "mismatch"
    return res


def upload_picker(tid, paths, item_title=None, timeout=90):
    """구글폼 파일 칸: '파일 추가' → Google Picker iframe(docs.google.com, 같은 출처)의 input[type=file]에
    DataTransfer로 여러 파일을 한 번에 넣는다(Codex 불필요, 11/16 광명 로고 3개 성공).
    돌려줌: 폼 숨은 값에 붙은 파일 이름 목록. 제출은 안 누른다."""
    import base64, mimetypes, os
    import chromectl as c
    sel = f"e.innerText.includes({json.dumps(item_title)})" if item_title else "[...e.querySelectorAll('[role=button]')].some(b=>b.innerText.includes('파일 추가'))"
    c.front(tid)
    ok = c.js_json(tid, f"""const it=[...document.querySelectorAll('div[role=listitem]')].filter(e=>{sel})[0]; if(!it) return false;
      const b=[...it.querySelectorAll('[role=button]')].find(e=>e.innerText.includes('파일 추가')); if(!b) return false; b.click(); return true""")
    if not ok:
        raise RuntimeError("파일 추가 버튼 없음")
    for _ in range(20):
        time.sleep(1)
        if c.js_json(tid, "const f=[...document.querySelectorAll('iframe')].find(x=>x.src.includes('picker'));return !!(f&&f.contentDocument&&f.contentDocument.querySelector('input[type=file]'))"):
            break
    else:
        raise RuntimeError("Picker 파일 칸 안 뜸")
    c.run_js(tid, "window.__cf=[];1")
    for p in paths:
        b64 = base64.b64encode(open(p, "rb").read()).decode()
        mime = mimetypes.guess_type(p)[0] or ("application/haansofthwpx" if p.endswith(".hwpx") else "application/octet-stream")
        c.run_js(tid, "window.__cu=[];1")
        for i in range(0, len(b64), 300000):
            c.run_js(tid, f"window.__cu.push({c.q(b64[i:i+300000])});1", 60)
        c.run_js(tid, f"""(()=>{{const s=atob(window.__cu.join(''));window.__cu=null;const u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);
          window.__cf.push(new File([u],{c.q(os.path.basename(p))},{{type:{c.q(mime)}}}));return 1}})()""", 120)
    c.run_js(tid, """(()=>{const f=[...document.querySelectorAll('iframe')].find(x=>x.src.includes('picker'));const W=f.contentWindow,i=f.contentDocument.querySelector('input[type=file]');
      const dt=new W.DataTransfer();window.__cf.forEach(x=>dt.items.add(new W.File([x],x.name,{type:x.type})));i.files=dt.files;
      i.dispatchEvent(new W.Event('change',{bubbles:true}));window.__cf=null;return 1})()""", 60)
    names = []
    end = time.time() + timeout
    while time.time() < end:
        time.sleep(3)
        names = c.js_json(tid, """const h=[...document.querySelectorAll('input[type=hidden]')].find(x=>{if(x.name==='partialResponse'||!x.value.startsWith('[[['))return false;try{const v=JSON.parse(x.value);return typeof v[0][0][0]==='string'&&typeof v[0][0][1]==='string'}catch(e){return false}});return h?JSON.parse(h.value)[0].map(x=>x[1]):[]""") or []
        if len(names) >= len(paths):
            break
    return names
