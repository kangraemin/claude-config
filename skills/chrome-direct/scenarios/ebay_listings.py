#!/usr/bin/env python3
"""[조회] eBay(호주) Seller Hub 판매 중 목록(제목·가격·수량·30일 조회수·관심·남은 시간)과 안 읽은 메시지 수.

  ebay_listings.py [--profile "Profile 1"]

- 사전 조건: Chrome에 eBay 로그인돼 있어야 한다. 로그아웃이면 BLOCKED.
  - 로그인 방법: eBay는 비번 칸을 안 주고 문자/구글만 준다 → Continue with Google → infopackplus.au 구글 로그인
    (비번 EBAY_AU_PASSWORD, 폰 구글 알림 '예'+숫자) → 맥 패스키 저장(맥 암호는 사용자). 2026-10-21 패스키 저장함.
- 왜 화면 조작인가: 개인 셀러 API 키가 없다. 표 행(tr)을 innerText 로 읽는다.
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.expanduser("~/.config/claude-accounts/personal/skills/chrome-direct"))
import chromectl as c  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--profile", default="Profile 1")
a = ap.parse_args()
t = c.new_tab("https://www.ebay.com.au/sh/lst/active", profile=a.profile)
try:
    time.sleep(8)
    if "signin" in c.js_json(t, "return location.href"):
        print("RESULT: BLOCKED 로그아웃 상태")
        sys.exit()
    rows = c.js_json(t, """return [...document.querySelectorAll('tr')].map(r=>r.innerText).filter(x=>/Buy It Now · \\d+|Auction · \\d+/.test(x))""")
    out = []
    for r in rows:
        f = [x.strip() for x in r.split("\t") if x.strip()]
        title = next((x.split("\n")[0] for x in f if re.search(r"· \d{9,}", x)), "")
        iid = (re.search(r"· (\d{9,})", r) or [None, ""])[1]
        price = (re.search(r"AU \$[\d,.]+", r) or [""])[0]
        views = (re.search(r"Views (\d+)", r) or [None, "?"])[1]
        left = f[-1] if f else ""
        nums = [x for x in f if re.fullmatch(r"\d+", x)]
        out.append({"id": iid, "title": title, "price": price, "qty": nums[0] if nums else "?", "views30": views, "left": left})
    msgs = (re.search(r"Messages \((\d+)\)", c.js_json(t, "return document.body.innerText")) or [None, "0"])[1]
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"RESULT: OK {len(out)} listings, unread messages {msgs}")
finally:
    c.close_tab(t)
