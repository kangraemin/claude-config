#!/usr/bin/env python3
"""[읽기] 공모전 관련 메일 훑기 (_radar/mailcheck/prompt.md 의 LLM 없는 판).
받은편지함+스팸+프로모션을 newer_than:Nd 로 검색해 공모전 키워드에 걸리는 메일만 표로.

  gmail_mailcheck.py                      # 10일, 화면 출력
  gmail_mailcheck.py --days 14 --out _radar/mailcheck/mails-script.md
  gmail_mailcheck.py --open-bodies        # 걸린 메일을 열어 본문 앞부분까지 (읽음 표시됨)
"""
import re
from datetime import datetime
from pathlib import Path

from _common import ACCOUNT, emit, parser, run, tab
from _gmail import list_rows, open_row, search, search_url
import chromectl as c

KW = (r"공모|접수|보완|서류|수상|당선|입상|선정|결과|심사|마감|인증|참가|응모|제출|해커톤|대회|챌린지|"
      r"thinkcontest|korea\.kr|go\.kr|or\.kr|devpost|kaggle|dacon|codabench|D-U-N-S|Google Play")
ADS = r"뉴스레터|newsletter|광고\)|\(광고|구독|unsubscribe|이번 주 공모전|공모전 소식|씽굿 추천"

MASK = re.compile(r"(인증번호는?|인증 ?코드|코드는|code is|code:)\s*[A-Z0-9]{4,8}", re.I)  # 인증번호·토큰은 기록 안 함

ap = parser(__doc__)
ap.add_argument("--days", type=int, default=10)
ap.add_argument("--account", default=ACCOUNT)
ap.add_argument("--out", help="마크다운 저장 경로")
ap.add_argument("--open-bodies", action="store_true")
a = ap.parse_args()
QUERIES = [f"in:anywhere newer_than:{a.days}d -in:sent -in:drafts", f"in:spam newer_than:{a.days}d",
           f"category:promotions newer_than:{a.days}d"]


def main():
    seen, hits, counts = set(), [], {}
    with tab(search_url(QUERIES[0], a.account), a) as tid:
        for qy in QUERIES:
            res = search(tid, qy, a.account, 100)
            counts[qy] = {"rows": len(res["rows"]), "pager": res["pager"]}
            for i, r in enumerate(res["rows"], 1):
                key = (r["subject"], r["date"])
                text = " ".join([r["subject"], r["snippet"], r["who"], " ".join(r["from"])])
                if key in seen or not re.search(KW, text, re.I):
                    continue
                seen.add(key)
                r["box"] = "spam" if "spam" in qy else "promo" if "promotions" in qy else "all"
                r["kind"] = "안내" if re.search(ADS, text, re.I) else "요청·결과"
                if a.open_bodies and r["kind"] != "안내":
                    th = open_row(tid, i)
                    r["body"] = (th["messages"][-1]["body"] if th["messages"] else "")[:600]
                    c.run_js(tid, "history.back()")
                    search(tid, qy, a.account, 100)
                hits.append(r)
    md = [f"# 공모전 관련 메일 (스크립트, {datetime.now():%Y-%m-%d %H:%M} KST, {a.account}, {a.days}일)", ""]
    for kind in ("요청·결과", "안내"):
        md += [f"## {kind}", "", "| 날짜 | 함 | 보낸사람 | 제목 | 미리보기 |", "|---|---|---|---|---|"]
        for r in hits:
            if r["kind"] == kind:
                cell = lambda s: MASK.sub(r"\1 ******", s.replace("|", "/").replace("\n", " "))[:160]  # noqa: E731
                md.append(f"| {r['date']} | {r['box']} | {cell(r['who'] or ','.join(r['from']))} | {cell(r['subject'])} | {cell(r.get('body') or r['snippet'])} |")
        md.append("")
    if a.out:
        Path(a.out).write_text("\n".join(md))
    emit({"counts": counts, "hits": len(hits), "out": a.out, "markdown": None if a.out else "\n".join(md)}, "DONE", str(len(hits)))


run(main, a, f"READ ONLY. Gmail {a.account}만. {' / '.join(QUERIES)} 를 검색해 공모전 관련 메일(공모전·접수·보완·서류·수상·결과·심사·마감·인증 등)을 "
    f"날짜|보낸사람|제목|핵심 내용(요청·기한) 표로 {a.out or '출력'}에 써라. 광고성 안내는 '안내' 절에 목록만. 답장·삭제·보관·링크 클릭 금지. 마지막 줄 RESULT: DONE <건수>")
