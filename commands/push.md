---
description: 리모트에 푸시
---

# /push

`~/.claude/rules/git-rules.md`의 푸시 규칙을 따른다.

1. `git status`로 커밋 안 된 변경사항 확인
2. `git log --oneline @{u}..HEAD 2>/dev/null`로 푸시할 커밋 확인
3. 현재 브랜치 + 리모트 확인
4. git-rules.md 안전 규칙 준수하여 푸시
5. 결과 보고
