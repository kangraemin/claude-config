#!/usr/bin/env python3
"""[조회] LINE Creators Market 판매·통계(Sales and Statistics)를 읽는다.

  line_stats.py

- /stats/dashboard 의 이번 달 추정 매출, /stats/sticker 의 세트별 판매 시작일·누적 매출을 출력한다.
- 로그인은 line_sticker_upload.login 재사용(PIN 텔레그램). 읽기만 한다.
- 왜 화면 조작인가: Creators Market은 통계 API를 공개하지 않는다.
- 함정: 판매가 너무 적거나 전송 수가 적으면 숫자가 안 나온다(LINE 안내). 아레인지로 보낸 건 전송 수에 안 잡힌다.
"""
import os
import re
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
            print("RESULT: BLOCKED 로그인 실패")
            return
        c.goto(t, f"{U.BASE}{root}/stats/dashboard")
        time.sleep(8)
        m = re.search(r"This month's sales\s*(\S+)", U.js(t, "document.body.innerText"))
        month = m.group(1).split("(")[0] if m else "?"
        print("이번 달 추정 매출", month)
        c.goto(t, f"{U.BASE}{root}/stats/sticker")
        time.sleep(8)
        rows = U.jj(t, """return [...document.querySelectorAll('tr')].map(r=>[...r.querySelectorAll('td')].map(d=>d.innerText.trim()).filter(Boolean)).filter(r=>r.length>=3)""") or []
        for r in rows:
            print(" | ".join(r))
        print(f"RESULT: OK month={month} items={len(rows)} " + "; ".join(f"{r[0]} {r[-1]}" for r in rows))
    finally:
        c.close_tab(t)


if __name__ == "__main__":
    main()
