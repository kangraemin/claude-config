#!/bin/bash
# Claude Code 글로벌 설정 설치 스크립트
# 사용법: bash <(curl -sL https://raw.githubusercontent.com/kangraemin/claude-config/main/install.sh)

set -e

REPO="https://github.com/kangraemin/claude-config.git"
TARGET="$HOME/.claude"
BACKUP="$HOME/.claude-backup-$(date +%Y%m%d%H%M%S)"

echo "=== Claude Code 글로벌 설정 설치 ==="
echo ""

# --- 1. 기존 설정 백업 ---
if [ -d "$TARGET" ]; then
  echo "[1/4] 기존 설정 백업 → $BACKUP"

  # git으로 관리 중이면 pull로 업데이트
  if [ -d "$TARGET/.git" ]; then
    echo "  이미 claude-config으로 관리 중. 업데이트합니다."
    cd "$TARGET" && git pull origin main
    echo ""
    echo "=== 업데이트 완료! ==="
    exit 0
  fi

  # 보존할 파일/폴더 (머신별 데이터)
  mkdir -p "$BACKUP"
  [ -d "$TARGET/projects" ] && mv "$TARGET/projects" "$BACKUP/"
  [ -d "$TARGET/worklogs" ] && mv "$TARGET/worklogs" "$BACKUP/"
  [ -d "$TARGET/plugins" ] && mv "$TARGET/plugins" "$BACKUP/"
  [ -d "$TARGET/cache" ] && mv "$TARGET/cache" "$BACKUP/"
  [ -f "$TARGET/statsig_user_id" ] && mv "$TARGET/statsig_user_id" "$BACKUP/"

  # 기존 사용자 설정 보존
  [ -f "$TARGET/settings.json" ] && cp "$TARGET/settings.json" "$BACKUP/settings.json.bak"

  # 기존 .claude 삭제
  rm -rf "$TARGET"
else
  echo "[1/4] 기존 설정 없음. 새로 설치합니다."
  mkdir -p "$BACKUP"
fi

# --- 2. 레포 클론 ---
echo "[2/4] claude-config 클론 → $TARGET"
git clone "$REPO" "$TARGET"

# --- 3. 백업 데이터 복원 ---
echo "[3/4] 머신별 데이터 복원"
[ -d "$BACKUP/projects" ] && mv "$BACKUP/projects" "$TARGET/"
[ -d "$BACKUP/worklogs" ] && mv "$BACKUP/worklogs" "$TARGET/"
[ -d "$BACKUP/plugins" ] && mv "$BACKUP/plugins" "$TARGET/"
[ -d "$BACKUP/cache" ] && mv "$BACKUP/cache" "$TARGET/"
[ -f "$BACKUP/statsig_user_id" ] && mv "$BACKUP/statsig_user_id" "$TARGET/"

# 임시 수집 디렉토리 생성
mkdir -p "$TARGET/worklogs/.collecting"

# --- 4. 훅 스크립트 실행 권한 ---
echo "[4/4] 실행 권한 설정"
chmod +x "$TARGET/hooks/"*.sh 2>/dev/null || true

# 백업 폴더 정리 (비어있으면 삭제)
rmdir "$BACKUP" 2>/dev/null || true

echo ""
echo "=== 설치 완료! ==="
echo ""
echo "포함된 설정:"
echo "  agents/    — lead, dev, qa, git"
echo "  commands/  — /commit, /push, /pr, /test, /status"
echo "  rules/     — git-rules (커밋/PR/브랜치 규칙)"
echo "  hooks/     — worklog, auto-commit, session-end"
echo ""
echo "업데이트: cd ~/.claude && git pull"
