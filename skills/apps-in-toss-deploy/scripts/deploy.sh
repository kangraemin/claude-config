#!/bin/bash
# Test-deploy a built .ait to Apps-in-Toss and write a QR for the intoss-private link.
# Usage: deploy.sh <ait-dir> <file.ait> "<memo>" [profile=default] [qr-out=<ait-dir>/test_qr.png]
# Works without a TTY (Claude Code Bash): calls node_modules/.bin/ait directly instead of `pnpm exec`.
set -u
DIR="$1"; AIT="$2"; MEMO="$3"; PROFILE="${4:-default}"; QR="${5:-$DIR/test_qr.png}"
case "$QR" in /*) ;; *) QR="$PWD/$QR" ;; esac   # resolve before cd
case "$AIT" in /*) ;; *) [ -f "$AIT" ] && AIT="$PWD/$AIT" ;; esac   # a path relative to the caller, not to <ait-dir>
cd "$DIR" || exit 1
export CI=true
NODE_BIN=$(ls -d "$HOME"/.ait-unity-sdk/nodejs/*/darwin-arm64/bin 2>/dev/null | tail -1)
export PATH="$PWD/node_modules/.bin:${NODE_BIN:+$NODE_BIN:}$PATH"
if [ -x node_modules/.bin/ait ]; then AITCMD=node_modules/.bin/ait; else AITCMD="npx --yes ait"; fi
LOG=$(mktemp)
timeout 900 $AITCMD deploy --profile "$PROFILE" --location "$AIT" -m "$MEMO" < /dev/null > "$LOG" 2>&1
CLEAN=$(sed -E 's/\x1b\[[0-9;?]*[a-zA-Z]//g' "$LOG" | tr '\r' '\n')   # strip ANSI first: colour codes stick to the URL
echo "$CLEAN" | grep -E "완료|오류|Code|intoss|rror" | sed 's/.*◒.*//' | grep -v '^$' | tail -4
URL=$(echo "$CLEAN" | grep -oE 'intoss-private://[^ ]+' | tail -1)
rm -f "$LOG"
[ -n "$URL" ] || { echo "DEPLOY_FAILED (see Code above; 4031 = app not in this key's workspace; 4097 = same bundle already uploaded)"; exit 1; }
echo "DEPLOY_URL $URL"
if command -v uv >/dev/null; then
  uv run -q --with qrcode --with pillow python -c "import qrcode,sys; qrcode.make(sys.argv[1], box_size=12, border=3).save(sys.argv[2])" "$URL" "$QR"
else
  npx --yes qrcode -w 600 -o "$QR" "$URL" >/dev/null
fi
echo "QR $QR"
