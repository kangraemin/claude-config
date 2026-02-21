---
description: 변경사항을 커밋하고 푸시
---

# /commit

`~/.claude/rules/git-rules.md`의 커밋 규칙을 따른다.

1. `git status`로 변경 파일 확인
2. `git diff` + `git diff --cached`로 변경 내용 분석
3. `git log --oneline -5`로 최근 커밋 스타일 확인
4. git-rules.md의 커밋 규칙에 따라 메시지 작성
5. 변경 파일 개별 `git add`
6. `/worklog` 실행 (워크로그 작성 + staging)
7. HEREDOC으로 커밋 실행
8. `git push` (커밋과 푸시는 항상 세트)
9. `git status`로 결과 확인
