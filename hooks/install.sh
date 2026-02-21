#!/bin/bash
# Claude Code 워크로그 + 토큰 추적 훅 설치 스크립트
# 사용법: curl -sL <URL> | bash  또는  bash install.sh

set -e

HOOKS_DIR="$HOME/.claude/hooks"
WORKLOGS_DIR="$HOME/.claude/worklogs"
SETTINGS="$HOME/.claude/settings.json"

echo "🔧 Claude Code 워크로그 시스템 설치 중..."

# 디렉토리 생성
mkdir -p "$HOOKS_DIR" "$WORKLOGS_DIR"

# --- 1. PostToolUse 훅: 도구 사용 수집 ---
cat > "$HOOKS_DIR/worklog.sh" << 'SCRIPT'
#!/bin/bash
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')
TOOL_INPUT=$(echo "$INPUT" | jq -c '.tool_input // {}')
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

COLLECT_DIR="$HOME/.claude/worklogs/.collecting"
mkdir -p "$COLLECT_DIR"
echo "{\"ts\":\"$TIMESTAMP\",\"tool\":\"$TOOL_NAME\",\"input\":$TOOL_INPUT}" >> "$COLLECT_DIR/$SESSION_ID.jsonl"
exit 0
SCRIPT

# --- 2. SessionEnd 훅: 마크다운 보고서 생성 ---
cat > "$HOOKS_DIR/session-end.sh" << 'SCRIPT'
#!/bin/bash
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
CWD=$(echo "$INPUT" | jq -r '.cwd')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // ""')
DATE=$(date +"%Y-%m-%d")
TIME=$(date +"%H:%M")

PROJECT=$(basename "$CWD")
LOG_DIR="$HOME/.claude/worklogs/$DATE"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/${TIME}_${PROJECT}_${SESSION_ID:0:8}.md"
COLLECT_FILE="$HOME/.claude/worklogs/.collecting/$SESSION_ID.jsonl"

# 토큰
TOTAL_INPUT=0; TOTAL_OUTPUT=0; CACHE_READ=0; CACHE_CREATE=0
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  TOTAL_INPUT=$(jq -s '[.[].message.usage.input_tokens // 0] | add // 0' "$TRANSCRIPT" 2>/dev/null || echo 0)
  TOTAL_OUTPUT=$(jq -s '[.[].message.usage.output_tokens // 0] | add // 0' "$TRANSCRIPT" 2>/dev/null || echo 0)
  CACHE_READ=$(jq -s '[.[].message.usage.cache_read_input_tokens // 0] | add // 0' "$TRANSCRIPT" 2>/dev/null || echo 0)
  CACHE_CREATE=$(jq -s '[.[].message.usage.cache_creation_input_tokens // 0] | add // 0' "$TRANSCRIPT" 2>/dev/null || echo 0)
fi

