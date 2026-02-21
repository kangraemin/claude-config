#!/bin/bash
# SessionEnd: 커밋 안 된 잔여 변경사항 자동 commit + push (안전장치)
# 워크로그는 git post-commit 훅이 자동 생성

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
COLLECT_FILE="$HOME/.claude/worklogs/.collecting/$SESSION_ID.jsonl"

cd "$CWD" 2>/dev/null || exit 0

# git 레포가 아니면 스킵
git rev-parse --is-inside-work-tree &>/dev/null || exit 0

# 이 세션에서 변경한 파일만 추출
CHANGED_FILES=""
if [ -f "$COLLECT_FILE" ]; then
  CHANGED_FILES=$(jq -r '
    select(.tool == "Write" or .tool == "Edit") |
    .input.file_path // .input.path // empty
  ' "$COLLECT_FILE" 2>/dev/null | sort -u)
fi

[ -z "$CHANGED_FILES" ] && exit 0

# git diff 확인
HAS_CHANGES=false
while IFS= read -r file; do
  [ -z "$file" ] && continue
  REL_PATH=$(realpath --relative-to="$CWD" "$file" 2>/dev/null || echo "$file")
  if git diff --quiet -- "$REL_PATH" 2>/dev/null; then
    if ! git diff --cached --quiet -- "$REL_PATH" 2>/dev/null; then
      HAS_CHANGES=true; break
    fi
  else
    HAS_CHANGES=true; break
  fi
  if git ls-files --others --exclude-standard -- "$REL_PATH" 2>/dev/null | grep -q .; then
    HAS_CHANGES=true; break
  fi
done <<< "$CHANGED_FILES"

$HAS_CHANGES || exit 0

# 스테이징
while IFS= read -r file; do
  [ -z "$file" ] && continue
  REL_PATH=$(realpath --relative-to="$CWD" "$file" 2>/dev/null || echo "$file")
  git add "$REL_PATH" 2>/dev/null
done <<< "$CHANGED_FILES"

git diff --cached --quiet && exit 0

# 커밋 (post-commit 훅이 워크로그 자동 생성)
FILE_SUMMARY=$(git diff --cached --name-only | head -10 | tr '\n' ', ' | sed 's/,$//')
FILE_COUNT=$(git diff --cached --name-only | wc -l | tr -d ' ')

git commit --no-verify -m "chore(claude): auto-commit session ${SESSION_ID:0:8}

Changed $FILE_COUNT file(s): $FILE_SUMMARY

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>" 2>/dev/null || exit 0

# 푸시
REMOTE=$(git remote 2>/dev/null | head -1)
BRANCH=$(git branch --show-current 2>/dev/null)
if [ -n "$REMOTE" ] && [ -n "$BRANCH" ]; then
  git push "$REMOTE" "$BRANCH" 2>/dev/null || true
fi

rm -f "$COLLECT_FILE"
exit 0
