# /worklog

`~/.claude/rules/worklog-rules.md`의 규칙을 따른다.

## 플로우

1. `git diff --cached --stat`으로 staged 변경 확인 (없으면 `git diff --stat`으로 unstaged 확인)
2. 대화 컨텍스트에서 **사용자 요청사항** 정리
3. 변경 내용 분석하여 **작업 내용** 요약
4. `npx ccusage@latest session --json`으로 **토큰 사용량** 수집
5. `.worklogs/YYYY-MM-DD.md`에 엔트리 append
6. `git add .worklogs/YYYY-MM-DD.md`

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
- 모델: (사용된 모델)
- 총 토큰: (ccusage 결과, 일일 누적)
- 비용: (ccusage 결과, 일일 누적)
```

## 규칙

- 파일이 없으면 헤더(`# Worklog: <프로젝트> — YYYY-MM-DD`) 먼저 생성
- 요청사항은 **사용자 관점**으로 작성 (기술 구현 디테일 X)
- 작업 내용은 **간결하게** (3줄 이내 권장)
- ccusage 실패 시 "데이터 없음"으로 표기
