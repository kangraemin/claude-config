#!/bin/bash
# Notion API로 library 지식 파일을 DB에 생성/업데이트
# Usage: notion-library.sh <file_path>
#   file_path: library/ 하위 상대 경로 (예: ml/backtest/sharpe-ratio.md)
#
# 환경변수:
#   NOTION_TOKEN          Notion API 토큰 (필수, .env에서 로드)
#   LIBRARY_NOTION_DB_ID  Library Notion DB ID (필수, settings.json env)
#   LIBRARY_ROOT          library 루트 경로 (기본: ~/.claude/.claude-library)

set -euo pipefail

PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || echo python3)

# .env 탐색
for _envfile in "$HOME/.claude/.env" ${AI_WORKLOG_DIR:+"$AI_WORKLOG_DIR/.env"}; do
  [ -f "$_envfile" ] && { set -a; source "$_envfile"; set +a; }
done

FILE_PATH="${1:?file_path required (relative to library/)}"
LIBRARY_ROOT="${LIBRARY_ROOT:-$HOME/.claude/.claude-library}"
FULL_PATH="$LIBRARY_ROOT/library/$FILE_PATH"

if [ ! -f "$FULL_PATH" ]; then
  echo "ERROR: $FULL_PATH not found" >&2
  exit 1
fi

if [ -z "${NOTION_TOKEN:-}" ]; then
  echo "ERROR: NOTION_TOKEN required (set in .env)" >&2
  exit 1
fi
if [ -z "${LIBRARY_NOTION_DB_ID:-}" ]; then
  echo "ERROR: LIBRARY_NOTION_DB_ID required (set in settings.json env)" >&2
  exit 1
fi

