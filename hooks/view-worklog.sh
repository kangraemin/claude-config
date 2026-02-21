#!/bin/bash
# 워크로그 조회 (프로젝트 내 .worklogs/)
# 사용법:
#   view-worklog.sh           → 오늘 전체
#   view-worklog.sh 2026-02-21  → 특정 날짜
#   view-worklog.sh latest      → 가장 최근 세션

DATE=${1:-$(date +"%Y-%m-%d")}

# git 레포 루트 감지, 아니면 현재 디렉토리
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
LOG_DIR="${REPO_ROOT:-.}/.worklogs"

if [ ! -d "$LOG_DIR" ]; then
  echo "이 프로젝트에 워크로그가 없습니다: $LOG_DIR"
  exit 0
fi

if [ "$DATE" = "latest" ]; then
  LATEST=$(find "$LOG_DIR" -name "*.md" ! -name "index.md" -type f | sort | tail -1)
  if [ -n "$LATEST" ]; then
    cat "$LATEST"
  else
    echo "워크로그 없음"
  fi
  exit 0
fi

DAY_DIR="$LOG_DIR/$DATE"

if [ ! -d "$DAY_DIR" ]; then
  echo "워크로그 없음: $DATE"
  echo "사용 가능한 날짜:"
  ls "$LOG_DIR" 2>/dev/null | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  exit 0
fi

echo "=== $DATE 워크로그 ==="
echo ""
for f in "$DAY_DIR"/*.md; do
  [ -f "$f" ] || continue
  echo "--- $(basename "$f") ---"
  cat "$f"
  echo ""
done
