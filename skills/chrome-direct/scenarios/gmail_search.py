#!/usr/bin/env python3
"""[읽기] Gmail 웹 검색 결과 목록 (+선택: N번째 메일 열어 본문·첨부 읽기, 화면 캡처).

  gmail_search.py "in:sent to:jjh914@kead.or.kr"          # 보낸편지함에 이미 보냈나
  gmail_search.py "in:spam newer_than:14d" --limit 50     # 스팸함 (Gmail MCP는 스팸 못 봄)
  gmail_search.py 'in:sent subject:"[공모전접수]"' --open 1 --proof /path/x-proof.pdf
Exit 2 = 로그아웃/다른 계정 (로그인 시도 안 함).
"""
import sys

from _common import ACCOUNT, Blocked, emit, parser, run, tab
from _gmail import open_row, search, search_url
import chromectl as c

ap = parser(__doc__)
ap.add_argument("query")
ap.add_argument("--account", default=ACCOUNT)
ap.add_argument("--limit", type=int, default=30)
ap.add_argument("--open", type=int, metavar="N", help="N번째 결과를 열어 본문·첨부 읽기 (읽음 표시됨)")
ap.add_argument("--proof", help="--open 뒤 그 화면을 .png/.pdf로 저장 (제출 완료 화면용)")
a = ap.parse_args()


def main():
    with tab(search_url(a.query, a.account), a) as tid:
        res = search(tid, a.query, a.account, a.limit)
        out = {"query": a.query, "account": a.account, "count": len(res["rows"]), **res}
        if a.open:
            out["thread"] = open_row(tid, a.open)
            if a.proof:
                out["proof"] = c.shot(tid, a.proof)
        emit(out, "OK", f"{len(res['rows'])} rows")


run(main, a, f"READ ONLY. Gmail ({a.account}) 웹에서 검색어 `{a.query}` 결과를 날짜|보낸사람|제목|미리보기 한 줄로 최대 {a.limit}개 출력."
    + (f" 그다음 {a.open}번째 메일을 열어 본문·첨부 이름을 출력." if a.open else "")
    + (f" 그 화면을 {a.proof} 로 캡처 저장." if a.proof else "")
    + " 답장·삭제·보관·라벨·링크 클릭 금지.")
