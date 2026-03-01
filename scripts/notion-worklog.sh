#!/bin/bash
# Notion API로 워크로그 엔트리를 DB에 생성
# Usage: notion-worklog.sh <title> <date> <tokens> <cost> <duration_min> <model> <daily_tokens> <daily_cost> <content>

set -euo pipefail

# 글로벌 .env에서 NOTION_TOKEN 로딩 (없으면 환경변수 사용)
ENV_FILE="$HOME/.claude/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

TITLE="${1:?title required}"
DATE="${2:?date required}"
TOKENS="${3:-0}"
COST="${4:-0}"
DURATION="${5:-0}"
MODEL="${6:-claude-opus-4-6}"
DAILY_TOKENS="${7:-0}"
DAILY_COST="${8:-0}"
CONTENT="${9:-}"

if [ -z "${NOTION_TOKEN:-}" ]; then
  echo "ERROR: NOTION_TOKEN required (set in ~/.claude/.env or env)" >&2
  exit 1
fi
if [ -z "${NOTION_DB_ID:-}" ]; then
  echo "ERROR: NOTION_DB_ID required (set in project settings.json env)" >&2
  exit 1
fi

# 본문을 Notion blocks JSON으로 변환
CHILDREN_JSON=$(python3 -c "
import sys, json
content = sys.argv[1] if len(sys.argv) > 1 else ''
blocks = []
for line in content.split('\n'):
    if line.strip():
        blocks.append({
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {'rich_text': [{'text': {'content': line[:2000]}}]}
        })
print(json.dumps(blocks))
" "$CONTENT")

# API 페이로드 생성
PAYLOAD=$(python3 -c "
import json, sys
data = {
    'parent': {'database_id': sys.argv[1]},
    'properties': {
        'Title': {'title': [{'text': {'content': sys.argv[2]}}]},
        'Date': {'date': {'start': sys.argv[3]}},
        'Tokens': {'number': int(sys.argv[4])},
        'Cost': {'number': float(sys.argv[5])},
        'Duration': {'number': int(sys.argv[6])},
        'Model': {'select': {'name': sys.argv[7]}},
        'Daily Tokens': {'number': int(sys.argv[8])},
        'Daily Cost': {'number': float(sys.argv[9])}
    },
    'children': json.loads(sys.argv[10])
}
print(json.dumps(data))
" "$NOTION_DB_ID" "$TITLE" "$DATE" "$TOKENS" "$COST" "$DURATION" "$MODEL" "$DAILY_TOKENS" "$DAILY_COST" "$CHILDREN_JSON")

# Notion API 호출
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
  echo "OK"
else
  echo "FAIL: HTTP $HTTP_CODE" >&2
  echo "$BODY" >&2
  exit 1
fi
