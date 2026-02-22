---
description: 워크로그 작성
---

# /worklog

`~/.claude/rules/worklog-rules.md`의 규칙을 따른다.

## 플로우

1. `git diff --cached --stat`으로 staged 변경 확인 (없으면 `git diff --stat`으로 unstaged 확인)
2. 대화 컨텍스트에서 **사용자 요청사항** 정리
3. 변경 내용 분석하여 **작업 내용** 요약
4. **토큰/시간 계산** (아래 참조)
5. `.worklogs/YYYY-MM-DD.md`에 엔트리 append
6. **스냅샷 갱신** (`.worklogs/.snapshot`)
7. `git add .worklogs/`

## 토큰/시간 계산

### 스냅샷 파일: `<프로젝트>/.worklogs/.snapshot`

```json
{
  "timestamp": 1740100000,
  "totalTokens": 29760365,
  "totalCost": 17.87
}
```

### 계산 순서

1. `date +%s`로 현재 unix timestamp 가져오기
2. `ccusage session --json`으로 현재 세션 토큰 수집 (없으면 `npx ccusage@latest session --json`)
3. `cat .worklogs/.snapshot`으로 이전 스냅샷 읽기
4. delta 계산:
   - **토큰 delta** = 현재 totalTokens - 스냅샷 totalTokens
   - **비용 delta** = 현재 totalCost - 스냅샷 totalCost
   - **소요 시간** = 현재 timestamp - 스냅샷 timestamp → 분 단위로 변환
5. 워크로그에 delta 값 기록
6. 스냅샷 갱신: `echo '{"timestamp":NOW,"totalTokens":NOW,"totalCost":NOW}' > .worklogs/.snapshot`

스냅샷이 없으면 (첫 실행) delta 대신 전체값 표시하고 스냅샷 생성.

### 중요

- 소요 시간은 **반드시 스냅샷 timestamp에서 계산**한다. 추정하지 않는다.
- 스냅샷 갱신은 **워크로그 작성 후** 반드시 실행한다.

## 엔트리 포맷

```markdown
---

## HH:MM

### 요청사항
- 사용자가 요청한 내용 (대화 컨텍스트에서 추출)

### 작업 내용
- 어떤 작업을 했는지 간결하게
- 주요 변경점 위주

### 변경 파일
- `파일명`: 이 파일에서 한 작업 한 줄 설명
- `파일명`: 이 파일에서 한 작업 한 줄 설명

### 토큰 사용량
- 모델: claude-opus-4-6
- 이번 작업: 1,234,567 토큰 / $1.23
- 소요 시간: 15분
- 일일 누적: 29,760,365 토큰 / $17.87
```

## 규칙

- 파일이 없으면 헤더(`# Worklog: <프로젝트> — YYYY-MM-DD`) 먼저 생성
- 요청사항은 **사용자 관점**으로 작성 (기술 구현 디테일 X)
- 작업 내용은 **간결하게** (3줄 이내 권장)
- ccusage 실패 시 "데이터 없음"으로 표기
- `.worklogs/.snapshot`은 git 추적하지 않음 (`.gitignore`에 추가)
