#!/bin/bash
# SessionEnd: 변경사항 있으면 자동 commit + push

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

# 변경된 파일이 없으면 스킵
[ -z "$CHANGED_FILES" ] && exit 0

# git diff 확인 (실제로 변경사항이 있는지)
HAS_CHANGES=false
while IFS= read -r file; do
  [ -z "$file" ] && continue
  # CWD 기준 상대경로로 변환
  REL_PATH=$(realpath --relative-to="$CWD" "$file" 2>/dev/null || echo "$file")
  if git diff --quiet -- "$REL_PATH" 2>/dev/null; then
    # staged 확인
    if ! git diff --cached --quiet -- "$REL_PATH" 2>/dev/null; then
      HAS_CHANGES=true
      break
    fi
  else
    HAS_CHANGES=true
    break
  fi
  # untracked 파일 확인
  if git ls-files --others --exclude-standard -- "$REL_PATH" 2>/dev/null | grep -q .; then
    HAS_CHANGES=true
    break
  fi
done <<< "$CHANGED_FILES"

$HAS_CHANGES || exit 0

# 이 세션에서 변경한 파일만 stage
while IFS= read -r file; do
  [ -z "$file" ] && continue
  REL_PATH=$(realpath --relative-to="$CWD" "$file" 2>/dev/null || echo "$file")
  git add "$REL_PATH" 2>/dev/null
done <<< "$CHANGED_FILES"

# staged 변경사항 확인
git diff --cached --quiet && exit 0

# 변경 파일 요약
FILE_SUMMARY=$(git diff --cached --name-only | head -10 | tr '\n' ', ' | sed 's/,$//')
FILE_COUNT=$(git diff --cached --name-only | wc -l | tr -d ' ')

# 커밋 메시지 생성
COMMIT_MSG="chore(claude): auto-commit session ${SESSION_ID:0:8}

Changed $FILE_COUNT file(s): $FILE_SUMMARY

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

git commit -m "$COMMIT_MSG" --no-verify 2>/dev/null || exit 0

# 리모트 + 업스트림 있으면 push
REMOTE=$(git remote 2>/dev/null | head -1)
BRANCH=$(git branch --show-current 2>/dev/null)
if [ -n "$REMOTE" ] && [ -n "$BRANCH" ]; then
  git push "$REMOTE" "$BRANCH" 2>/dev/null || true
fi

exit 0
