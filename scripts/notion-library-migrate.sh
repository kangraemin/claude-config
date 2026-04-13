#!/bin/bash
# 기존 library/*.md 파일을 Notion DB로 일괄 마이그레이션
# Usage: notion-library-migrate.sh [--dry-run] [--category <name>] [library_root]
#
# --dry-run         : 실제 전송 없이 대상 파일만 출력
# --category <name> : 특정 카테고리만 처리 (예: ml, dev)
# library_root      : library 루트 경로 (기본: ~/.claude/.claude-library)

set -euo pipefail

PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || echo python3)

# .env 탐색
for _envfile in "$HOME/.claude/.env" ${AI_WORKLOG_DIR:+"$AI_WORKLOG_DIR/.env"}; do
  [ -f "$_envfile" ] && { set -a; source "$_envfile"; set +a; }
done

DRY_RUN=false
TARGET_CATEGORY=""
LIBRARY_ROOT=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)    DRY_RUN=true; shift ;;
    --category)   TARGET_CATEGORY="$2"; shift 2 ;;
    *) LIBRARY_ROOT="$1"; shift ;;
  esac
done

LIBRARY_ROOT="${LIBRARY_ROOT:-$HOME/.claude/.claude-library}"
LIBRARY_DIR="$LIBRARY_ROOT/library"

if [ ! -d "$LIBRARY_DIR" ]; then
  echo "ERROR: library directory not found: $LIBRARY_DIR" >&2
  exit 1
fi

if [ "$DRY_RUN" = false ]; then
  if [ -z "${NOTION_TOKEN:-}" ]; then
    echo "ERROR: NOTION_TOKEN required (set in .env)" >&2
    exit 1
  fi
  if [ -z "${LIBRARY_NOTION_DB_ID:-}" ]; then
    echo "ERROR: LIBRARY_NOTION_DB_ID required (set in settings.json env)" >&2
    exit 1
  fi
fi

NOTION_SCRIPT="$(dirname "$0")/notion-library.sh"
if [ "$DRY_RUN" = false ] && [ ! -x "$NOTION_SCRIPT" ]; then
  # fallback: installed location
  NOTION_SCRIPT="$HOME/.claude/scripts/notion-library.sh"
  if [ ! -x "$NOTION_SCRIPT" ]; then
    echo "ERROR: notion-library.sh not found" >&2
    exit 1
  fi
fi

# 마이그레이션 추적 파일
MIGRATED_FILE="$LIBRARY_ROOT/.notion-migrated"
touch "$MIGRATED_FILE" 2>/dev/null || true

TOTAL=0
SUCCESS=0
SKIPPED=0
FAILED=0

# library/ 하위의 모든 .md 파일 탐색
while IFS= read -r file; do
  # library/ 기준 상대 경로
  rel_path="${file#$LIBRARY_DIR/}"

  # 제외: _template.md, index.md, 숨김 파일
  basename_file=$(basename "$rel_path")
  case "$basename_file" in
    _template.md|index.md|.*) continue ;;
  esac

  # 카테고리 필터
  if [ -n "$TARGET_CATEGORY" ]; then
    file_category=$(echo "$rel_path" | cut -d'/' -f1)
    [ "$file_category" != "$TARGET_CATEGORY" ] && continue
  fi

  TOTAL=$((TOTAL + 1))

  # 이미 마이그레이션된 파일 스킵
  if grep -qF "$rel_path" "$MIGRATED_FILE" 2>/dev/null; then
    SKIPPED=$((SKIPPED + 1))
    [ "$DRY_RUN" = true ] && echo "  SKIP (already migrated): $rel_path"
    continue
  fi

  if [ "$DRY_RUN" = true ]; then
    echo "  WILL MIGRATE: $rel_path"
    continue
  fi

  # Notion에 전송
  if bash "$NOTION_SCRIPT" "$rel_path" 2>/dev/null; then
    echo "  OK: $rel_path"
    echo "$rel_path" >> "$MIGRATED_FILE"
    SUCCESS=$((SUCCESS + 1))
  else
    echo "  FAIL: $rel_path" >&2
    FAILED=$((FAILED + 1))
  fi

  # API rate limit 방지
  sleep 0.5
done < <(find "$LIBRARY_DIR" -name '*.md' -type f | sort)

echo ""
if [ "$DRY_RUN" = true ]; then
  echo "Dry run complete: $TOTAL files found, $SKIPPED already migrated"
else
  echo "Migration complete: $SUCCESS OK, $SKIPPED skipped, $FAILED failed (total: $TOTAL)"
fi
