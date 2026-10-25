#!/bin/bash
# Anthropic 키는 money-web·area-insight(개인)·ai-paper(회사)에서만 쓰게 막는지 본다(2026-10-25 사용자 지시).
set -e
H=~/.claude/hooks/anthropic-key-guard.py
V=~/programming/vibecoding
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
printf 'SUPABASE_URL=x\nANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxx\n' > "$T/.env.local"
fail=0
run() {  # 기대(0|2) 도구 cwd 입력json
  local want=$1 tool=$2 cwd=$3 inp=$4 got=0
  printf '{"tool_name":"%s","cwd":"%s","tool_input":%s}' "$tool" "$cwd" "$inp" | env -u ANTHROPIC_KEY_GUARD_OFF python3 "$H" 2>/dev/null || got=$?
  if [ "$got" != "$want" ]; then echo "FAIL want=$want got=$got $tool $cwd $inp"; fail=1; fi
}
# 막아야 하는 것
run 2 Bash "$V/mukmap" '{"command":"export ANTHROPIC_API_KEY=$SSUM_ANTHROPIC_API_KEY && python3 x.py"}'
run 2 Bash "$V/mukmap" '{"command":"ANTHROPIC_API_KEY=$UNSE_ANTHROPIC_API_KEY node run.js"}'
run 2 Bash "$V/mukmap" '{"command":"curl https://api.anthropic.com/v1/messages -H x-api-key:abc"}'
run 2 Bash "$T" '{"command":"set -a && source .env.local && set +a && python3 a.py"}'
run 2 Bash "$V/money-web" '{"command":"echo $UNSE_ANTHROPIC_API_KEY"}'
run 2 Bash "$V/mukmap" '{"command":"cd ~/programming/vibecoding/stash && wrangler secret put ANTHROPIC_API_KEY"}'
run 2 Write "$V/mukmap" '{"file_path":"'"$V"'/mukmap/.env.local","content":"ANTHROPIC_API_KEY=sk-ant-api03-abcdefghijk\n"}'
run 2 Write "$V/mukmap" '{"file_path":"'"$HOME"'/.claude/.env","content":"UNSE_ANTHROPIC_API_KEY=sk-ant-api03-abcdefghijk\n"}'
# 허용
run 0 Bash "$V/money-web/api" '{"command":"wrangler secret put ANTHROPIC_API_KEY"}'
run 0 Bash "$V/mukmap" '{"command":"cd ~/programming/vibecoding/area-insight && export ANTHROPIC_API_KEY=$AREA_INSIGHT_ANTHROPIC_API_KEY && npm test"}'
run 0 Bash "$V/mukmap" '{"command":"cd ~/.claude/skills && ls; cd ~/programming/vibecoding/money-web && curl -H \"x-api-key: $SSUM_ANTHROPIC_API_KEY\" https://api.anthropic.com/v1/messages"}'
run 2 Bash "$V/mukmap" '{"command":"cd ~/programming/vibecoding/money-web && ls; cd ~/programming/vibecoding/mukmap && echo $SSUM_ANTHROPIC_API_KEY"}'
run 0 Bash "$V/ai-paper" '{"command":"python3 run.py --key $AI_PAPER_GC_ANTHROPIC_API_KEY"}'
run 0 Bash "$T" '{"command":"set -a && source .env.local && set +a && env -u ANTHROPIC_API_KEY python3 a.py"}'
run 0 Bash "$V/mukmap" '{"command":"grep -n \"ANTHROPIC_API_KEY=\" .env.local | wc -l; unset ANTHROPIC_API_KEY"}'
run 0 Bash "$V/mukmap" '{"command":"source .env.local && npm run build"}'
run 0 Write "$V/mukmap" '{"file_path":"'"$HOME"'/.claude/.env","content":"SSUM_ANTHROPIC_API_KEY=sk-ant-api03-abcdefghijk\n"}'
[ $fail = 0 ] && echo PASS || exit 1
