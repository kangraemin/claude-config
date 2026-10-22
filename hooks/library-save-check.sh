#!/bin/bash

# Stop hook: 방금 응답에서 library 저장 대상 있는지 체크

command -v jq &>/dev/null || exit 0

INPUT=$(cat)
umask 077
EVENT=$(echo "$INPUT" | jq -r '.hook_event_name // "Stop"')

# 재진입 방지
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
[ "$STOP_HOOK_ACTIVE" = "true" ] && exit 0

# ralph-x in-session 루프 active이면 skip (루프 진행 우선)
CWD=$(echo "$INPUT" | jq -r '.cwd // ""')
if [ -n "$CWD" ]; then
  for sf in "$CWD"/ralph-x-runs/*/session-state.json; do
    [ -f "$sf" ] || continue
    if [ "$(jq -r '.active // false' "$sf")" = "true" ]; then
      exit 0
    fi
  done
fi

# 20번에 1번만 실행 (세션별 독립)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
[[ "$SESSION_ID" =~ ^[A-Za-z0-9_-]+$ ]] || exit 0
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // ""')
COUNTER_DIR="$HOME/.claude/hooks/.counters"
mkdir -p "$COUNTER_DIR" 2>/dev/null || exit 0
COUNTER_FILE="$COUNTER_DIR/.library-check-counter-$SESSION_ID"
MARKER_FILE="$HOME/.claude/hooks/.library-check-marker-$SESSION_ID"
PENDING_FILE="$HOME/.claude/hooks/.library-review-pending-$SESSION_ID.txt"
# 압축 발췌는 다음 Stop에서 카운터보다 우선한다.
if [ "$EVENT" != "PreCompact" ] && [ -s "$PENDING_FILE" ]; then
  EXCERPT_FILE=$(mktemp "$HOME/.claude/hooks/.library-review-excerpt-$SESSION_ID-XXXXXX") || exit 0
  mv "$PENDING_FILE" "$EXCERPT_FILE" || exit 0
else
if [ "$EVENT" != "PreCompact" ]; then
  COUNT=0
  [ -f "$COUNTER_FILE" ] && COUNT=$(cat "$COUNTER_FILE")
  [[ "$COUNT" =~ ^[0-9]+$ ]] || COUNT=0
  COUNT=$((COUNT + 1))
  echo "$COUNT" > "$COUNTER_FILE"
  [ $((COUNT % 20)) -ne 0 ] && exit 0
fi

# transcript 없거나 접근 불가 → skip
{ [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; } && exit 0

# 지난 리뷰 이후 새 대화만 추출 (증분, user/assistant 텍스트만)
MARKER=0
[ -f "$MARKER_FILE" ] && MARKER=$(cat "$MARKER_FILE")
[[ "$MARKER" =~ ^[0-9]+$ ]] || MARKER=0
TOTAL=$(wc -l < "$TRANSCRIPT" | tr -d ' ')
# 압축으로 transcript가 짧아졌으면 새 파일의 처음부터 읽는다.
[ "$MARKER" -gt "$TOTAL" ] && MARKER=0
EXCERPT_FILE=$(mktemp "$HOME/.claude/hooks/.library-review-excerpt-$SESSION_ID-XXXXXX") || exit 0

python3 - "$TRANSCRIPT" "$MARKER" "$TOTAL" "$EXCERPT_FILE" <<'PYEOF'
import json, sys
path, marker, total, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
parts = []
for l in lines[marker:total]:
    try: o = json.loads(l)
    except: continue
    if o.get('type') not in ('user', 'assistant'): continue
    c = o.get('message', {}).get('content', '')
    texts = []
    if isinstance(c, list):
        texts = [b['text'] for b in c if isinstance(b, dict) and b.get('type') == 'text']
        # 메모리·규칙 파일 쓰기는 tool_use에만 있다 → 결정이 메모리에만 남고 리뷰에서 안 보이던 구멍(2026-10-16)
        for b in c:
            if not (isinstance(b, dict) and b.get('type') == 'tool_use' and b.get('name') in ('Write', 'Edit')):
                continue
            inp = b.get('input') or {}
            fp = str(inp.get('file_path', ''))
            if '/memory/' in fp or fp.endswith('CLAUDE.md') or '/.claude/rules/' in fp:
                body_ = inp.get('content') or inp.get('new_string') or ''
                texts.append(f"[메모리/규칙 파일 쓰기] {fp}\n{body_[:1500]}")
    elif isinstance(c, str):
        texts = [c]
    body = '\n'.join(x for x in texts if x.strip())
    if body.strip():
        parts.append(f"## {o['type'].upper()}\n{body}")
joined = '\n\n'.join(parts)
# 사람이 한 말이 거의 없으면(cron 정기 점검이 같은 프롬프트를 반복) 기록할 교정·결정도 없다. 에이전트를 띄우지 않는다(2026-10-22 감사: 리뷰 44% 무기록).
human = sum(len(p) for p in parts if p.startswith('## USER') and '[메모리/규칙 파일 쓰기]' not in p and not p[8:].lstrip().startswith('<'))
# 기록 대상(교정·결정·원인 발견·메모리 쓰기) 신호가 하나도 없으면 띄우지 않는다.
import re
said = '\n'.join(p for p in parts if p.startswith('## USER'))
told = '\n'.join(p for p in parts if p.startswith('## ASSISTANT'))
signal = ('[메모리/규칙 파일 쓰기]' in joined
          or re.search(r'아니|말고|하지\s*마|안\s*된다|틀렸|잘못|왜\s|앞으로|항상|하기로|기억해|규칙|금지|그게 아니', said)
          or re.search(r'원인은|원인:|근본 원인|root cause|알고 보니|문서에 없|삽질|우회했|교정', told, re.I))
if joined.strip() and human >= 40 and signal:
    open(out, 'w', encoding='utf-8').write(joined)
PYEOF
if [ "$?" -ne 0 ]; then
  rm -f "$EXCERPT_FILE"
  exit 0
fi

# PreCompact는 지시를 주입하지 않고 발췌만 누적한다.
if [ "$EVENT" = "PreCompact" ]; then
  if [ -s "$EXCERPT_FILE" ]; then
    cat "$EXCERPT_FILE" >> "$PENDING_FILE" || exit 0
    printf '\n\n' >> "$PENDING_FILE"
  fi
  rm -f "$EXCERPT_FILE"
  echo "$TOTAL" > "$MARKER_FILE"
  exit 0
fi

# 마커는 항상 현재 위치로 업데이트 (중복 리뷰 방지)
echo "$TOTAL" > "$MARKER_FILE"

# 추출 내용 없으면 block 없이 종료
if [ ! -s "$EXCERPT_FILE" ]; then
  rm -f "$EXCERPT_FILE"
  exit 0
fi
fi

jq -n --arg path "$EXCERPT_FILE" '{
  "decision": "block",
  "reason": ("library 기록 점검: run_in_background=true로 Agent(general-purpose) 1개를 띄운다. subagent 프롬프트:\n---\n파일 \($path) 를 Read 해라. 최근 대화 발췌(user/assistant 텍스트)다. 이걸 '"'"'이번 세션 대화'"'"'로 간주하고 session-review 기준을 적용해라:\n1. 에러/삽질로 알게 된 API/라이브러리 동작\n2. 사용자가 접근법을 교정한 것\n3. 실패한 접근법과 이유\n4. 자명하지 않은 설계 결정\n5. 사용자가 정한 결정·교정(\"~하기로 함\", \"~안 한다고 했잖아\", 방향 확정) — 한 프로젝트 전용이어도 버리지 말고 ~/claude-library/decisions/<레포명 또는 _global>/<architecture|stack|convention|process|scope>/ 에 type: Decision 으로 남긴다. **메모리(memory/*.md)·CLAUDE.md에 이미 적혔다는 이유로 건너뛰지 마라** — 메모리는 그 프로젝트 세션에만 보이고 다른 레포·계정 세션엔 안 보인다. 발췌의 [메모리/규칙 파일 쓰기] 항목 중 결정인 것은 decisions/ 에 같은 내용이 있는지 grep 해 보고 없으면 승격한다. 「프로젝트 전용이라 library 대상 아님」은 지식(library/)에만 해당하는 판단이다.\n저장 가치가 있으면 ~/claude-library 규칙대로 파일 작성 + commit/push. 없으면 아무것도 하지 마라. 끝나면 \($path) 를 rm 해라.\n---\n체크리스트를 인라인으로 직접 수행하지 말고 에이전트에 맡긴다. 같은 턴에 다른 훅 지시(커밋 등)가 함께 왔으면 그것도 처리한 뒤 짧게 끝낸다.")
}'
