#!/usr/bin/env python3
"""[지식iN] 분야별 최신 질문 목록에서 '답변 0개·막 올라온' 질문만 고른다(브라우저·로그인 없이 curl로 읽음).

  kin_fresh.py [--minutes 60] [--max-answers 0] [--dir 6080402 ...] [--skip-file drafts/kin/log.md] [--must "실업|퇴직"]

- 왜: 검색 목록(kin_search.py)은 날짜만 보여서 이미 답변 1~3개 달린 질문을 늦게 잡았다.
  실업급여 분야는 질문 11분 만에 첫 답변이 달린다(10/23 확인). 분야 목록은 'N분 전'과 답변 수를 함께 보여 준다.
- 목록 주소 https://kin.naver.com/qna/list.naver?dirId=D (최신순, 20개).
- --skip-file 안에 있는 docId(이미 단 질문)는 뺀다.
출력: 후보 JSON(dir, title, url, answers, age_min), 마지막 줄 RESULT: OK <n> | NONE.
"""
import argparse, html, json, re, subprocess, time

# 우리 서비스가 답할 수 있는 분야(dirId: 이름 — 서비스)
DIRS = {
    "6080402": "고용보험·실업급여 — 오늘꿈 계산기",
    "6080401": "고용안정·육아휴직 — 오늘꿈 계산기",
    "60802": "근로기준·주휴·퇴직금 — 오늘꿈 계산기",
    "60805": "노동 정책 — 오늘꿈 계산기",
    "60202": "부동산·중개수수료 — 오늘꿈 계산기",
    "31505": "꿈·해몽 — 오늘꿈",
    "70114": "임신·배란 — 오늘꿈 계산기",
    "80208": "음식점·맛집 — 어디먹·먹맵",
    "11080105": "글쓰기 — 글마감",
    # 지역 분야: 'OO역 맛집' 질문이 음식점 분야보다 여기 많다(10/25). 맛집 아닌 질문도 섞이니 제목으로 고른다.
    "1201": "서울 지역(맛집) — 먹맵·어디먹",
    "1202": "부산 지역(맛집) — 먹맵",
    "1203": "대구 지역(맛집) — 먹맵",
    "1204": "인천 지역(맛집) — 먹맵",
    "1209": "경기 지역(맛집) — 먹맵",
    "1214": "제주 지역 — 제주 숙소·먹맵",
}

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--dir", action="append", help="dirId (없으면 DIRS 전부)")
ap.add_argument("--minutes", type=int, default=60)
ap.add_argument("--max-answers", type=int, default=0)
ap.add_argument("--skip-file", default="")
ap.add_argument("--must", action="append", default=[])
a = ap.parse_args()

ROW = re.compile(r'href="/qna/detail\.naver\?d1id=\d+&dirId=(\d+)&docId=(\d+)"[^>]*>(.*?)</a>.*?'
                 r'<td class="t_num">.*?</span>\s*\d*\s*</td>\s*<td class="t_num">(\d+)</td>\s*<td class="t_num">([^<]+)</td>', re.S)


def age_min(s):
    s = s.strip()
    if m := re.match(r"(\d+)분 전", s):
        return int(m.group(1))
    if m := re.match(r"(\d+)시간 전", s):
        return int(m.group(1)) * 60
    return 10 ** 6


skip = set(re.findall(r"docId=(\d+)", open(a.skip_file).read())) if a.skip_file else set()
out = []
for d in a.dir or DIRS:
    t = subprocess.run(["curl", "-s", "-m", "15", "-A", "Mozilla/5.0", f"https://kin.naver.com/qna/list.naver?dirId={d}"],
                       capture_output=True, text=True).stdout
    for dir_id, doc, title, ans, when in ROW.findall(t):
        title = html.unescape(re.sub(r"<[^>]+>", "", title)).strip()
        if doc in skip or int(ans) > a.max_answers or age_min(when) > a.minutes:
            continue
        if a.must and not any(re.search(m, title) for m in a.must):
            continue
        out.append({"dir": DIRS.get(d, d), "title": title, "answers": int(ans), "age_min": age_min(when),
                    "url": f"https://kin.naver.com/qna/detail.naver?dirId={dir_id}&docId={doc}"})
    time.sleep(1)
out.sort(key=lambda x: x["age_min"])
print(json.dumps(out, ensure_ascii=False, indent=1))
print(f"RESULT: OK {len(out)}" if out else "RESULT: NONE")
