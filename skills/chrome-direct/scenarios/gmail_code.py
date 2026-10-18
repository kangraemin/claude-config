#!/usr/bin/env python3
"""[읽기] 가입·제출 중 온 이메일 인증번호/인증 링크 읽기 (받은편지함+스팸).
가장 최근 메일 1통을 열어 본문에서 코드(또는 --link 패턴의 URL)를 뽑아 `CODE <값>` / `LINK <url>` 로 출력.

  gmail_code.py "from:enables.tech 인증번호" --newer 20m
  gmail_code.py "from:dacon.io" --link "verify_mail" --newer 1h
"""
import re

from _common import ACCOUNT, emit, parser, run, tab
from _gmail import open_row, search, search_url

ap = parser(__doc__)
ap.add_argument("query", help="Gmail 검색어 (보낸사람·제목 키워드)")
ap.add_argument("--newer", default="30m", help="Gmail newer_than 값: 30m, 2h, 1d")
ap.add_argument("--link", help="코드 대신 이 문자열이 든 URL을 찾음")
ap.add_argument("--pattern", default=r"(?:인증번호|인증 ?코드|코드|code)\D{0,20}(\d{4,8})", help="코드 정규식 (그룹1)")
ap.add_argument("--account", default=ACCOUNT)
a = ap.parse_args()
Q = f"in:anywhere newer_than:{a.newer} {a.query}"


def main():
    with tab(search_url(Q, a.account), a) as tid:
        res = search(tid, Q, a.account, 5)
        if not res["rows"]:
            emit({"query": Q}, "NONE", "메일 없음 (아직 안 왔거나 --newer 늘리기)")
            raise SystemExit(1)
        row = res["rows"][0]
        if a.link:
            th = open_row(tid, 1)
            hrefs = c_links(tid)
            url = next((h for h in hrefs if a.link in h), None)
            emit({"subject": row["subject"], "date": row["date"]}, "OK" if url else "NONE")
            if url:
                print(f"LINK {url}")
            raise SystemExit(0 if url else 1)
        m = re.search(a.pattern, row["subject"] + " " + row["snippet"], re.I)
        if not m:
            th = open_row(tid, 1)
            m = re.search(a.pattern, " ".join(x["body"] for x in th["messages"][-1:]), re.I)
        emit({"subject": row["subject"], "date": row["date"]}, "OK" if m else "NONE")
        if m:
            print(f"CODE {m.group(1)}")
        raise SystemExit(0 if m else 1)


def c_links(tid):
    from _common import js
    return js(tid, "return [...document.querySelectorAll('div.adn .a3s a[href]')].filter(__vis).map(a => a.href)") or []


run(main, a, f"READ ONLY. Gmail {a.account} 받은편지함·스팸함에서 `{Q}` 로 가장 최근 메일 1통을 열고 "
    + (f"본문의 '{a.link}'가 든 링크 URL만 `LINK <url>` 한 줄로 출력 (링크 클릭 금지)." if a.link else "본문의 인증번호만 `CODE <번호>` 한 줄로 출력."))
