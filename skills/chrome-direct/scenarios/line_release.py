#!/usr/bin/env python3
"""[제출] 승인(Approved)된 LINE 스티커를 판매 시작(Release)한다.

  line_release.py <sticker_id ...> [--submit]

- 상세 페이지 「Release」 → 확인창 OK. --submit 이 없으면 상태만 출력한다.
- 멱등: Approved 가 아니면(이미 On Sale 등) 누르지 않고 상태만 출력.
- 로그인: line_sticker_upload.login 재사용(PIN → 텔레그램).
- 정산 계좌 미등록이어도 Release 버튼은 보인다(판매 수익 정산만 막힘).
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import line_sticker_upload as U  # noqa: E402

c = U.c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--submit", action="store_true")
    a = ap.parse_args()
    t = c.new_tab("https://creator.line.me/my/", profile="Profile 1")
    res = []
    try:
        time.sleep(5)
        root = U.my_root(t)
        if not root and U.jj(t, "return !!document.querySelector('input[name=tid]')"):
            U.login(t)
            c.goto(t, "https://creator.line.me/my/")
            time.sleep(5)
            root = U.my_root(t)
        if not root:
            print("RESULT: BLOCKED 로그인 실패")
            return
        for sid in a.ids:
            st, _ = U.status(t, root, sid)
            st = " ".join(st)
            if "Approved" not in st or not a.submit:
                res.append(f"{sid}:{st}")
                continue
            U.js(t, "(()=>{const b=[...document.querySelectorAll('button,a')].find(b=>b.offsetParent&&b.innerText.trim()=='Release');if(!b)return 0;setTimeout(()=>b.click(),10);return 1})()")
            time.sleep(3)
            dlg = U.js(t, "[...document.querySelectorAll('[role=dialog],.modal,.MdDialog,div')].filter(d=>d.offsetParent&&/OK|Release/.test(d.innerText)&&d.innerText.length<600).map(d=>d.innerText).slice(-1)[0]||''")
            print("dialog:", (dlg or "")[:300].replace("\n", " / "))
            U.js(t, "(()=>{const b=[...document.querySelectorAll('button')].filter(b=>b.offsetParent&&/^(OK|Release)$/.test(b.innerText.trim()));const x=b[b.length-1];if(!x)return 0;setTimeout(()=>x.click(),10);return 1})()")
            time.sleep(5)
            st2, _ = U.status(t, root, sid)
            res.append(f"{sid}:{' '.join(st2)}")
        print("RESULT:", " | ".join(res))
    finally:
        c.close_tab(t)


if __name__ == "__main__":
    main()
