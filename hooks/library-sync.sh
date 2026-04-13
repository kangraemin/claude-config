#!/bin/bash
# SessionEnd / PostCompact: library 업데이트 체크 + commit/push + Notion sync

LIBRARY="$HOME/.claude/.claude-library/LIBRARY.md"
LIB_DIR="$HOME/.claude/.claude-library"

[ -f "$LIBRARY" ] || exit 0

# 세션 카운터 파일 청소
rm -f "$HOME/.claude/hooks/.library-check-counter-"* 2>/dev/null || true

# 새 파일 있으면 commit + push
if [ -d "$LIB_DIR/.git" ] && [ -n "$(git -C "$LIB_DIR" status --porcelain 2>/dev/null)" ]; then
  # 변경된 library/ 파일 목록 저장 (Notion sync용)
  CHANGED_FILES=$(git -C "$LIB_DIR" status --porcelain 2>/dev/null | \
    grep -E '^\s*[AM?]+\s+library/' | \
    sed 's/^.\{3\}//' | \
    grep -v '_template\.md$' | \
    grep -v 'index\.md$' | \
    grep '\.md$')

  git -C "$LIB_DIR" add -A
  git -C "$LIB_DIR" commit -q -m "feat: library 업데이트 $(date +%Y-%m-%d)"
  git -C "$LIB_DIR" push -q 2>/dev/null || true

  # Notion sync (LIBRARY_NOTION_DB_ID 설정된 경우만)
  if [ -n "${LIBRARY_NOTION_DB_ID:-}" ] && [ -n "$CHANGED_FILES" ]; then
    NOTION_SCRIPT="$HOME/.claude/scripts/notion-library.sh"
    if [ -x "$NOTION_SCRIPT" ]; then
      while IFS= read -r file; do
        [ -z "$file" ] && continue
        # library/ prefix 제거
        REL_PATH="${file#library/}"
        bash "$NOTION_SCRIPT" "$REL_PATH" 2>/dev/null || true
      done <<< "$CHANGED_FILES"
    fi
  fi
fi
