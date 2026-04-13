#!/bin/bash
# Library용 Notion DB 자동 생성
# Usage: notion-library-create-db.sh <parent_page_id>
#
# 환경변수:
#   NOTION_TOKEN  Notion API 토큰 (필수)

set -euo pipefail

PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || echo python3)

# .env 로드
for _envfile in "$HOME/.claude/.env" ${AI_WORKLOG_DIR:+"$AI_WORKLOG_DIR/.env"}; do
  [ -f "$_envfile" ] && { set -a; source "$_envfile"; set +a; }
done

PARENT_PAGE_ID="${1:?parent_page_id required}"

if [ -z "${NOTION_TOKEN:-}" ]; then
  echo "ERROR: NOTION_TOKEN required (set in .env)" >&2
  exit 1
fi

# 하이픈 제거
PARENT_PAGE_ID=$(echo "$PARENT_PAGE_ID" | tr -d '-')

PAYLOAD=$($PYTHON -c "
import json
data = {
    'parent': {'type': 'page_id', 'page_id': '$PARENT_PAGE_ID'},
    'icon': {'type': 'emoji', 'emoji': '📚'},
    'title': [{'type': 'text', 'text': {'content': 'AI Library'}}],
    'properties': {
        'Title':       {'title': {}},
        'Category':    {'select': {'options': []}},
        'Subcategory': {'select': {'options': []}},
        'Topic':       {'select': {'options': []}},
        'Path':        {'rich_text': {}},
        'Tags':        {'multi_select': {'options': []}},
        'Created':     {'date': {}},
    }
}
print(json.dumps(data))
")

RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 30 -X POST "https://api.notion.com/v1/databases" \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
  DB_ID=$(echo "$BODY" | $PYTHON -c "import json,sys; print(json.load(sys.stdin)['id'])")
  echo "$DB_ID"
else
  echo "FAIL: HTTP $HTTP_CODE" >&2
  echo "$BODY" >&2
  exit 1
fi
