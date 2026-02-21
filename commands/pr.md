---
description: Pull Request 생성
---

# /pr

`~/.claude/rules/git-rules.md`의 PR 규칙을 따른다.

1. `git status`로 커밋 안 된 변경사항 확인
2. base branch 자동 감지 (main 또는 develop)
3. `git log --oneline` + `git diff <base>...HEAD`로 전체 변경 이력 분석
4. 리모트에 브랜치 없으면 `git push -u origin <branch>`
5. git-rules.md PR 규칙에 따라 제목/본문 작성
6. `gh pr create`로 PR 생성
7. PR URL 출력
