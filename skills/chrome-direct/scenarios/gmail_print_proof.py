#!/usr/bin/env python3
"""[읽기] 보낸 메일의 Gmail 인쇄 보기(view=pt) 원본 HTML을 받아 제출 증거 PDF로 만든다. 메일을 보내지 않는다.

  gmail_print_proof.py <web thread id> --html out.html --pdf out-proof.pdf [--mask 010-1234-5678] [--extra-html box.html]

<web thread id>: gmail_search.py --open N 결과 thread.url 끝의 id. 실제 Chrome Profile 1(remin1994)에서
메일을 열어 첨부 링크의 ik와 data-legacy-thread-id를 읽고 view=pt를 fetch(credentials)로 받는다.
--mask 값은 가운데를 ****로 바꾼다(여러 번 가능). --extra-html 내용은 </body> 앞에 붙인다(첨부 해시 상자 등).
2026-11-07 강원 톡톡 제출에서 처음 씀(GLOBALS[9]은 비어 있어 첨부 링크 ik= 로 얻음).
"""
import argparse, glob, json, os, re, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chromectl as c

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("thread"); ap.add_argument("--html", required=True); ap.add_argument("--pdf", required=True)
ap.add_argument("--mask", action="append", default=[]); ap.add_argument("--extra-html")
ap.add_argument("--profile", default="Profile 1")
a = ap.parse_args()
t = c.new_tab(f"https://mail.google.com/mail/u/0/#sent/{a.thread}", a.profile)
try:
    time.sleep(8)
    href = c.js_json(t, "const x=document.querySelector('a[href*=\"ik=\"]'); return x?x.href:''")
    m = re.search(r"ik=([0-9a-f]+)", href or "")
    th = c.js_json(t, "const e=document.querySelector('[data-legacy-thread-id]'); return e?e.getAttribute('data-legacy-thread-id'):''")
    if not (m and th):
        print("RESULT: NOT_FOUND ik/thread"); sys.exit(1)
    url = f"https://mail.google.com/mail/u/0/?ik={m.group(1)}&view=pt&search=all&permthid=thread-f:{int(th, 16)}"
    c.run_js(t, f"window.__pt=null;fetch({json.dumps(url)},{{credentials:'include'}}).then(r=>r.text()).then(x=>window.__pt=x)")
    n = 0
    for _ in range(20):
        time.sleep(1); n = c.js_json(t, "return window.__pt ? window.__pt.length : 0")
        if n: break
    html = "".join(c.js_json(t, f"return window.__pt.slice({k},{k + 20000})") for k in range(0, n, 20000))
finally:
    c.close_tab(t)
for v in a.mask:
    html = html.replace(v, v[:4] + "****" + v[-5:] if len(v) > 9 else "****")
if a.extra_html:
    box = open(a.extra_html).read()
    html = html.replace("</body>", box + "</body>") if "</body>" in html else html + box
open(a.html, "w").write(html)
B = sorted(glob.glob(os.path.expanduser("~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell")))[-1]
subprocess.run(["timeout", "90", B, "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={os.path.abspath(a.pdf)}", "file://" + os.path.abspath(a.html)], capture_output=True)
print(json.dumps({"bytes": len(html), "pdf": a.pdf, "pdfKB": os.path.getsize(a.pdf) // 1024}, ensure_ascii=False))
print("RESULT: OK")
