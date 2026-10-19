#!/usr/bin/env python3
"""[읽기] 노션 페이지 트리(본문+이미지)를 로컬 마크다운 책(INDEX.md + part<N>/NN-제목.md + img/)으로 뽑기.

  notion_export.py <page_id> <out_dir> [--refresh] [--gap 2.5] [--max-img 0]

- 로그인된 Chrome(Profile 1) 탭에서 노션 내부 API(/api/v3 syncRecordValues·getSignedFileUrls)를 부른다.
- 왜 화면 조작인가: 공식 통합 토큰은 연동에 공유된 페이지만 보이고, 이미지 파일은 HttpOnly 로그인 쿠키가 있어야 받힌다.
- 멱등: 트리는 <out_dir>/.notion_export/tree.json 캐시(--refresh로 다시 받음), 이미지는 이미 받은 파일은 건너뛴다.
  이미지 서버가 연속 ~300장 뒤 막으므로 1장씩 --gap 초 간격, 연속 5번 실패하면 멈추고 다음 실행에서 이어 받는다.
- 사전 조건: Profile 1 크롬에서 app.notion.com 로그인(로그아웃이면 BLOCKED. 이메일 코드 로그인 → gmail_code.py "from:notion").
"""
import base64, json, subprocess, sys, time
from pathlib import Path

from _common import Blocked, c, emit, parser, poll, run, tab

HERE = Path(__file__).resolve().parent / "notion_export_js"
ap = parser(__doc__)
ap.add_argument("page_id")
ap.add_argument("out_dir")
ap.add_argument("--refresh", action="store_true", help="트리 캐시 무시하고 다시 받기")
ap.add_argument("--gap", type=float, default=2.5, help="이미지 사이 대기(초)")
ap.add_argument("--max-img", type=int, default=0, help="이번 실행에서 받을 이미지 수 상한(0=전부)")
a = ap.parse_args()
OUT = Path(a.out_dir).expanduser().resolve()
CACHE = OUT / ".notion_export"


def pid(s):
    s = s.replace("-", "")[-32:]
    return f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"


def pull(tid, var):
    n = int(c.run_js(tid, f"window.{var}.length", 20))
    return "".join(c.run_js(tid, f"window.{var}.slice({i},{i + 200000})", 30) for i in range(0, n, 200000))


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    with tab(f"https://app.notion.com/p/{a.page_id.replace('-', '')}", a) as tid:
        time.sleep(4)
        if "/login" in c.run_js(tid, "location.href"):
            raise Blocked("노션 로그아웃 — Profile 1에서 app.notion.com 로그인 필요")
        tree_f = CACHE / "tree.json"
        if a.refresh or not tree_f.exists():
            c.run_js(tid, f"window.__ROOT={json.dumps(pid(a.page_id))};window.__done=false;window.__err=null;" + (HERE / "tree.js").read_text(), 30)
            poll(tid, "return window.__done ? true : null", timeout=600, every=2)
            if c.run_js(tid, "String(window.__err)") != "null":
                raise RuntimeError(c.run_js(tid, "window.__err"))
            tree_f.write_text(pull(tid, "__exp"))
        d = json.loads(tree_f.read_text())
        subprocess.run([sys.executable, str(HERE / "build.py"), str(tree_f), str(OUT), str(CACHE / "imgmap.json")], check=True)
        imgmap = json.loads((CACHE / "imgmap.json").read_text())
        todo = [i for i in d["imgs"] if not (OUT / imgmap[i["id"]]).exists()]
        if a.max_img:
            todo = todo[:a.max_img]
        got, fails = 0, 0
        for k in range(0, len(todo), 50):
            batch = todo[k:k + 50]
            req = json.dumps([{"url": i["src"], "permissionRecord": {"table": "block", "id": i["id"], "spaceId": i["space"]}} for i in batch])
            c.run_js(tid, "window.__sg=null;fetch('/api/v3/getSignedFileUrls',{method:'POST',headers:{'content-type':'application/json'},"
                          f"body:JSON.stringify({{urls:{req}}})}}).then(r=>r.json()).then(j=>window.__sg=JSON.stringify(j.signedUrls))", 30)
            signed = json.loads(poll(tid, "return window.__sg", timeout=30) and c.run_js(tid, "window.__sg"))
            for im, u in zip(batch, signed):
                c.run_js(tid, f"window.__im=null;fetch({json.dumps(u)},{{credentials:'include'}}).then(r=>{{if(!r.ok)throw r.status;return r.blob()}})"
                              ".then(b=>new Promise(s=>{const f=new FileReader();f.onload=()=>s(f.result);f.readAsDataURL(b)})).then(x=>window.__im=x).catch(e=>window.__im='ERR '+e)")
                poll(tid, "return window.__im ? true : null", timeout=40, every=0.5)
                data = c.run_js(tid, "window.__im", 60)
                if data.startswith("ERR"):
                    fails += 1
                    if fails >= 5:
                        break
                else:
                    fails = 0
                    dst = OUT / imgmap[im["id"]]
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(base64.b64decode(data.split(",", 1)[1]))
                    got += 1
                time.sleep(a.gap)
            if fails >= 5:
                break
        left = sum(1 for i in d["imgs"] if not (OUT / imgmap[i["id"]]).exists())
        emit({"pages": len(d["pages"]), "images": len(d["imgs"]), "downloaded_now": got, "images_left": left, "out": str(OUT)},
             "OK" if left == 0 else "PARTIAL", "" if left == 0 else "이미지 서버 스로틀 — 몇 분 뒤 같은 명령 다시 실행")


run(main, a, f"노션 페이지 {a.page_id} 트리를 {a.out_dir}에 마크다운으로 내보내기")
