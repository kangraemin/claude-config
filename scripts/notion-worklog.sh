#!/bin/bash
# Notion API로 워크로그 엔트리를 DB에 저장 (날짜별 1페이지)
# Usage: notion-worklog.sh <title> <date> <project> <cost> <duration_min> <model> <content>
#   - date에 이미 엔트리가 있으면 기존 페이지에 append (Cost/Duration 누적)
#   - 없으면 새 페이지 생성 (title = date)

set -euo pipefail

# 글로벌 .env에서 NOTION_TOKEN 로딩
ENV_FILE="$HOME/.claude/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

TITLE="${1:?title required}"
DATE="${2:?date required}"
PROJECT="${3:?project required}"
COST="${4:-0}"
DURATION="${5:-0}"
MODEL="${6:-claude-opus-4-6}"
CONTENT="${7:-}"

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
import sys, json

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

# date에 기존 페이지가 있는지 확인
EXISTING=$(python3 - "$NOTION_DB_ID" "$DATE" "$NOTION_TOKEN" <<'PYEOF'
import sys, json
import urllib.request, urllib.error

db_id = sys.argv[1]
date  = sys.argv[2]
token = sys.argv[3]

payload = json.dumps({
    "filter": {
        "property": "Date",
        "date": {"equals": date}
    }
}).encode()

req = urllib.request.Request(
    f"https://api.notion.com/v1/databases/{db_id}/query",
    data=payload,
    headers={
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    },
    method="POST"
)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    results = data.get("results", [])
    if results:
        p            = results[0]
        pid          = p["id"]
        cur_cost     = p["properties"].get("Cost",     {}).get("number", 0) or 0
        cur_duration = p["properties"].get("Duration", {}).get("number", 0) or 0
        print(f"{pid}|{cur_cost}|{cur_duration}")
    else:
        print("")
except Exception as e:
    print("", file=sys.stderr)
    raise
PYEOF
)

if [ -n "$EXISTING" ]; then
  # ── 기존 페이지에 append ───────────────────────────────────────────────────
  PAGE_ID=$(echo "$EXISTING" | cut -d'|' -f1)
  CUR_COST=$(echo "$EXISTING" | cut -d'|' -f2)
  CUR_DUR=$(echo "$EXISTING"  | cut -d'|' -f3)

  NEW_COST=$(python3 -c "print(round($CUR_COST + $COST, 3))")
  NEW_DUR=$(python3  -c "print(int($CUR_DUR  + $DURATION))")

  # 구분선 + 새 블록
  APPEND_JSON=$(python3 - "$CHILDREN_JSON" <<'PYEOF'
import sys, json
blocks  = json.loads(sys.argv[1])
divider = {"object": "block", "type": "divider", "divider": {}}
print(json.dumps([divider] + blocks))
PYEOF
)

  # 블록 추가
  RESP=$(curl -s -w "\n%{http_code}" -X PATCH \
    "https://api.notion.com/v1/blocks/${PAGE_ID}/children" \
    -H "Authorization: Bearer $NOTION_TOKEN" \
    -H "Notion-Version: 2022-06-28" \
    -H "Content-Type: application/json" \
    -d "{\"children\": $APPEND_JSON}")

  HTTP_CODE=$(echo "$RESP" | tail -1)
  if [ "$HTTP_CODE" != "200" ]; then
    echo "FAIL: append blocks HTTP $HTTP_CODE" >&2
    echo "$RESP" | sed '$d' >&2
    exit 1
  fi

  # Cost / Duration 누적 업데이트
  PROPS_RESP=$(curl -s -w "\n%{http_code}" -X PATCH \
    "https://api.notion.com/v1/pages/${PAGE_ID}" \
    -H "Authorization: Bearer $NOTION_TOKEN" \
    -H "Notion-Version: 2022-06-28" \
    -H "Content-Type: application/json" \
    -d "{\"properties\":{\"Cost\":{\"number\":$NEW_COST},\"Duration\":{\"number\":$NEW_DUR}}}")

  HTTP_CODE=$(echo "$PROPS_RESP" | tail -1)
  if [ "$HTTP_CODE" != "200" ]; then
    echo "FAIL: update properties HTTP $HTTP_CODE" >&2
    echo "$PROPS_RESP" | sed '$d' >&2
    exit 1
  fi

  echo "OK"

else
  # ── 새 페이지 생성 (title = date) ─────────────────────────────────────────
  PAYLOAD=$(python3 - "$NOTION_DB_ID" "$DATE" "$PROJECT" "$COST" "$DURATION" "$MODEL" "$CHILDREN_JSON" <<'PYEOF'
import json, sys
data = {
    'parent': {'database_id': sys.argv[1]},
    'icon': {'type': 'emoji', 'emoji': '📖'},
    'properties': {
        'Title': {'title': [{'text': {'content': sys.argv[2]}}]},
        'Date':  {'date': {'start': sys.argv[2]}},
        'Project': {'select': {'name': sys.argv[3]}},
        'Cost':    {'number': round(float(sys.argv[4]), 3)},
        'Duration': {'number': int(sys.argv[5])},
        'Model':   {'select': {'name': sys.argv[6]}},
    },
    'children': json.loads(sys.argv[7])
}
print(json.dumps(data))
PYEOF
)

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
fi