# 파일에서 메타데이터 추출 + Notion payload 생성
PAYLOAD=$($PYTHON - "$FULL_PATH" "$FILE_PATH" "$LIBRARY_NOTION_DB_ID" <<'PYEOF'
import sys, json, re, os

full_path = sys.argv[1]
rel_path  = sys.argv[2]
db_id     = sys.argv[3]

content = open(full_path, encoding='utf-8').read()
lines = content.split('\n')

# --- frontmatter 파싱 및 제거 ---
frontmatter = {}
body_start = 0
if lines and lines[0].strip() == '---':
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            body_start = i + 1
            break
        m = re.match(r'^(\w+):\s*(.+)', lines[i])
        if m:
            frontmatter[m.group(1)] = m.group(2).strip()

body_lines = lines[body_start:]

# 제목: frontmatter name > 첫 # 헤딩 > 파일명
title = frontmatter.get('name', '')
if not title:
    for line in body_lines:
        if line.startswith('# '):
            title = line[2:].strip()
            break
if not title:
    title = os.path.splitext(os.path.basename(rel_path))[0]

# 경로 파싱: category / [subcategory] / [topic] / file.md
# 3단계 (ml/lgbm/file.md): cat=ml, sub=lgbm, topic=없음
# 4단계 (dev/tooling/claude-code/file.md): cat=dev, sub=tooling, topic=claude-code
parts = rel_path.split('/')
category = parts[0] if len(parts) > 1 else 'uncategorized'
subcategory = parts[1] if len(parts) > 2 else ''
topic = parts[2] if len(parts) > 3 else ''

# 날짜 추출: frontmatter > 본문의 "날짜:" > git log
date_val = None
m = re.search(r'\d{4}-\d{2}-\d{2}', frontmatter.get('date', ''))
if m:
    date_val = m.group(0)
if not date_val:
    for line in body_lines:
        m = re.search(r'날짜:\s*(\d{4}-\d{2}-\d{2})', line)
        if m:
            date_val = m.group(1)
            break
if not date_val:
    import subprocess
    try:
        git_date = subprocess.check_output(
            ['git', '-C', os.path.dirname(full_path), 'log', '-1',
             '--format=%ai', '--', full_path],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        if git_date:
            date_val = git_date[:10]
    except:
        pass

# 태그: frontmatter tags > 본문의 "관련:" > index.md의 "관련:"
# 경로에서 마지막 slug만 추출 (finance/equity/leverage-etf-timing → leverage-etf-timing)
def extract_tags(raw_tags):
    return [t.strip().rstrip('/').split('/')[-1] for t in raw_tags if t.strip()]

tags = []
if 'tags' in frontmatter:
    tags = extract_tags(frontmatter['tags'].split(','))
if not tags:
    for line in body_lines:
        m = re.search(r'관련:\s*(.+)', line)
        if m:
            tags = extract_tags(m.group(1).split(','))
            break
if not tags:
    index_path = os.path.join(os.path.dirname(full_path), 'index.md')
    if os.path.isfile(index_path):
        for line in open(index_path, encoding='utf-8'):
            m = re.search(r'관련:\s*(.+)', line)
            if m:
                tags = extract_tags(m.group(1).split(','))
                break

# 본문 → Notion blocks (frontmatter 제외)
blocks = []
in_code_block = False
code_lines = []
code_lang = ''

for line in body_lines:
    stripped = line.strip()

    # 코드 블록 처리
    if stripped.startswith('```'):
        if in_code_block:
            # 코드 블록 종료
            blocks.append({
                'object': 'block', 'type': 'code',
                'code': {
                    'rich_text': [{'text': {'content': '\n'.join(code_lines)[:2000]}}],
                    'language': code_lang or 'plain text'
                }
            })
            code_lines = []
            code_lang = ''
            in_code_block = False
        else:
            # 코드 블록 시작
            in_code_block = True
            lang = stripped[3:].strip()
            lang_map = {'bash': 'bash', 'sh': 'bash', 'python': 'python',
                        'json': 'json', 'js': 'javascript', 'typescript': 'typescript',
                        'yaml': 'yaml', 'sql': 'sql', 'go': 'go', 'rust': 'rust',
                        'java': 'java', 'kotlin': 'kotlin', 'swift': 'swift',
                        'html': 'html', 'css': 'css', 'markdown': 'markdown'}
            code_lang = lang_map.get(lang, 'plain text')
        continue

    if in_code_block:
        code_lines.append(line.rstrip())
        continue

    if not stripped:
        continue

    text = stripped[:2000]

    if stripped.startswith('### '):
        blocks.append({
            'object': 'block', 'type': 'heading_3',
            'heading_3': {'rich_text': [{'text': {'content': text[4:]}}]}
        })
    elif stripped.startswith('## '):
        blocks.append({
            'object': 'block', 'type': 'heading_2',
            'heading_2': {'rich_text': [{'text': {'content': text[3:]}}]}
        })
    elif stripped.startswith('# '):
        blocks.append({
            'object': 'block', 'type': 'heading_1',
            'heading_1': {'rich_text': [{'text': {'content': text[2:]}}]}
        })
    elif stripped.startswith('- '):
        blocks.append({
            'object': 'block', 'type': 'bulleted_list_item',
            'bulleted_list_item': {'rich_text': [{'text': {'content': text[2:]}}]}
        })
    else:
        blocks.append({
            'object': 'block', 'type': 'paragraph',
            'paragraph': {'rich_text': [{'text': {'content': text}}]}
        })

# properties
props = {
    'Title':    {'title': [{'text': {'content': title}}]},
    'Category': {'select': {'name': category}},
    'Path':     {'rich_text': [{'text': {'content': rel_path}}]},
}

if subcategory:
    props['Subcategory'] = {'select': {'name': subcategory}}

if topic:
    props['Topic'] = {'select': {'name': topic}}

if date_val:
    props['Created'] = {'date': {'start': date_val}}

if tags:
    props['Tags'] = {'multi_select': [{'name': t} for t in tags[:10]]}

data = {
    'parent': {'database_id': db_id},
    'icon': {'type': 'emoji', 'emoji': '📚'},
    'properties': props,
    'children': blocks[:100]  # Notion 100 block limit
}

print(json.dumps(data))
PYEOF
)

# 중복 체크: 같은 Path가 이미 있으면 archive 후 새로 생성
EXISTING=$($PYTHON - "$LIBRARY_NOTION_DB_ID" "$FILE_PATH" "$NOTION_TOKEN" <<'PYEOF'
import sys, json, urllib.request

db_id = sys.argv[1]
path  = sys.argv[2]
token = sys.argv[3]

query = {
    'filter': {
        'property': 'Path',
        'rich_text': {'equals': path}
    }
}

req = urllib.request.Request(
    f'https://api.notion.com/v1/databases/{db_id}/query',
    data=json.dumps(query).encode(),
    headers={
        'Authorization': f'Bearer {token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }
)

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        results = json.load(resp).get('results', [])
        for r in results:
            print(r['id'])
except:
    pass
PYEOF
) || true

# 기존 페이지 archive
if [ -n "$EXISTING" ]; then
  while IFS= read -r page_id; do
    [ -z "$page_id" ] && continue
    curl -s --max-time 10 -X PATCH "https://api.notion.com/v1/pages/$page_id" \
      -H "Authorization: Bearer $NOTION_TOKEN" \
      -H "Notion-Version: 2022-06-28" \
      -H "Content-Type: application/json" \
      -d '{"archived": true}' >/dev/null 2>&1 || true
  done <<< "$EXISTING"
fi

# 새 페이지 생성
RESPONSE=$(curl -s --connect-timeout 10 --max-time 30 -w "\n%{http_code}" -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
  echo "OK: $FILE_PATH"
else
  echo "FAIL: HTTP $HTTP_CODE — $FILE_PATH" >&2
  echo "$BODY" >&2
  exit 1
fi
