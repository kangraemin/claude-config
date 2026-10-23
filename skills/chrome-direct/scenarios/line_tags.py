#!/usr/bin/env python3
"""[설정] LINE Creators Market 스티커 자동 추천 태그(Tag Settings)를 세트마다 넣는다.

  line_tags.py ids.json [--only 48516185,48519670] [--dry-run]

- ids.json: {"<sticker id>": [[태그 id, ...] x 스티커 수], ...}. 태그 id는 /my/api/auto_suggest_tags?product_type=sticker 목록의 id(c174 등).
- 세트마다 GET 으로 지금 값을 읽고, 다르면 PUT 으로 전체를 덮어쓴 뒤 다시 GET 으로 확인한다(멱등).
- 로그인은 line_sticker_upload.login 재사용(PIN 텔레그램).
- 왜 API 직접 호출인가: 편집 화면(/sticker/<id>/tag#/NN)은 체크박스 한 칸씩 눌러야 하고 24장×9개라 느리다. 화면도 같은 API를 쓴다.
- 함정:
  - 한 장 최대 9개. 정해진 목록 밖 태그는 못 넣는다. 승인 뒤 자동으로 붙는 태그는 보거나 고칠 수 없다.
  - 태그도 심사를 거친다("Auto-suggest tags must match your stickers"). 글자·그림과 뜻이 맞는 것만 넣는다.
  - Waiting for Review·In Review 세트는 편집이 닫혀 있어 PUT이 실패한다. 판매 중·Processing·Ready for tagging 세트만 된다.
  - GET 응답 앞에 )]}' 줄이 붙는다(JSON 하이재킹 방지). 떼고 파싱한다.
  - 판매 중 세트는 태그를 바꾸면 상태가 Editing 이 되고 상세 화면 Request(업데이트 심사)를 눌러야 반영된다. 이 스크립트가 누른다(--dry-run 제외).
  - PUT 헤더: X-Requested-With XMLHttpRequest, X-XSRF-TOKEN = decodeURIComponent(쿠키 XSRF-TOKEN). 본문 [{type:'01',tag_ids:[...]}, ...].
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import line_sticker_upload as U  # noqa: E402
from line_add_language import request  # noqa: E402

c = U.c

GET = r"""(()=>{window.__tg=null;fetch(location.pathname.split('/sticker')[0].replace(/\/$/,'')+'/api/sticker/%s/auto_suggest_tags',{credentials:'include'})
  .then(r=>r.text().then(b=>__tg=[r.status,JSON.parse(b.replace(/^\)\]\}',?\s*/,''))])).catch(e=>__tg=[0,String(e)]);return 1})()"""
PUT = r"""(()=>{window.__tp=null;const x=decodeURIComponent((document.cookie.match(/XSRF-TOKEN=([^;]+)/)||[])[1]||'');
  fetch(location.pathname.split('/sticker')[0].replace(/\/$/,'')+'/api/sticker/%s/auto_suggest_tags',{method:'PUT',credentials:'include',
   headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest','X-XSRF-TOKEN':x},body:JSON.stringify(%s)})
  .then(r=>r.text().then(b=>__tp=[r.status,b])).catch(e=>__tp=[0,String(e)]);return 1})()"""


def wait(t, var):
    for _ in range(20):
        time.sleep(0.5)
        v = U.jj(t, f"return window.{var}")
        if v:
            return v
    return [0, "timeout"]


def current(t, sid):
    U.js(t, GET % sid)
    st, j = wait(t, "__tg")
    if st != 200 or not isinstance(j, dict):
        return None
    return {r["type"]: sorted(r["tag_ids"]) for r in j.get("update_request") or []}


def ask(t, root, sid, dry=False):
    """판매 중 세트가 Editing 이면 Request 를 누른다. 반환: 'requested' | 'no-request' | 'would-request'."""
    c.goto(t, f"{U.BASE}{root}/sticker/{sid}")
    time.sleep(6)
    if "Please request a review" not in (U.js(t, "document.body.innerText") or ""):
        return "no-request"
    if dry:
        return "would-request"
    request(t, root, sid)
    c.goto(t, f"{U.BASE}{root}/sticker/{sid}")
    time.sleep(6)
    return "requested" if "Please request a review" not in U.js(t, "document.body.innerText") else "request-fail"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids")
    ap.add_argument("--only", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sets = json.load(open(a.ids))
    if a.only:
        sets = {k: v for k, v in sets.items() if k in a.only.split(",")}
    t = c.new_tab(U.BASE, profile="Profile 1")
    res = []
    try:
        time.sleep(5)
        root = U.my_root(t)
        if not root and U.jj(t, "return !!document.querySelector('input[name=tid]')"):
            U.login(t)
            c.goto(t, U.BASE)
            time.sleep(5)
            root = U.my_root(t)
        if not root:
            print("RESULT: BLOCKED 로그인 실패")
            return
        for sid, rows in sets.items():
            want = [{"type": f"{i:02d}", "tag_ids": ids[:9]} for i, ids in enumerate(rows, 1)]
            c.goto(t, f"{U.BASE}{root}/sticker/{sid}/tag")
            time.sleep(4)
            now = current(t, sid)
            if now is None:
                print(sid, "읽기 실패(편집 닫힘?)")
                res.append(f"{sid}:closed")
                continue
            if now == {w["type"]: sorted(w["tag_ids"]) for w in want}:
                print(sid, "이미 같음", ask(t, root, sid, a.dry_run))
                res.append(f"{sid}:same")
                continue
            if a.dry_run:
                print(sid, f"바꿀 것 {len(now)}장 → {len(want)}장")
                res.append(f"{sid}:would")
                continue
            U.js(t, PUT % (sid, json.dumps(want, ensure_ascii=False)))
            st, body = wait(t, "__tp")
            after = current(t, sid)
            ok = st == 200 and after == {w["type"]: sorted(w["tag_ids"]) for w in want}
            print(sid, "PUT", st, body.split("\n")[-1][:60], "확인", "OK" if ok else after, ask(t, root, sid) if ok else "")
            res.append(f"{sid}:{'ok' if ok else 'fail'}")
        print("RESULT: " + ("OK " if all(r.split(":")[1] in ("ok", "same", "would") for r in res) else "PARTIAL ") + " ".join(res))
    finally:
        c.close_tab(t)


if __name__ == "__main__":
    main()
