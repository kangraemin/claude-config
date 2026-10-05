#!/bin/bash
# Drive the Apps-in-Toss console in the owner's logged-in Chrome through Codex (computer use + external browser).
# Usage: codex_console.sh <prompt-file> <out-file> [repo-dir]
#        codex_console.sh --resume <session-id> "<message>" <out-file> [repo-dir]
# Prints "SESSION <id>" and Codex's agent messages to <out-file>; the last lines carry STATUS/APP/AD_GROUP/PRODUCT.
set -u
FLAGS=(--dangerously-bypass-approvals-and-sandbox --enable computer_use --enable browser_use_external
       -c 'model_reasoning_effort="medium"' --json)
parse='import sys, json
for line in sys.stdin:
    try: o=json.loads(line)
    except Exception: continue
    if o.get("type")=="thread.started": print("SESSION", o.get("thread_id"), flush=True)
    if o.get("type")=="item.completed" and o["item"].get("type")=="agent_message": print(o["item"].get("text",""), flush=True)'
if [ "${1:-}" = "--resume" ]; then
  SID="$2"; MSG="$3"; OUT="$4"; cd "${5:-$PWD}" || exit 1
  timeout 2400 codex exec resume "$SID" "$MSG" "${FLAGS[@]}" < /dev/null 2>>"$OUT.err" | python3 -u -c "$parse" >> "$OUT"
else
  PROMPT_FILE="$1"; OUT="$2"; cd "${3:-$PWD}" || exit 1
  [ -s "$PROMPT_FILE" ] || { echo "missing prompt file $PROMPT_FILE" >&2; exit 1; }
  timeout 2400 codex exec "$(cat "$PROMPT_FILE")" "${FLAGS[@]}" < /dev/null 2>"$OUT.err" | python3 -u -c "$parse" > "$OUT"
fi
echo "exit=$?" >> "$OUT"
grep -E "^(STATUS|APP|AD_GROUP|PRODUCT|LOGIN_REQUIRED|NEEDS_OWNER)" "$OUT" | tail -10
