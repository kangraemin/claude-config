#!/bin/bash
# SessionEnd: 변경사항 있으면 워크로그 생성 + 자동 commit + push

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // ""')
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

# --- 워크로그 생성 ---
LOG_FILE=$(echo "{\"session_id\":\"$SESSION_ID\",\"cwd\":\"$CWD\",\"transcript_path\":\"$TRANSCRIPT\"}" | "$HOME/.claude/hooks/generate-worklog.sh")

# --- 스테이징 ---
while IFS= read -r file; do
  [ -z "$file" ] && continue
  REL_PATH=$(realpath --relative-to="$CWD" "$file" 2>/dev/null || echo "$file")
  git add "$REL_PATH" 2>/dev/null
done <<< "$CHANGED_FILES"
[ -n "$LOG_FILE" ] && [ -f "$LOG_FILE" ] && git add "$LOG_FILE" 2>/dev/null

git diff --cached --quiet && exit 0

# --- 커밋 ---
FILE_SUMMARY=$(git diff --cached --name-only | grep -v '.worklogs/' | head -10 | tr '\n' ', ' | sed 's/,$//')
FILE_COUNT=$(git diff --cached --name-only | grep -v '.worklogs/' | wc -l | tr -d ' ')

COMMIT_MSG="chore(claude): auto-commit session ${SESSION_ID:0:8}

Changed $FILE_COUNT file(s): $FILE_SUMMARY

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

git commit -m "$COMMIT_MSG" --no-verify 2>/dev/null || exit 0

# --- 푸시 ---
REMOTE=$(git remote 2>/dev/null | head -1)
BRANCH=$(git branch --show-current 2>/dev/null)
if [ -n "$REMOTE" ] && [ -n "$BRANCH" ]; then
  git push "$REMOTE" "$BRANCH" 2>/dev/null || true
fi

# 임시 수집 파일 정리
rm -f "$COLLECT_FILE"

exit 0
