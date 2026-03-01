#!/bin/bash
# Notion에 워크로그 DB를 생성하고 ID를 출력
# Usage: notion-create-db.sh <project_name> [parent_page_id] [db_title]
# Output: DB ID (stdout)

set -euo pipefail

# 글로벌 .env 로딩
ENV_FILE="$HOME/.claude/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

PROJECT="${1:?project name required}"
PARENT_PAGE_ID="${2:-${NOTION_PARENT_PAGE_ID:-}}"
CUSTOM_TITLE="${3:-${NOTION_DB_TITLE:-}}"

if [ -z "${NOTION_TOKEN:-}" ]; then
  echo "ERROR: NOTION_TOKEN required" >&2
  exit 1
fi

# 부모 페이지가 없으면 검색해서 첫 번째 페이지 사용
if [ -z "$PARENT_PAGE_ID" ]; then
  PARENT_PAGE_ID=$(curl -s -X POST "https://api.notion.com/v1/search" \
    -H "Authorization: Bearer $NOTION_TOKEN" \
    -H "Notion-Version: 2022-06-28" \
    -H "Content-Type: application/json" \
    -d '{"filter":{"property":"object","value":"page"},"page_size":1}' \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('results', [])
print(results[0]['id'] if results else '')
")
  if [ -z "$PARENT_PAGE_ID" ]; then
    echo "ERROR: No accessible Notion page found. Connect integration to a page first." >&2
    exit 1
  fi
fi

# DB 이름: 커스텀 제목 > NOTION_DB_TITLE env > 기본값 "{project}) worklog"
DB_TITLE="${CUSTOM_TITLE:-${PROJECT}) worklog}"

PAYLOAD=$(python3 - "$PARENT_PAGE_ID" "$DB_TITLE" <<'PYEOF'
import json, sys
data = {
    'parent': {'page_id': sys.argv[1]},
    'title': [{'text': {'content': sys.argv[2]}}],
    'properties': {
        'Title': {'title': {}},
        'Date': {'date': {}},
        'Project': {'select': {'options': []}},
        'Tokens': {'number': {'format': 'number_with_commas'}},
        'Cost': {'number': {'format': 'dollar'}},
        'Duration': {'number': {'format': 'number'}},
        'Model': {'select': {'options': []}},
        'Daily Tokens': {'number': {'format': 'number_with_commas'}},
        'Daily Cost': {'number': {'format': 'dollar'}}
    }
}
print(json.dumps(data))
PYEOF
)

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "https://api.notion.com/v1/databases" \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
  DB_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
  echo "$DB_ID"
else
  echo "ERROR: Failed to create DB (HTTP $HTTP_CODE)" >&2
  echo "$BODY" >&2
  exit 1
fi