# 사용자 요청
USER_MESSAGES=""
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  USER_MESSAGES=$(jq -r '
    select(.type == "human" or .role == "user") |
    if .message.content then
      if (.message.content | type) == "string" then .message.content
      elif (.message.content | type) == "array" then
        [.message.content[] | select(.type == "text") | .text] | join("\n")
      else empty end
    elif .content then
      if (.content | type) == "string" then .content
      elif (.content | type) == "array" then
        [.content[] | select(.type == "text") | .text] | join("\n")
      else empty end
    else empty end
  ' "$TRANSCRIPT" 2>/dev/null | head -c 3000)
fi

# 도구 통계
TOOL_STATS=""
[ -f "$COLLECT_FILE" ] && TOOL_STATS=$(jq -r '.tool' "$COLLECT_FILE" 2>/dev/null | sort | uniq -c | sort -rn)

# 변경된 파일
CHANGED_FILES=""
[ -f "$COLLECT_FILE" ] && CHANGED_FILES=$(jq -r 'select(.tool == "Write" or .tool == "Edit") | .input.file_path // .input.path // empty' "$COLLECT_FILE" 2>/dev/null | sort -u)

# Bash 명령어
BASH_COMMANDS=""
[ -f "$COLLECT_FILE" ] && BASH_COMMANDS=$(jq -r 'select(.tool == "Bash") | .input.command // empty' "$COLLECT_FILE" 2>/dev/null | head -30)

cat > "$LOG_FILE" << REPORT
# Worklog: $PROJECT
- **날짜**: $DATE $TIME
- **세션**: \`$SESSION_ID\`
- **경로**: $CWD

## 토큰 사용량
| 항목 | 토큰 수 |
|------|---------|
| Input | $TOTAL_INPUT |
| Output | $TOTAL_OUTPUT |
| Cache Read | $CACHE_READ |
| Cache Create | $CACHE_CREATE |
| **합계** | **$(($TOTAL_INPUT + $TOTAL_OUTPUT))** |

## 사용자 요청
\`\`\`
$USER_MESSAGES
\`\`\`

## 도구 사용 통계
\`\`\`
$TOOL_STATS
\`\`\`

## 변경된 파일
\`\`\`
${CHANGED_FILES:-없음}
\`\`\`

## 실행된 명령어
\`\`\`
${BASH_COMMANDS:-없음}
\`\`\`
REPORT

rm -f "$COLLECT_FILE"
echo "- [$TIME $PROJECT](./${TIME}_${PROJECT}_${SESSION_ID:0:8}.md) — in:$TOTAL_INPUT out:$TOTAL_OUTPUT" >> "$LOG_DIR/index.md"
exit 0
SCRIPT

# --- 3. 워크로그 조회 스크립트 ---
cat > "$HOOKS_DIR/view-worklog.sh" << 'SCRIPT'
#!/bin/bash
DATE=${1:-$(date +"%Y-%m-%d")}
LOG_DIR="$HOME/.claude/worklogs"

if [ "$DATE" = "latest" ]; then
  LATEST=$(find "$LOG_DIR" -name "*.md" ! -name "index.md" -type f | sort | tail -1)
  [ -n "$LATEST" ] && cat "$LATEST" || echo "워크로그 없음"
  exit 0
fi

INDEX="$LOG_DIR/$DATE/index.md"
if [ ! -f "$INDEX" ]; then
  echo "워크로그 없음: $DATE"
  echo "사용 가능한 날짜:"
  ls "$LOG_DIR" 2>/dev/null | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
  exit 0
fi

echo "=== $DATE 워크로그 ==="
echo ""
cat "$INDEX"
echo ""
echo "상세: cat ~/.claude/worklogs/$DATE/<파일명>.md"
SCRIPT

chmod +x "$HOOKS_DIR/worklog.sh" "$HOOKS_DIR/session-end.sh" "$HOOKS_DIR/view-worklog.sh"

# --- 4. settings.json 업데이트 ---
if [ -f "$SETTINGS" ]; then
  # 기존 설정에 hooks 병합
  EXISTING=$(cat "$SETTINGS")
  echo "$EXISTING" | jq '.hooks = {
    "PostToolUse": [{"hooks": [{"type": "command", "command": "$HOME/.claude/hooks/worklog.sh", "timeout": 5, "async": true}]}],
    "SessionEnd": [{"hooks": [{"type": "command", "command": "$HOME/.claude/hooks/session-end.sh", "timeout": 15}]}]
  }' > "$SETTINGS"
else
  cat > "$SETTINGS" << 'SETTINGS_JSON'
{
  "hooks": {
    "PostToolUse": [{"hooks": [{"type": "command", "command": "$HOME/.claude/hooks/worklog.sh", "timeout": 5, "async": true}]}],
    "SessionEnd": [{"hooks": [{"type": "command", "command": "$HOME/.claude/hooks/session-end.sh", "timeout": 15}]}]
  }
}
SETTINGS_JSON
fi

echo ""
echo "✅ 설치 완료!"
echo ""
echo "📁 훅 스크립트: $HOOKS_DIR/"
echo "📁 워크로그:    $WORKLOGS_DIR/"
echo ""
echo "조회 명령어:"
echo "  ~/.claude/hooks/view-worklog.sh          # 오늘"
echo "  ~/.claude/hooks/view-worklog.sh latest   # 최근 세션"
echo "  ~/.claude/hooks/view-worklog.sh 2026-02-21  # 특정 날짜"
