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

### 스냅샷 파일: `.worklogs/.snapshot`

```json
{
  "timestamp": 1740100000,
  "totalTokens": 29760365,
  "totalCost": 17.87
}
```

### 계산 방법

1. `npx ccusage@latest session --json`으로 현재 세션 토큰 수집
2. `.worklogs/.snapshot` 읽기 (없으면 delta = 전체값)
3. **토큰 delta** = 현재 totalTokens - 스냅샷 totalTokens
4. **비용 delta** = 현재 totalCost - 스냅샷 totalCost
5. **소요 시간** = 현재 timestamp - 스냅샷 timestamp
6. 워크로그 작성 후 현재 값으로 스냅샷 갱신

## 엔트리 포맷

```markdown
---

## HH:MM

### 요청사항
- 사용자가 요청한 내용 (대화 컨텍스트에서 추출)

### 작업 내용
- 어떤 작업을 했는지 간결하게
- 주요 변경점 위주

### 변경 통계
\`\`\`
(git diff --cached --stat 결과)
\`\`\`

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
