#!/usr/bin/env python3
"""[지식iN] 검색 목록 한 쪽에서 답할 만한 질문을 고른다(질문은 열지 않는다 — 목록만 읽는다).

  kin_search.py --query "서울 맛집 추천" [--query "..."] [--days 14] [--hours 6] [--max-answers 2] [--must "맛집|점심"]

- 목록 주소 https://kin.naver.com/search/list.naver?query=…&section=qna&sort=date (최신순).
- 질문마다 제목·링크·날짜·답변 수·미리보기를 뽑고, --days 안·답변 --max-answers 이하만 남긴다.
- 왜 목록만: 질문을 하나씩 열면 조회 기록이 쌓이고 느리다(결정 kin-research-from-search-list-not-opening-each-question).
- 알림창·보안문자·제한 문구가 보이면 BLOCKED(exit 2)로 바로 멈춘다.
출력: 후보 JSON, 마지막 줄 RESULT: OK <n> | NONE.
"""
import datetime, re, time, urllib.parse

from _common import Blocked, emit, js, parser, poll, run, tab

ap = parser(__doc__)
ap.add_argument("--query", action="append", required=True)
ap.add_argument("--days", type=int, default=14)
ap.add_argument("--hours", type=int, default=0, help="0보다 크면 'N분/시간 전'으로 올라온 지 이 시간 안인 것만(늦게 붙지 않게)")
ap.add_argument("--max-answers", type=int, default=2)
ap.add_argument("--must", action="append", default=[], help="제목에 이 중 하나는 있어야 함(정규식)")
a = ap.parse_args()
a.no_fallback = True  # 읽기만 하는 스크립트라 Codex로 넘길 일이 없다

READ = r"""if (document.readyState !== 'complete') return null;
  const t = document.body.innerText;
  const warn = (t.match(/자동입력 ?방지|보안문자|일시적으로 제한|비정상적인 접근/) || [''])[0];
  const items = [...document.querySelectorAll('ul.basic1 > li, .search_list li, li._noanswerItem, li')]
    .map(li => {
      const a = li.querySelector('dt a[href*="qna/detail"], a._nclicks\\:kin\\.txt, a[href*="/qna/detail.naver"]');
      if (!a) return null;
      const txt = li.innerText;
      return {title: a.innerText.trim(), url: a.href.split('&')[0] + '&' + (a.href.match(/docId=\d+/) || [''])[0],
              date: (txt.match(/(\d{4}\.\d{2}\.\d{2})|(\d+(분|시간|일) 전)/) || [''])[0],
              answers: (txt.match(/답변수\s*(\d+)/) || txt.match(/답변\s*(\d+)/) || [0, 0])[1] * 1,
              preview: ((li.querySelector('dd:not(.txt_inline)') || {}).innerText || '').trim().slice(0, 160)};
    }).filter(Boolean);
  const seen = new Set();
  return {warn, items: items.filter(x => !seen.has(x.url) && seen.add(x.url))};"""


def age_days(s):
    now = datetime.date.today()
    if m := re.match(r"(\d{4})\.(\d{2})\.(\d{2})", s):
        return (now - datetime.date(*map(int, m.groups()))).days
    if "일 전" in s:
        return int(re.match(r"\d+", s).group())
    return 0 if s else 99


def age_hours(s):
    if m := re.match(r"(\d+)분 전", s):
        return int(m.group(1)) / 60
    if m := re.match(r"(\d+)시간 전", s):
        return int(m.group(1))
    return 999


def main():
    out = []
    for q in a.query:
        u = "https://kin.naver.com/search/list.naver?" + urllib.parse.urlencode({"query": q, "section": "qna", "sort": "date"})
        with tab(u, a) as tid:
            time.sleep(2)
            r = poll(tid, READ, timeout=25)
            if r["warn"]:
                raise Blocked(f"지식iN 목록에 '{r['warn']}' — 멈춤")
            for it in r["items"]:
                if not it["title"] or (a.must and not any(re.search(m, it["title"]) for m in a.must)):
                    continue
                if a.hours and age_hours(it["date"]) > a.hours:
                    continue
                if age_days(it["date"]) <= a.days and it["answers"] <= a.max_answers:
                    out.append({"query": q, **it})
        time.sleep(3)
    emit(out, f"OK {len(out)}" if out else "NONE")


run(main, a, "kin search list")
