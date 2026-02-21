#!/bin/bash
# Stop: 커밋 안 된 변경사항 자동 commit + push (안전장치)

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd')
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')

# Stop 훅 재진입 방지
[ "$STOP_HOOK_ACTIVE" = "true" ] && exit 0

cd "$CWD" 2>/dev/null || exit 0

# git 레포가 아니면 스킵
git rev-parse --is-inside-work-tree &>/dev/null || exit 0

# 변경사항 확인 (unstaged + untracked)
if git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null; then
  # staged/unstaged 변경 없음, untracked 확인
  UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null)
  [ -z "$UNTRACKED" ] && exit 0
fi

# 모든 변경사항 스테이징 (tracked 파일만)
git add -u 2>/dev/null

# untracked 파일도 추가 (.env, credentials 등 제외)
git ls-files --others --exclude-standard 2>/dev/null | while IFS= read -r file; do
  case "$file" in
    *.env|*.key|*.pem|*credentials*|*Secrets/*) continue ;;
    *) git add "$file" 2>/dev/null ;;
  esac
done

git diff --cached --quiet && exit 0

# 커밋
FILE_SUMMARY=$(git diff --cached --name-only | head -10 | tr '\n' ', ' | sed 's/,$//')
FILE_COUNT=$(git diff --cached --name-only | wc -l | tr -d ' ')

git commit -m "chore(auto): Stop 자동 커밋

변경 ${FILE_COUNT}개 파일: $FILE_SUMMARY

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>" 2>/dev/null || exit 0

# 푸시
REMOTE=$(git remote 2>/dev/null | head -1)
BRANCH=$(git branch --show-current 2>/dev/null)
if [ -n "$REMOTE" ] && [ -n "$BRANCH" ]; then
  git push "$REMOTE" "$BRANCH" 2>/dev/null || true
fi

exit 0
