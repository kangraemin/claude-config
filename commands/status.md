---
description: 현재 Git 상태 요약
---

# /status

다음 정보를 한눈에 보여준다:

1. 현재 브랜치명
2. 리모트 tracking 상태 (ahead/behind 커밋 수)
3. 변경된 파일 목록 (staged / unstaged / untracked)
4. 최근 커밋 5개 (`git log --oneline -5`)
5. 커밋 안 된 변경사항이 있으면 간단한 diff 요약

깔끔한 표 형태로 출력할 것.
