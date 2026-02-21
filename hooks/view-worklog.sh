#!/bin/bash
# 워크로그 조회
# 사용법:
#   view-worklog.sh           → 오늘 전체
#   view-worklog.sh 2026-02-21  → 특정 날짜
#   view-worklog.sh latest      → 가장 최근 세션

DATE=${1:-$(date +"%Y-%m-%d")}
LOG_DIR="$HOME/.claude/worklogs"

if [ "$DATE" = "latest" ]; then
  LATEST=$(find "$LOG_DIR" -name "*.md" ! -name "index.md" -type f | sort | tail -1)
  if [ -n "$LATEST" ]; then
    cat "$LATEST"
  else
    echo "워크로그 없음"
  fi
  exit 0
fi

INDEX="$LOG_DIR/$DATE/index.md"

if [ ! -f "$INDEX" ]; then
  echo "워크로그 없음: $DATE"
  echo "사용 가능한 날짜:"
  ls "$LOG_DIR" 2>/dev/null | grep -E '^\d{4}-\d{2}-\d{2}$'
  exit 0
fi

echo "=== $DATE 워크로그 ==="
echo ""
cat "$INDEX"
echo ""
echo "---"
echo "상세 보기: cat ~/.claude/worklogs/$DATE/<파일명>.md"
