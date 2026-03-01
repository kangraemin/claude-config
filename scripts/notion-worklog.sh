#!/bin/bash
# Notion API로 워크로그 엔트리를 DB에 생성
# Usage: notion-worklog.sh <title> <date> <project> <tokens> <cost> <duration_min> <content>

set -euo pipefail

TITLE="${1:?title required}"
DATE="${2:?date required}"
PROJECT="${3:?project required}"
TOKENS="${4:-0}"
COST="${5:-0}"
DURATION="${6:-0}"
CONTENT="${7:-}"

if [ -z "${NOTION_TOKEN:-}" ] || [ -z "${NOTION_DB_ID:-}" ]; then
  echo "ERROR: NOTION_TOKEN and NOTION_DB_ID required" >&2
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
        'Project': {'select': {'name': sys.argv[4]}},
        'Tokens': {'number': int(sys.argv[5])},
        'Cost': {'number': float(sys.argv[6])},
        'Duration': {'number': int(sys.argv[7])}
    },
    'children': json.loads(sys.argv[8])
}
print(json.dumps(data))
" "$NOTION_DB_ID" "$TITLE" "$DATE" "$PROJECT" "$TOKENS" "$COST" "$DURATION" "$CHILDREN_JSON")

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
