#!/bin/bash
# Claude Code 설정 설치 스크립트
#
# 전역 설치: bash <(curl -sL https://raw.githubusercontent.com/kangraemin/claude-config/main/install.sh)
# 로컬 설치: bash <(curl -sL https://raw.githubusercontent.com/kangraemin/claude-config/main/install.sh) --local

set -e

REPO="https://github.com/kangraemin/claude-config.git"
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
    echo "[1/4] 기존 설정 백업"
    mkdir -p "$BACKUP"
    for item in projects worklogs plugins cache; do
      [ -d "$TARGET/$item" ] && mv "$TARGET/$item" "$BACKUP/"
    done
    [ -f "$TARGET/statsig_user_id" ] && mv "$TARGET/statsig_user_id" "$BACKUP/"
    [ -f "$TARGET/settings.json" ] && cp "$TARGET/settings.json" "$BACKUP/settings.json.bak"
    rm -rf "$TARGET"
  else
    echo "[1/4] 기존 설정 없음"
    mkdir -p "$BACKUP"
  fi

  # 클론
  echo "[2/4] 클론"
  git clone "$REPO" "$TARGET"

  # 복원
  echo "[3/4] 데이터 복원"
  for item in projects worklogs plugins cache; do
    [ -d "$BACKUP/$item" ] && mv "$BACKUP/$item" "$TARGET/"
  done
  [ -f "$BACKUP/statsig_user_id" ] && mv "$BACKUP/statsig_user_id" "$TARGET/"
  mkdir -p "$TARGET/worklogs/.collecting"

  # 권한
  echo "[4/5] 실행 권한 및 git hooks 설정"
  chmod +x "$TARGET/hooks/"*.sh 2>/dev/null || true
  chmod +x "$TARGET/git-hooks/"* 2>/dev/null || true
  git config --global core.hooksPath "$TARGET/git-hooks"


  rmdir "$BACKUP" 2>/dev/null || true

  # ── 현재 git repo에 hook 직접 설치 ─────────────────────────────────
  _install_hook_to_repo() {
    local repo_root="$1"
    local hook_src="$TARGET/git-hooks/post-commit"
    local hook_dst="$repo_root/.git/hooks/post-commit"
    [ -d "$repo_root/.git/hooks" ] || return 0
    [ -f "$hook_src" ] || return 0
    # 기존 hook 백업
    if [ -f "$hook_dst" ] && ! grep -q "ai-worklog" "$hook_dst" 2>/dev/null; then
      mv "$hook_dst" "$hook_dst.local"
      echo "  기존 hook → post-commit.local로 백업"
    fi
    cp "$hook_src" "$hook_dst"
    chmod +x "$hook_dst"
  }
  CURRENT_REPO=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
  if [ -n "$CURRENT_REPO" ]; then
    _install_hook_to_repo "$CURRENT_REPO"
    echo "  post-commit hook → $CURRENT_REPO/.git/hooks/ 설치 완료"
  fi

  echo ""
  echo "=== 전역 설치 완료! ==="
  echo ""
  echo "포함: agents/ commands/ rules/ hooks/ git-hooks/"
  echo "git hooksPath: $TARGET/git-hooks"
  echo "업데이트: cd ~/.claude && git pull"
  echo ""
  echo "💡 Claude Code 세션에서는 /worklog 또는 /finish로 워크로그를 작성하세요."

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
  echo "[1/3] 설정 파일 복사"
  for dir in agents commands rules; do
    if [ -d "$TMP_DIR/$dir" ]; then
      cp -r "$TMP_DIR/$dir" "$TARGET/"
      echo "  $dir/ 복사됨"
    fi
  done

  # hooks, scripts 복사 (워크로그 기능용)
  for dir in hooks git-hooks scripts; do
    if [ -d "$TMP_DIR/$dir" ]; then
      cp -r "$TMP_DIR/$dir" "$TARGET/"
      echo "  $dir/ 복사됨"
    fi
  done
  chmod +x "$TARGET/hooks/"*.sh 2>/dev/null || true
  chmod +x "$TARGET/git-hooks/"* 2>/dev/null || true
  chmod +x "$TARGET/scripts/"*.sh 2>/dev/null || true

  # git repo에 hook 직접 설치
  HOOK_SRC="$TARGET/git-hooks/post-commit"
  HOOK_DST="$REPO_ROOT/.git/hooks/post-commit"
  if [ -f "$HOOK_SRC" ]; then
    if [ -f "$HOOK_DST" ] && ! grep -q "ai-worklog" "$HOOK_DST" 2>/dev/null; then
      mv "$HOOK_DST" "$HOOK_DST.local"
      echo "  기존 hook → post-commit.local로 백업"
    fi
    cp "$HOOK_SRC" "$HOOK_DST"
    chmod +x "$HOOK_DST"
    echo "  post-commit hook → .git/hooks/ 설치 완료"
  fi

  echo "[2/3] 정리"
  rm -rf "$TMP_DIR"

  echo "[3/3] 완료"
  echo ""
  echo "=== 로컬 설치 완료! ==="
  echo ""
  echo "설치 경로: $TARGET/"
  echo "포함: agents/ commands/ rules/ hooks/ git-hooks/ scripts/"
  echo ""
  echo "💡 Claude Code 세션에서는 /worklog 또는 /finish로 워크로그를 작성하세요."
