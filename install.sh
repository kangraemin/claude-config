#!/bin/bash
# Claude Code 설정 설치 스크립트
#
# 전역 설치: bash <(curl -sL https://raw.githubusercontent.com/kangraemin/claude-config/main/install.sh)
# 로컬 설치: bash <(curl -sL https://raw.githubusercontent.com/kangraemin/claude-config/main/install.sh) --local

set -e

REPO="https://github.com/kangraemin/claude-config.git"
WORKLOG_REPO="https://github.com/kangraemin/ai-worklog.git"
MODE="${1:-}"

# --- 의존성 체크 ---
echo "=== 의존성 확인 ==="
MISSING=0
for cmd in git node jq gh; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "  ✓ $cmd"
  else
    echo "  ✗ $cmd — 설치 필요"
    MISSING=1
  fi
done

if [ "$MISSING" -eq 1 ]; then
  echo ""
  echo "누락된 의존성을 설치한 후 다시 실행해주세요."
  echo "  - node: https://nodejs.org/"
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
      echo "  - jq: winget install jqlang.jq"
      echo "  - gh: winget install GitHub.cli"
      ;;
    *)
      echo "  - jq: brew install jq"
      echo "  - gh: brew install gh"
      ;;
  esac
  exit 1
fi
echo ""

# --- 모드 선택 ---
if [ "$MODE" = "--local" ]; then
  MODE="local"
elif [ "$MODE" = "--global" ]; then
  MODE="global"
else
  echo "=== Claude Code 설정 설치 ==="
  echo ""
  echo "  1) 전역 설치 (~/.claude/) — 모든 프로젝트에 적용"
  echo "  2) 이 레포에만 설치 (.claude/) — 현재 프로젝트에만 적용"
  echo ""
  read -p "선택 [1/2]: " CHOICE
  case "$CHOICE" in
    1) MODE="global" ;;
    2) MODE="local" ;;
    *) echo "취소됨."; exit 0 ;;
  esac
fi

# =============================================================
# 전역 설치
# =============================================================
if [ "$MODE" = "global" ]; then
  TARGET="$HOME/.claude"
  BACKUP="$HOME/.claude-backup-$(date +%Y%m%d%H%M%S)"

  echo ""
  echo "=== 전역 설치 → $TARGET ==="

  if [ -d "$TARGET" ]; then
    # 이미 git으로 관리 중이면 pull
    if [ -d "$TARGET/.git" ]; then
      echo "이미 설치됨. 업데이트합니다."
      cd "$TARGET" && git pull origin main
      echo ""
      echo "=== 업데이트 완료! ==="
      exit 0
    fi

    # 기존 설정 백업
    echo "[1/3] 기존 설정 백업"
    mkdir -p "$BACKUP"
    for item in projects worklogs plugins cache; do
      [ -d "$TARGET/$item" ] && mv "$TARGET/$item" "$BACKUP/"
    done
    [ -f "$TARGET/statsig_user_id" ] && mv "$TARGET/statsig_user_id" "$BACKUP/"
    [ -f "$TARGET/settings.json" ] && cp "$TARGET/settings.json" "$BACKUP/settings.json.bak"
    rm -rf "$TARGET"
  else
    echo "[1/3] 기존 설정 없음"
    mkdir -p "$BACKUP"
  fi

  # 클론
  echo "[2/3] 클론"
  git clone "$REPO" "$TARGET"

  # 복원
  echo "[3/3] 데이터 복원"
  for item in projects worklogs plugins cache; do
    [ -d "$BACKUP/$item" ] && mv "$BACKUP/$item" "$TARGET/"
  done
  [ -f "$BACKUP/statsig_user_id" ] && mv "$BACKUP/statsig_user_id" "$TARGET/"
  mkdir -p "$TARGET/worklogs/.collecting"

  rmdir "$BACKUP" 2>/dev/null || true

  echo ""
  echo "=== 전역 설치 완료! ==="
  echo ""
  echo "포함: agents/ commands/ rules/"
  echo "업데이트: cd ~/.claude && git pull"

# =============================================================
# 로컬 설치 (현재 레포에만)
# =============================================================
elif [ "$MODE" = "local" ]; then
  # git 레포 루트 확인
  REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
  if [ -z "$REPO_ROOT" ]; then
    echo "에러: git 레포 안에서 실행해주세요."
    exit 1
  fi

  TARGET="$REPO_ROOT/.claude"
  echo ""
  echo "=== 로컬 설치 → $TARGET ==="

  # 임시 디렉토리에 클론 후 필요한 것만 복사
  TMP_DIR=$(mktemp -d)
  git clone --depth 1 "$REPO" "$TMP_DIR" 2>/dev/null

  mkdir -p "$TARGET"

  # 복사할 항목
  echo "[1/2] 설정 파일 복사"
  for dir in agents commands rules; do
    if [ -d "$TMP_DIR/$dir" ]; then
      cp -r "$TMP_DIR/$dir" "$TARGET/"
      echo "  $dir/ 복사됨"
    fi
  done

  echo "[2/2] 정리"
  rm -rf "$TMP_DIR"

  echo ""
  echo "=== 로컬 설치 완료! ==="
  echo ""
  echo "설치 경로: $TARGET/"
  echo "포함: agents/ commands/ rules/"
fi

# =============================================================
# ai-worklog 설치
# =============================================================
echo ""
echo "=== ai-worklog 설치 ==="
TMP_WL=$(mktemp -d)
git clone --depth 1 "$WORKLOG_REPO" "$TMP_WL"
bash "$TMP_WL/install.sh"
rm -rf "$TMP_WL"
