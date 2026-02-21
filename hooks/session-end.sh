#!/bin/bash
# SessionEnd: 트랜스크립트 + 수집 데이터 파싱 → 대화 요약 마크다운 생성

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
CWD=$(echo "$INPUT" | jq -r '.cwd')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // ""')
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DATE=$(date +"%Y-%m-%d")
TIME=$(date +"%H:%M")

PROJECT=$(basename "$CWD")
LOG_DIR="$HOME/.claude/worklogs/$DATE"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/${TIME}_${PROJECT}_${SESSION_ID:0:8}.md"

COLLECT_FILE="$HOME/.claude/worklogs/.collecting/$SESSION_ID.jsonl"

# --- 1. 토큰 사용량 ---
TOTAL_INPUT=0
TOTAL_OUTPUT=0
CACHE_READ=0
CACHE_CREATE=0
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  TOTAL_INPUT=$(jq -s '[.[].message.usage.input_tokens // 0] | add // 0' "$TRANSCRIPT" 2>/dev/null || echo 0)
  TOTAL_OUTPUT=$(jq -s '[.[].message.usage.output_tokens // 0] | add // 0' "$TRANSCRIPT" 2>/dev/null || echo 0)
  CACHE_READ=$(jq -s '[.[].message.usage.cache_read_input_tokens // 0] | add // 0' "$TRANSCRIPT" 2>/dev/null || echo 0)
  CACHE_CREATE=$(jq -s '[.[].message.usage.cache_creation_input_tokens // 0] | add // 0' "$TRANSCRIPT" 2>/dev/null || echo 0)
fi

# --- 2. 사용자 요청 추출 ---
USER_MESSAGES=""
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  USER_MESSAGES=$(jq -r '
    select(.type == "human" or .role == "user") |
    if .message.content then
      if (.message.content | type) == "string" then .message.content
      elif (.message.content | type) == "array" then
        [.message.content[] | select(.type == "text") | .text] | join("\n")
      else empty
      end
    elif .content then
      if (.content | type) == "string" then .content
      elif (.content | type) == "array" then
        [.content[] | select(.type == "text") | .text] | join("\n")
      else empty
      end
    else empty
    end
  ' "$TRANSCRIPT" 2>/dev/null | head -c 3000)
fi

# --- 3. 도구 사용 통계 ---
TOOL_STATS=""
if [ -f "$COLLECT_FILE" ]; then
  TOOL_STATS=$(jq -r '.tool' "$COLLECT_FILE" 2>/dev/null | sort | uniq -c | sort -rn)
fi

# --- 4. 변경된 파일 목록 ---
CHANGED_FILES=""
if [ -f "$COLLECT_FILE" ]; then
  # Write/Edit 도구에서 파일 경로 추출
  CHANGED_FILES=$(jq -r '
    select(.tool == "Write" or .tool == "Edit") |
    .input.file_path // .input.path // empty
  ' "$COLLECT_FILE" 2>/dev/null | sort -u)
fi

# --- 5. Bash 명령어 목록 ---
BASH_COMMANDS=""
if [ -f "$COLLECT_FILE" ]; then
  BASH_COMMANDS=$(jq -r '
    select(.tool == "Bash") | .input.command // empty
  ' "$COLLECT_FILE" 2>/dev/null | head -30)
fi

# --- 마크다운 보고서 생성 ---
cat > "$LOG_FILE" << REPORT
# Worklog: $PROJECT
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
${CHANGED_FILES:-변경된 파일 없음}
\`\`\`

## 실행된 명령어
\`\`\`
${BASH_COMMANDS:-실행된 명령어 없음}
\`\`\`
REPORT

# 임시 수집 파일 정리
rm -f "$COLLECT_FILE"

# 일별 인덱스 업데이트
INDEX="$HOME/.claude/worklogs/$DATE/index.md"
echo "- [$TIME $PROJECT](./${TIME}_${PROJECT}_${SESSION_ID:0:8}.md) — in:$TOTAL_INPUT out:$TOTAL_OUTPUT" >> "$INDEX"

exit 0