fi

# =============================================================
# Notion 연동 설정 (전역/로컬 공통)
# =============================================================
echo ""
read -p "Notion 워크로그 연동을 설정하시겠습니까? [y/N]: " SETUP_NOTION
if [ "$SETUP_NOTION" = "y" ] || [ "$SETUP_NOTION" = "Y" ]; then
  echo ""
  echo "=== Notion 연동 설정 ==="
  echo ""

  # ── NOTION_TOKEN ───────────────────────────────────────────
  ENV_FILE="$HOME/.claude/.env"
  EXISTING_TOKEN=""
  if [ -f "$ENV_FILE" ]; then
    EXISTING_TOKEN=$(grep '^NOTION_TOKEN=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-)
  fi

  if [ -n "$EXISTING_TOKEN" ]; then
    echo "NOTION_TOKEN: 이미 설정됨 (${EXISTING_TOKEN:0:8}...)"
  else
    echo "Notion Internal Integration 토큰이 필요합니다."
    echo "  → https://www.notion.so/my-integrations 에서 생성"
    echo ""
    read -p "NOTION_TOKEN: " INPUT_TOKEN
    if [ -n "$INPUT_TOKEN" ]; then
      mkdir -p "$(dirname "$ENV_FILE")"
      echo "NOTION_TOKEN=$INPUT_TOKEN" >> "$ENV_FILE"
      export NOTION_TOKEN="$INPUT_TOKEN"
      echo "  → $ENV_FILE 에 저장됨"
    else
      echo "토큰 미입력. Notion 설정을 건너뜁니다."
    fi
  fi

  # ── NOTION_DB_ID ───────────────────────────────────────────
  if [ -n "${NOTION_TOKEN:-}$EXISTING_TOKEN" ]; then
    export NOTION_TOKEN="${NOTION_TOKEN:-$EXISTING_TOKEN}"
    echo ""
    echo "Notion DB 설정:"
    echo "  1) 새 DB 자동 생성 (parent page ID 필요)"
    echo "  2) 기존 DB ID 입력"
    echo ""
    read -p "선택 [1/2]: " DB_CHOICE

    NOTION_DB_ID=""
    case "$DB_CHOICE" in
      1)
        echo ""
        echo "DB를 생성할 Notion 페이지의 URL 또는 ID를 입력하세요."
        echo "  (예: https://notion.so/My-Page-abc123... 또는 abc123...)"
        read -p "Parent page: " PARENT_INPUT
        # URL에서 ID 추출 (마지막 - 뒤 32자 또는 마지막 경로 세그먼트)
        PARENT_ID=$(echo "$PARENT_INPUT" | sed -E 's|.*/||; s|.*-||; s|\?.*||')
        if [ -n "$PARENT_ID" ]; then
          CREATE_SCRIPT="${TARGET:-$HOME/.claude}/scripts/notion-create-db.sh"
          if [ -f "$CREATE_SCRIPT" ]; then
            echo "DB 생성 중..."
            NOTION_DB_ID=$(bash "$CREATE_SCRIPT" "$PARENT_ID" 2>&1) || {
              echo "DB 생성 실패: $NOTION_DB_ID" >&2
              NOTION_DB_ID=""
            }
          else
            echo "notion-create-db.sh를 찾을 수 없습니다." >&2
          fi
        fi
        ;;
      2)
        read -p "NOTION_DB_ID: " NOTION_DB_ID
        ;;
    esac

    # settings.json에 NOTION_DB_ID 반영
    if [ -n "$NOTION_DB_ID" ]; then
      echo ""
      echo "NOTION_DB_ID: $NOTION_DB_ID"

      # 프로젝트 settings.json에 env 반영
      _update_settings_json() {
        local settings_file="$1"
        local db_id="$2"
        mkdir -p "$(dirname "$settings_file")"
        if [ -f "$settings_file" ]; then
          # 기존 파일에 env 병합
          python3 -c "
import json
with open('$settings_file') as f:
    cfg = json.load(f)
env = cfg.setdefault('env', {})
env['NOTION_DB_ID'] = '$db_id'
env['WORKLOG_DEST'] = env.get('WORKLOG_DEST', 'notion')
with open('$settings_file', 'w') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
    f.write('\n')
"
        else
          # 신규 생성
          python3 -c "
import json
cfg = {'env': {'NOTION_DB_ID': '$db_id', 'WORKLOG_DEST': 'notion'}}
with open('$settings_file', 'w') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
    f.write('\n')
"
        fi
      }

      # 글로벌 settings.json
      _update_settings_json "$HOME/.claude/settings.json" "$NOTION_DB_ID"
      echo "  → ~/.claude/settings.json 반영"

      # 현재 프로젝트 settings.json (git repo 안이면)
      PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
      if [ -n "$PROJECT_ROOT" ] && [ -d "$PROJECT_ROOT/.claude" ]; then
        _update_settings_json "$PROJECT_ROOT/.claude/settings.json" "$NOTION_DB_ID"
        echo "  → $PROJECT_ROOT/.claude/settings.json 반영"
      fi

      echo ""
      echo "✅ Notion 연동 설정 완료!"
    else
      echo "DB ID가 설정되지 않았습니다. 나중에 수동으로 settings.json에 NOTION_DB_ID를 추가하세요."
    fi
  fi
fi
