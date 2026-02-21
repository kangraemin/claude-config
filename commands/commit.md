# /commit

`~/.claude/rules/git-rules.md`의 커밋 규칙, `~/.claude/rules/worklog-rules.md`의 워크로그 규칙을 따른다.

## 커밋 플로우

1. `git status`로 변경 파일 확인
2. `git diff` + `git diff --cached`로 변경 내용 분석
3. `git log --oneline -5`로 최근 커밋 스타일 확인
4. git-rules.md의 커밋 규칙에 따라 메시지 작성
5. 변경 파일 개별 `git add`
6. **워크로그 작성** (아래 참조)
7. HEREDOC으로 커밋 실행
8. `git push` (커밋과 푸시는 항상 세트)
9. `git status`로 결과 확인

## 워크로그 작성 (6번 상세)

커밋 전에 `.worklogs/YYYY-MM-DD.md`에 엔트리를 append한다.

### 작성할 내용

```markdown
---

## HH:MM:SS

### 요청사항
- 이 커밋에 포함된 사용자의 요청을 정리 (대화 컨텍스트에서)

### 작업 내용
- 어떤 작업을 했는지 간결하게 요약
- 변경된 파일과 주요 변경점

### 변경 통계
\`\`\`
(git diff --cached --stat 결과)
\`\`\`

### 토큰 사용량
- 모델: (사용된 모델)
- 총 토큰: (ccusage 결과)
- 비용: (ccusage 결과)
```

### 토큰 데이터 수집

```bash
npx ccusage@latest session --json 2>/dev/null
```

- 현재 세션의 토큰 사용량을 가져온다
- ccusage 실패 시 "데이터 없음"으로 표기
- 일일 누적이므로 해당 시점의 스냅샷

### 규칙

- 파일이 없으면 헤더(`# Worklog: <프로젝트> — YYYY-MM-DD`) 먼저 생성
- 워크로그 파일도 `git add`해서 같은 커밋에 포함
- pre-commit 훅이 워크로그가 staged인 걸 감지하면 fallback 생략
