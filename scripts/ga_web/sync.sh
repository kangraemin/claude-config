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
  T=$(date +%F); NOW=$(python3 -c 'import time;print(int(time.time()*1000))'); DAYJ=""
  # 0시~아침 확정판(07시) 전에 누르면 오늘치는 몇십 분이라 전부 0으로 보인다(사용자 11/13 00:31 "갱신 눌렀는데 아직 저 상태").
  # 그 사이엔 어제 하루치(확정 전 임시)를 뽑는다. 어제 파일이 이미 있으면(아침판 나옴) 원래대로 오늘치.
  Y=$(date -v-1d +%F)
  if [ "$(date +%H)" -lt 7 ] && [ ! -f "$C/$Y.txt" ]; then T=$Y; DAYJ=", \"day\": \"$Y\""; fi
  # 갱신 버튼판은 하루 중간 숫자다. <오늘>.txt에 남기면 다음 날 아침 확정판이 덮어써 같은 날 숫자가 바뀐 것처럼 보인다(사용자 11/11 "11/10 데이터가 왜 바뀜").
  # 그래서 돌린 뒤 live.txt로만 옮기고 날짜 파일은 원래대로 되돌린다.
  B="$C/.live-bak"; rm -rf "$B"; mkdir -p "$B"
  for s in "" -full -detail; do [ -f "$C/$T$s.txt" ] && cp -p "$C/$T$s.txt" "$B/"; done
  if python3 "$HOME/.claude/scripts/ga_daily_report.py" --day "$T" --dry-run --no-ai --force >> "$LOG" 2>&1 && [ -f "$C/$T.txt" ]; then
    cp "$C/$T.txt" "$C/live.txt"; echo "{\"at\": $NOW$DAYJ}" > "$C/live.json"
  else echo "live FAIL" >> "$LOG"; fi
  for s in "" -full -detail; do rm -f "$C/$T$s.txt"; [ -f "$B/$T$s.txt" ] && cp -p "$B/$T$s.txt" "$C/"; done
  rm -rf "$B"
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
