"""[읽기] 보낸 메일의 첨부를 Gmail에서 내려받아 SHA256을 로컬 파일과 대조 (제출 증거 게이트 --stage sent용).

  gmail_att_hash.py <thread id> --expect 제안1.hwpx [--expect 제안2.pdf] [--save-dir <폴더>]

<thread id>: gmail_search.py --open N 결과 thread.url 끝의 id (예: QgrcJHsNj...).
메일 화면의 view=att 링크를 fetch(credentials)로 받아 base64로 꺼낸다. 첨부 이름은 --expect 파일 이름 순서와 짝짓지 않고
해시로 맞춘다. 전부 맞으면 RESULT: OK, 하나라도 안 맞으면 RESULT: MISMATCH(exit 1). 2026-10-28 강릉 제출에서 처음 씀.
"""
import base64
import hashlib
import sys
from pathlib import Path

from _common import emit, js, parser, poll, run, tab

ap = parser(__doc__)
ap.add_argument("thread")
ap.add_argument("--expect", action="append", default=[], help="대조할 로컬 파일 (여러 개면 반복)")
ap.add_argument("--save-dir", help="내려받은 첨부를 저장할 폴더")
ap.add_argument("--account", default="0", help="mail/u/<n>")
ap.add_argument("--expand", action="store_true", help="스레드의 접힌 메일을 모두 펼친 뒤 받는다(받은 메일 스레드는 앞 메일이 접혀 첨부 링크가 없음)")
ap.add_argument("--label", default="sent", help="주소 라벨(sent|inbox|all). 스레드 id만 맞으면 열린다")
a = ap.parse_args()

FETCH = """window.__d=[];const hs=[...new Set([...document.querySelectorAll('a[href*="view=att"]')].map(x=>x.href))];
window.__n=hs.length;hs.forEach((h,k)=>fetch(h.replace('disp=inline','disp=safe'),{credentials:'include'}).then(r=>r.arrayBuffer())
 .then(b=>{let s='',u=new Uint8Array(b);for(let i=0;i<u.length;i+=32768)s+=String.fromCharCode.apply(null,u.subarray(i,i+32768));window.__d[k]=btoa(s)})
 .catch(e=>window.__d[k]='ERR'+e));return hs.length"""


def main():
    want = {hashlib.sha256(Path(f).read_bytes()).hexdigest(): Path(f).name for f in a.expect}
    with tab(f"https://mail.google.com/mail/u/{a.account}/#{a.label}/{a.thread}", a) as tid:
        poll(tid, "return document.querySelectorAll('a[href*=\"view=att\"]').length>0", 40)
        if a.expand:  # 접힌 메일 머리글(.kv/.kQ)을 눌러 펼치고 첨부 링크가 늘어날 때까지 기다린다
            n0 = js(tid, "return document.querySelectorAll('a[href*=\"view=att\"]').length")
            js(tid, "var b=document.querySelector('[aria-label=\"모두 펼치기\"],[aria-label=\"Expand all\"]');if(b)b.click();document.querySelectorAll('div.kv,div.kQ').forEach(function(e){e.click()});return 1")
            try:
                poll(tid, f"return new Set([...document.querySelectorAll('a[href*=\"view=att\"]')].map(x=>x.href)).size>{n0}", 30)
            except Exception as e:
                print(f"expand: no new attachments ({e})", file=sys.stderr)
        names = js(tid, "return [...document.querySelectorAll('[download_url]')].map(e=>(e.getAttribute('download_url')||'').split(':')[1])") or []
        n = js(tid, FETCH)
        poll(tid, f"return window.__d.filter(x=>x).length=={n}", 90)
        got = []
        for k in range(n):
            L = js(tid, f"return window.__d[{k}].length")
            b64 = "".join(js(tid, f"return window.__d[{k}].slice({i},{i + 400000})", 60) for i in range(0, L, 400000))
            if b64.startswith("ERR"):
                raise RuntimeError(b64[:200])
            b = base64.b64decode(b64)
            h = hashlib.sha256(b).hexdigest()
            if a.save_dir:
                Path(a.save_dir).mkdir(parents=True, exist_ok=True)
                (Path(a.save_dir) / f"downloaded_{k + 1}_{(names[k] if k < len(names) else 'att')}").write_bytes(b)
            got.append({"name": names[k] if k < len(names) else None, "bytes": len(b), "sha256": h, "matches": want.get(h)})
    ok = bool(got) and all(g["matches"] for g in got) and len({g["matches"] for g in got}) == len(want)
    emit({"thread": a.thread, "attachments": got, "expected": list(want.values())}, "OK" if ok else "MISMATCH")
    if not ok:
        sys.exit(1)


run(main, a, f"READ ONLY. Gmail 보낸 메일 {a.thread}의 첨부 파일명과 크기를 보고.")
