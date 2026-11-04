#!/usr/bin/env python3
"""보낸 메일의 수신자·시각과 첨부 해시를 실제 Gmail에서 대조한다. 메일을 보내지 않는다.
python3 gmail_sent_verify.py "<검색어>" --subject <제목 일부> --file <로컬 첨부> [--profile "Profile 1"] [--shot x.png]
마지막 줄 RESULT: MATCH | MISMATCH | NOT_FOUND. Apple 이벤트라 tmux -L gh 세션에서 돌린다."""
import argparse, hashlib, json, os, sys, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chromectl as c
a = argparse.ArgumentParser()
a.add_argument('query'); a.add_argument('--subject', required=True); a.add_argument('--file', required=True)
a.add_argument('--profile', default='Profile 1'); a.add_argument('--shot')
a = a.parse_args()
local = hashlib.sha256(open(a.file, 'rb').read()).hexdigest()
t = c.new_tab('https://mail.google.com/mail/u/0/#search/' + urllib.parse.quote_plus(a.query), a.profile)
res = {'localSha256': local}
try:
    time.sleep(6)
    ok = c.js_json(t, "const r=[...document.querySelectorAll('tr.zA')].find(r=>r.offsetParent&&r.innerText.includes(%s)); if(!r) return false; r.click(); return true" % json.dumps(a.subject))
    if not ok:
        print(json.dumps(res, ensure_ascii=False)); print('RESULT: NOT_FOUND'); sys.exit(1)
    time.sleep(5)
    res['message'] = c.js_json(t, "const ms=[...document.querySelectorAll('[data-message-id]')];const m=ms[ms.length-1];return {id:m.getAttribute('data-legacy-message-id'),when:(m.querySelector('.g3')||{}).title,to:[...m.querySelectorAll('.hb [email]')].map(e=>e.getAttribute('email')),atts:[...m.querySelectorAll('[download_url]')].map(e=>decodeURIComponent(e.getAttribute('download_url').split(':')[1]))}")
    c.js_json(t, """window.__h=null;const ms=[...document.querySelectorAll('[data-message-id]')];const a=ms[ms.length-1].querySelector('[download_url]');const u=a.getAttribute('download_url').split(':').slice(2).join(':');
fetch(u,{credentials:'include'}).then(r=>r.arrayBuffer()).then(b=>crypto.subtle.digest('SHA-256',b).then(d=>{window.__h={len:b.byteLength,sha:[...new Uint8Array(d)].map(x=>x.toString(16).padStart(2,'0')).join('')}})).catch(e=>{window.__h={err:String(e)}});return 1""")
    h = None
    for _ in range(60):
        time.sleep(1)
        h = c.js_json(t, "return window.__h")
        if h: break
    res['sent'] = h
    if a.shot: c.shot(t, a.shot)
finally:
    c.close_tab(t)
print(json.dumps(res, ensure_ascii=False, indent=1))
print('RESULT:', 'MATCH' if (h or {}).get('sha') == local else 'MISMATCH')
