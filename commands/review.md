---
description: 코드 리뷰 실행
---

# /review

코드 변경사항을 리뷰한다. 인자로 PR 번호나 URL을 주면 PR 리뷰, 없으면 로컬 브랜치 diff 리뷰.

## 실행 흐름

### Step 1: 대상 결정

- 인자가 PR 번호/URL → `gh pr view`로 PR 정보 수집
- 인자 없음 → `git diff main...HEAD`로 로컬 diff 수집
- diff가 없으면 안내 후 중단

### Step 2: 리뷰 실행

1. `~/.claude/rules/review-rules.md` 읽기
2. `DEVELOPMENT_GUIDE.md` 있으면 읽기 (프로젝트 컨벤션 파악)
3. 변경 파일별 분석
4. 심각도별 이슈 분류 (Critical / Important / Minor)

### Step 3: 결과 전달

- **PR 리뷰**: `gh api`로 인라인 코멘트 + 요약 코멘트
- **로컬 리뷰**: 터미널에 요약 출력

### Step 4: 사용자에게 보고

- 발견 건수, 심각도별 분포, 주요 이슈 요약
