#!/bin/bash
# 워크로그 생성 공통 스크립트
# 사용법: echo '{"session_id":"...","cwd":"...","transcript_path":"..."}' | generate-worklog.sh
# /commit, auto-commit.sh 등에서 호출

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
CWD=$(echo "$INPUT" | jq -r '.cwd')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // ""')
DATE=$(date +"%Y-%m-%d")
TIME=$(date +"%H:%M")

COLLECT_FILE="$HOME/.claude/worklogs/.collecting/$SESSION_ID.jsonl"

# git 레포 루트 감지
REPO_ROOT=$(cd "$CWD" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
  # git 레포가 아니면 스킵
  exit 0
fi

LOG_DIR="$REPO_ROOT/.worklogs/$DATE"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/${TIME}_${SESSION_ID:0:8}.md"

# 토큰 사용량
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
[ -f "$COLLECT_FILE" ] && CHANGED_FILES=$(jq -r '
  select(.tool == "Write" or .tool == "Edit") |
  .input.file_path // .input.path // empty
' "$COLLECT_FILE" 2>/dev/null | sort -u)

# Bash 명령어
BASH_COMMANDS=""
[ -f "$COLLECT_FILE" ] && BASH_COMMANDS=$(jq -r '
  select(.tool == "Bash") | .input.command // empty
' "$COLLECT_FILE" 2>/dev/null | head -30)

cat > "$LOG_FILE" << REPORT
# Worklog: $(basename "$REPO_ROOT")
- **날짜**: $DATE $TIME
- **세션**: \`$SESSION_ID\`
- **프로젝트 경로**: $CWD

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

# 워크로그 파일 경로 반환 (호출자가 git add 할 수 있도록)
echo "$LOG_FILE"
