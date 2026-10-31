---
name: koubo-daily-collect
description: 公募の栞(koubonoshiori.com, 일본 문학 공모전 사이트) 데이터를 매일 새로 모으는 일 — 주최사 공모 목록 페이지에서 새 공고 찾기, AI로 요강 읽기, 사이트 다시 배포. "일본 꺼도 수집 매일", "公募の栞 데이터 오래됐어", "일본 공모전 새로 안 들어와", "수집 날짜가 10/31이야", "일본 수집 돌려", "koubo 수집", "새 공모 추가", "sources.csv에 넣어", "일본 추출 비용" 같은 말이 나오면, 그리고 일본 공모전 데이터·수집 순서를 고치기 전에 반드시 이 스킬부터 연다. 글마감(한국)은 ops/mac-local.sh 몫이라 여기 아니다.
---

# 公募の栞 매일 수집

## 왜 있나
- 11/1 사용자: "뭔소리여 일본꺼도 수집을매일해야지". 그때까지 일본은 10/31에 손으로 한 번 돌린 게 전부였다.
- 한국(글마감)은 `ops/mac-local.sh`가 매일 도는데 일본은 빠져 있었다. 레이더 묶음(`my-sns/drafts/src/lit_radar.py`, 09:00)이 오래된 일본 데이터를 그대로 보냈다.

## 어떻게 도나
- launchd `kr.geulmagam.jpdaily` 매일 08:00 → 09:00 공모전 레이더보다 먼저 끝난다.
- 레포 `~/programming/vibecoding/글쓰기공모전`, 코드 `ops/jp/daily.py`, 기록 `ops/jp/logs/daily-<날짜>.log`.
- 순서:
  1. `data/jp/sources.csv`의 `watch_url`(주최사 공모 목록 페이지, 약 230곳)을 받아 공모처럼 보이는 링크(賞·募集·公募·短歌·俳句·小説…)를 모은다. robots.txt가 막은 곳은 안 받는다.
  2. `data/jp/hub_links.json`에 없던 링크만 새 후보로 `sources.csv` 끝에 붙인다. 첫 실행은 본 것만 적는다(수백 건이 한꺼번에 비용으로 나가지 않게).
  3. 마감이 다 지난 공고는 읽은 지 30일이 지나면 다시 읽는다. 같은 주소에 다음 회차 요강이 올라오기 때문이다. 옛 파일은 `extracted/old/`.
  4. 안 읽은 공고를 하루 12건까지 `batch.py --sources`로 AI가 읽는다. 공고가 아닌 페이지는 `is_contest_page=false`로 사이트에서 빠진다.
  5. `ops/jp/deploy.sh`로 사이트를 다시 만들어 배포한다.
- 마지막 줄 `RESULT: OK | FAIL ... | DRY`.

## 돈
- AI 읽기는 민구형 키(`MUKMAP_ANTHROPIC_API_KEY`)로만 한다. 사용자 10/31 "30달러까지 ㄱㅊ" → 월 상한 $30(`batch.py` `CAP`, 기록 `data/jp/spend.json`).
- 1건 평균 $0.063(10/31 394건 $22.4). 하루 12건이면 월 약 $23. 하루 건수를 올리기 전에 이 계산부터 다시 한다.
- 상한에 닿으면 `batch.py`가 `cap`으로 멈춘다. 그 달 나머지는 링크 모으기·배포만 돈다.

## 손으로 돌릴 때
```bash
cd ~/programming/vibecoding/글쓰기공모전
/opt/homebrew/bin/python3 ops/jp/daily.py --dry        # 링크만 모아 보고 저장·비용·배포 없음(약 6분)
/opt/homebrew/bin/python3 ops/jp/daily.py [--limit N]  # 실제
launchctl print gui/$(id -u)/kr.geulmagam.jpdaily | grep -E 'runs|last exit'
```
- `/usr/bin/python3`는 버전이 낮아 안 된다. `/opt/homebrew/bin/python3`를 쓴다.

## 함정
- `jp-watch-trial`의 `kr.geulmagam.jpwatch`(09:00)는 목록 페이지 스냅샷만 남기는 시험판이다. 사이트에 새 공고를 넣지 않는다. 이걸 보고 "매일 수집 중"이라고 말하지 않는다.
- 읽다 실패한 공고(오류 기록)는 파일이 남아 다음 날 건너뛴다. 다시 읽히려면 그 `extracted/<해시>.json`을 `old/`로 옮긴다.
- 한국어 번역·사람이 골랐다는 말은 사이트에 쓰지 않는다(`contest-posts` 스킬 '公募の栞만의 규칙').
- 수집 규칙을 바꾸면 이 스킬만 고치지 말고 `daily.py`에 넣는다. launchd는 스킬을 읽지 않는다.

## 검증 상태
- 11/1 `--dry`: 목록 페이지 227곳 중 18곳 오류, 첫 실행이라 새 후보 0(본 것만 저장). 5분 52초.
- 11/1 첫 실제 실행: 로그 `ops/jp/logs/daily-2026-11-01.log`.
