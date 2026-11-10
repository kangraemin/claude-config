#!/bin/bash
# GA 리포트 웹(ga-report.remin1994.workers.dev) 갱신. launchd com.ram.ga-web가 60초마다 부른다.
# 1) 웹 '갱신' 요청이 들어오면 오늘 0시~지금 리포트를 만들어 live로 저장
# 2) ~/.cache/ga-daily/*.txt가 지난 배포보다 새로우면 다시 만들어 배포
set -u
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH
D=$HOME/.claude/scripts/ga_web; C=$HOME/.cache/ga-daily; SITE=$HOME/.cache/ga-site; LOG=$HOME/.cache/ga-web.log
URL=https://ga-report.remin1994.workers.dev
LOCK=$HOME/.cache/ga-web.lock
mkdir "$LOCK" 2>/dev/null || { [ $(( $(date +%s) - $(stat -f %m "$LOCK") )) -gt 1200 ] && rm -rf "$LOCK" && mkdir "$LOCK"; } || exit 0
trap 'rm -rf "$LOCK"' EXIT
KEY=$(grep "^PRIVATE_WEB_KEY=" $HOME/.claude/.env | cut -d= -f2)
REQ=$(curl -s -m 10 -H "cookie: pk=$KEY" "$URL/api/state" | python3 -c 'import sys,json;print(json.load(sys.stdin)["req"])' 2>/dev/null || echo 0)
DONE=$(cat "$C/live.req" 2>/dev/null || echo 0)
if [ "$REQ" -gt "$DONE" ]; then
  echo "== $(date '+%F %T') live req=$REQ" >> "$LOG"
  T=$(date +%F); NOW=$(python3 -c 'import time;print(int(time.time()*1000))')
  [ -f "$C/$T.txt" ] && cp "$C/$T.txt" "$C/.today-backup.txt"
  if python3 "$HOME/.claude/scripts/ga_daily_report.py" --day "$T" --dry-run --no-ai --force >> "$LOG" 2>&1 && [ -f "$C/$T.txt" ]; then
    cp "$C/$T.txt" "$C/live.txt"; echo "{\"at\": $NOW}" > "$C/live.json"
  else echo "live FAIL" >> "$LOG"; fi
  echo "$REQ" > "$C/live.req"
fi
STAMP=$HOME/.cache/ga-web.deployed
if [ -z "$(find "$C" -maxdepth 1 \( -name '20*.txt' -o -name 'live.json' \) -newer "$STAMP" 2>/dev/null | head -1)" ] && [ -f "$STAMP" ] && [ "${FORCE:-0}" != 1 ]; then exit 0; fi
python3 "$D/build.py" --out "$SITE/public" >> "$LOG" 2>&1 || exit 1
cat > "$SITE/wrangler.jsonc" <<J
{"name":"ga-report","main":"$D/worker.js","compatibility_date":"2026-10-01",
 "assets":{"directory":"$SITE/public","binding":"ASSETS","run_worker_first":true},
 "vars":{"PRIVATE_KEY":"$KEY"},
 "kv_namespaces":[{"binding":"ga_report","id":"ef600102d151469f8de3d5d01505bf3a"}]}
J
cd /tmp
for i in 1 2 3; do
  OUT=$(env -u CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID=c023da92383ce204b357f6f18b86eb86 /Users/ram/programming/vibecoding/money-web/app/node_modules/.bin/wrangler deploy -c "$SITE/wrangler.jsonc" 2>&1)
  if echo "$OUT" | grep -qE 'Deployed|Uploaded'; then touch "$STAMP"; echo "$(date '+%F %T') deployed" >> "$LOG"; exit 0; fi
  sleep 5
done
echo "$OUT" | tail -5 >> "$LOG"; exit 1
