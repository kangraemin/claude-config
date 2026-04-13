#!/bin/bash
# learnings-for-claude 자동 업데이트 체커
# Usage: update-check.sh [--force] [--check-only]

set -euo pipefail

REPO="kangraemin/learnings-for-claude"
API_URL="https://api.github.com/repos/$REPO/commits/main"
RAW_BASE="https://raw.githubusercontent.com/$REPO/main"

HOOK_DIR="$HOME/.claude/hooks"
VERSION_FILE="$HOOK_DIR/.learnings-version"
CHECKED_FILE="$HOOK_DIR/.learnings-version-checked"
SELF="$HOOK_DIR/learnings-update-check.sh"

FORCE=false
CHECK_ONLY=false
for arg in "$@"; do
  case $arg in
    --force)      FORCE=true ;;
    --check-only) CHECK_ONLY=true ;;
  esac
done

# ── 누락 hook 검증 (매 세션) ──────────────────────────────────────────────────
PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || echo python3)

_ensure_hook() {
  local sf="$1" event="$2" cmd="$3" timeout="$4" is_async="$5" matcher="${6:-}"
  [ -f "$sf" ] || return 0
  [ -f "$cmd" ] || return 0
  local bn
  bn=$(basename "$cmd")
  grep -q "$bn" "$sf" 2>/dev/null && return 0
  $PYTHON -c "
import json, sys
sf, event, cmd = sys.argv[1], sys.argv[2], sys.argv[3]
timeout, is_async, matcher = int(sys.argv[4]), sys.argv[5] == 'true', sys.argv[6]
cfg = json.load(open(sf))
hooks = cfg.setdefault('hooks', {})
entries = hooks.setdefault(event, [])
hook = {'type': 'command', 'command': cmd, 'timeout': timeout}
if is_async:
    hook['async'] = True
entry = {'hooks': [hook]}
if matcher:
    entry['matcher'] = matcher
entries.append(entry)
with open(sf, 'w') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
    f.write('\n')
print('added')
" "$sf" "$event" "$cmd" "$timeout" "$is_async" "$matcher" >/dev/null 2>&1
  echo "✓  ${event} hook 등록: $bn" >&2
}

SETTINGS="$HOME/.claude/settings.json"
_ensure_hook "$SETTINGS" "SessionStart" "$HOOK_DIR/learnings-update-check.sh" 15 true  "" || true
_ensure_hook "$SETTINGS" "Stop"         "$HOOK_DIR/library-save-check.sh"     10 false "" || true

# 설치 확인
[ -f "$HOOK_DIR/library-sync.sh" ] || exit 0

# 24h throttle
if [ "$FORCE" = false ] && [ "$CHECK_ONLY" = false ] && [ -f "$CHECKED_FILE" ]; then
  LAST=$(cat "$CHECKED_FILE" 2>/dev/null || echo 0)
  NOW=$(date +%s)
  if [ $(( NOW - LAST )) -lt 86400 ]; then
    exit 0
  fi
fi

# 최신 SHA 조회
LATEST_SHA=$(curl -sf --max-time 5 "$API_URL" 2>/dev/null | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['sha'][:7])" 2>/dev/null) || exit 0

# 체크 타임스탬프 갱신
date +%s > "$CHECKED_FILE"

INSTALLED_SHA=$(cat "$VERSION_FILE" 2>/dev/null || echo "unknown")

if [ "$CHECK_ONLY" = true ]; then
  echo "installed: $INSTALLED_SHA"
  echo "latest:    $LATEST_SHA"
  [ "$LATEST_SHA" = "$INSTALLED_SHA" ] && echo "status: up-to-date" || echo "status: update-available"
  exit 0
fi

[ "$LATEST_SHA" = "$INSTALLED_SHA" ] && exit 0

# bootstrap: 자기 자신 먼저 업데이트
if [ "${_LEARNINGS_BOOTSTRAPPED:-}" != "1" ]; then
  SELF_TMP=$(mktemp)
  trap 'rm -f "$SELF_TMP"' EXIT
  if curl -sf --max-time 10 "$RAW_BASE/scripts/update-check.sh" -o "$SELF_TMP" 2>/dev/null && \
     [ -s "$SELF_TMP" ] && bash -n "$SELF_TMP" 2>/dev/null; then
    if ! cmp -s "$SELF_TMP" "$SELF" 2>/dev/null; then
      mv "$SELF_TMP" "$SELF"
      chmod +x "$SELF"
      trap - EXIT
      export _LEARNINGS_BOOTSTRAPPED=1
      exec bash "$SELF" --force
    fi
  fi
  rm -f "$SELF_TMP"
  trap - EXIT
fi

# git clone → update.sh 실행
CLONE_DIR=$(mktemp -d)
trap 'rm -rf "$CLONE_DIR"' EXIT

git clone --depth 1 "https://github.com/$REPO.git" "$CLONE_DIR/learnings-for-claude" -q 2>/dev/null || exit 0

bash "$CLONE_DIR/learnings-for-claude/update.sh" || exit 0

echo "learnings-for-claude $INSTALLED_SHA → $LATEST_SHA 업데이트 완료"
