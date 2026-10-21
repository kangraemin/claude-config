#!/usr/bin/env python3
"""[조회] LINE Creators Market 스티커 심사 상태를 본다(로그아웃이면 로그인부터).

  line_status.py [sticker_id ...]     # 생략하면 Manage Items 목록 전체

- 로그인은 line_sticker_upload.login 재사용: 인증번호(PIN)를 텔레그램으로 보내고 폰 LINE 앱 입력을 3분 기다린다.
- 읽기만 한다(Release·Request 버튼은 누르지 않음).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import line_sticker_upload as U  # noqa: E402

c = U.c


def main():
    t = c.new_tab("https://creator.line.me/my/", profile="Profile 1")
    try:
        time.sleep(5)
        root = U.my_root(t)
        if not root and U.jj(t, "return !!document.querySelector('input[name=tid]')"):
            U.login(t)
            c.goto(t, "https://creator.line.me/my/")
            time.sleep(5)
            root = U.my_root(t)
        if not root:
            print("RESULT: BLOCKED 로그인 실패(폰 인증 시간 초과?)")
            return
        ids = sys.argv[1:]
        if not ids:
            c.goto(t, f"{U.BASE}{root}/sticker/")
            time.sleep(5)
            ids = U.jj(t, "return [...document.querySelectorAll('[data-test=product-info-card]')].map(a=>a.dataset.productId)") or []
        out = []
        for sid in ids:
            st, body = U.status(t, root, sid)
            title = U.js(t, "document.querySelector('h2,h1')?.innerText||''")
            out.append(f"{sid} {title.strip()[:40]} {' '.join(st)}")
            print(out[-1])
        print("RESULT: OK", " | ".join(out))
    finally:
        c.close_tab(t)


if __name__ == "__main__":
    main()
