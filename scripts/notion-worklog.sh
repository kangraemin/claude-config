#!/bin/bash
# Notion API로 워크로그 엔트리를 DB에 생성
# Usage: notion-worklog.sh <title> <date> <project> <tokens> <cost> <duration_min> <model> <daily_tokens> <daily_cost> <content>

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
PROJECT="${3:?project required}"
TOKENS="${4:-0}"
COST="${5:-0}"
DURATION="${6:-0}"
MODEL="${7:-claude-opus-4-6}"
DAILY_TOKENS="${8:-0}"
DAILY_COST="${9:-0}"
CONTENT="${10:-}"

if [ -z "${NOTION_TOKEN:-}" ]; then
  echo "ERROR: NOTION_TOKEN required (set in ~/.claude/.env or env)" >&2
  exit 1
fi
if [ -z "${NOTION_DB_ID:-}" ]; then
  echo "ERROR: NOTION_DB_ID required (set in settings.json env)" >&2
  exit 1
fi

# 본문을 Notion blocks JSON으로 변환 (마크다운 → heading/bullet/paragraph)
CHILDREN_JSON=$(python3 - "$CONTENT" <<'PYEOF'
import sys, json, re

content = sys.argv[1] if len(sys.argv) > 1 else ''
blocks = []

for line in content.split('\n'):
    stripped = line.strip()
    if not stripped:
        continue

    text = stripped[:2000]

    if stripped.startswith('### '):
        blocks.append({
            'object': 'block',
            'type': 'heading_3',
            'heading_3': {'rich_text': [{'text': {'content': text[4:]}}]}
        })
    elif stripped.startswith('## '):
        blocks.append({
            'object': 'block',
            'type': 'heading_2',
            'heading_2': {'rich_text': [{'text': {'content': text[3:]}}]}
        })
    elif stripped.startswith('# '):
        blocks.append({
            'object': 'block',
            'type': 'heading_1',
            'heading_1': {'rich_text': [{'text': {'content': text[2:]}}]}
        })
    elif stripped.startswith('- '):
        blocks.append({
            'object': 'block',
            'type': 'bulleted_list_item',
            'bulleted_list_item': {'rich_text': [{'text': {'content': text[2:]}}]}
        })
    else:
        blocks.append({
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {'rich_text': [{'text': {'content': text}}]}
        })

print(json.dumps(blocks))
PYEOF
)

# API 페이로드 생성
PAYLOAD=$(python3 - "$NOTION_DB_ID" "$TITLE" "$DATE" "$PROJECT" "$TOKENS" "$COST" "$DURATION" "$MODEL" "$DAILY_TOKENS" "$DAILY_COST" "$CHILDREN_JSON" <<'PYEOF'
import json, sys
data = {
    'parent': {'database_id': sys.argv[1]},
    'icon': {'type': 'emoji', 'emoji': '📖'},
    'properties': {
        'Title': {'title': [{'text': {'content': sys.argv[2]}}]},
        'Date': {'date': {'start': sys.argv[3]}},
        'Project': {'select': {'name': sys.argv[4]}},
        'Tokens': {'number': int(sys.argv[5])},
        'Cost': {'number': float(sys.argv[6])},
        'Duration': {'number': int(sys.argv[7])},
        'Model': {'select': {'name': sys.argv[8]}},
        'Daily Tokens': {'number': int(sys.argv[9])},
        'Daily Cost': {'number': float(sys.argv[10])}
    },
    'children': json.loads(sys.argv[11])
}
print(json.dumps(data))
PYEOF
)

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
