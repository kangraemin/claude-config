#!/usr/bin/env python3
"""[읽기] _radar/announce.json 에서 발표일이 지난(또는 --days 안에 오는) 공모전마다 resultHow 의 URL을 열어
'수상·결과·선정·발표'와 공모전 이름 단어, 내 이름(강래민·강*민·강○민)을 찾는다. 판정은 안 함 — 힌트만.
메일 통보형은 gmail_search.py 로 볼 쿼리를 같이 출력. 아무것도 누르지 않음.

  announce_check.py                 # 오늘까지 발표일 지난 것
  announce_check.py --days 3 --only jecheon
"""
import json
import re
from datetime import date, timedelta

from _common import CONTEST, emit, parser, personal_info, run
from _pagecheck import scan
import chromectl as c

ap = parser(__doc__)
ap.add_argument("--days", type=int, default=0, help="오늘+N일까지 발표 예정도 포함")
ap.add_argument("--only", action="append", help="이 id만")
a = ap.parse_args()
KW = ["수상", "결과", "선정", "발표", "입상", "당선"]


def main():
    ann = json.loads((CONTEST / "_radar/announce.json").read_text())
    upto = (date.today() + timedelta(days=a.days)).isoformat()
    name = personal_info()["name"]
    todo = [(k, v) for k, v in ann.items() if (not a.only or k in a.only) and str(v.get("announceAt") or "9999")[:10] <= upto]
    out = []
    tid = None
    try:
        for k, v in todo:
            urls = re.findall(r"https?://[^\s)'\"，,]+", v.get("resultHow", ""))
            words = [w for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", v["name"]) if w not in ("2026", "공모전", "아이디어", "활용")][:4]
            item = {"id": k, "name": v["name"], "announceAt": v.get("announceAt"),
                    "gmailQuery": f'"{words[0] if words else v["name"][:10]}" newer_than:30d', "pages": []}
            for u in urls[:2]:
                try:
                    if tid is None:
                        tid = c.new_tab(u, a.profile)
                    else:
                        c.goto(tid, u)
                    r = scan(tid, KW + words, name)
                    item["pages"].append({"url": u, "login": r["login"], "nameHits": r["nameHits"], "hits": r["hits"][:8], "links": r["links"][:8]})
                except Exception as e:  # one bad page must not stop the rest
                    item["pages"].append({"url": u, "error": f"{type(e).__name__}: {str(e)[:120]}"})
            item["hint"] = "NAME_FOUND" if any(p.get("nameHits") for p in item["pages"]) else ("NO_URL_MAIL_ONLY" if not urls else "CHECK")
            out.append(item)
    finally:
        if tid and not a.keep_tab:
            c.close_tab(tid)
    emit({"checked": out}, "OK", f"{len(out)} contests, name found in {sum(i['hint'] == 'NAME_FOUND' for i in out)}")


run(main, a, "READ ONLY. 공모전/_radar/announce.json 의 발표일 지난 공모전마다 resultHow URL을 열어 수상자 명단에 강래민(강*민·강○민)이 있는지 보고. 아무것도 누르지 마라.")
