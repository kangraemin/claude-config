#!/usr/bin/env python3
"""[읽기] KIPRIS 국내 상표 검색 — 브라우저 없이 kipris.or.kr 검색 XHR(grrt1000a.do?method=searchTM)을 직접 부른다.
네이밍 공모전 후보의 동일·유사 상표 확인용. 로그인 불필요.

  kipris_tm.py 이솦 코드닷                # 이름별 총 건수 + 살아 있는(출원·등록·공고) 건 요약
  kipris_tm.py --classes 09,41,42 이솦     # 지정 상품류만 '관련'으로 표시 (기본 09,16,28,41,42)
  kipris_tm.py --json out.json 이솦 ...    # 원자료 저장

검색은 KIPRIS 기본 검색과 같아 부분·발음 유사도 함께 걸린다(이솦 → 이솦틴·하이솦).
마지막 줄: RESULT: OK <이름 수>
"""
import argparse, json, sys, time, urllib.parse, urllib.request

URL = "https://www.kipris.or.kr/kdtj/grrt1000a.do?method=searchTM"
FIXED = ("sortField=RANK&sortState=DESC&currentPage=1&numPerPage=90"
         "&merchandiseString=td40%2Ctd41%2Ctd42%2Ctd43%2Ctd44%2Ctd45%2Ctd47%2Ctd48%2Ctdmd%2C"
         "&measureString=A%2CB%2CR%2CJ%2CI%2CF%2CC%2CG"
         "&patternString=NAKletter%2CNAKfigure%2CNAKlmixed%2CNAKfmixed%2CNAKsounds%2CNAKfragre%2CTPDcommon%2CTPDcolors"
         "%2CTPDcolor%2CTPDdimens%2CTPDcmixed%2CTPDdimcol%2CTPDhologr%2CTPDaction%2CTPDvisual%2CTPDinvisible"
         "&downYn=N&piSearchYN=N&searchInTrans=N&searchInComplate=N")
LIVE = ("출원", "등록", "공고", "공고대기")


def search(word):
    q = urllib.parse.quote(word)
    body = f"queryText={q}&expression={q}&{FIXED}".encode()
    req = urllib.request.Request(URL, data=body, headers={
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": "https://www.kipris.or.kr/khome/search/searchResult.do?tab=trademark",
        "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words", nargs="+")
    ap.add_argument("--classes", default="09,16,28,41,42", help="관련 상품류(쉼표)")
    ap.add_argument("--json", help="원자료 저장 경로")
    a = ap.parse_args()
    cls = {c.strip().lstrip("0") for c in a.classes.split(",")}
    raw = {}
    for w in a.words:
        try:
            d = search(w)
        except Exception as e:  # noqa: BLE001
            print(f"## {w}\n- 검색 실패: {e}"); continue
        raw[w] = d
        rows = d.get("resultList") or []
        live = [r for r in rows if any(r.get("LAS", "").startswith(s) for s in LIVE)]
        rel = [r for r in live if {c.lstrip("0") for c in r.get("PRC", "").split("|")} & cls]
        print(f"## {w}\n- 총 {d.get('countInfo', {}).get('totalcount', 0)}건 · 살아 있음 {len(live)} · 관련류({a.classes}) 살아 있음 {len(rel)}")
        seen = set()
        for r in rel + [x for x in live if x not in rel][:5]:
            key = (r.get("TTL_SUB"), r.get("PRC"), r.get("LAS"))
            if key in seen: continue
            seen.add(key)
            mark = "★" if r in rel else " "
            print(f"  {mark} {r.get('TTL_SUB')} | {r.get('LAS')} | {r.get('PRC')}류 | {(r.get('TRH') or r.get('APNM') or '').strip()} | {r.get('GD','')[:50]}")
        time.sleep(0.7)
    if a.json:
        json.dump(raw, open(a.json, "w"), ensure_ascii=False)
    print(f"RESULT: OK {len(raw)}")


if __name__ == "__main__":
    sys.exit(main())
