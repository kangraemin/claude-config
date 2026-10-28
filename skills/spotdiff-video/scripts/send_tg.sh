#!/bin/bash
# usage: send.sh <video> <caption> — sends with width/height/duration/thumbnail so Telegram keeps the aspect ratio
set -a; source ~/.claude/.env; set +a
v="$1"; cap="$2"
IFS=, read W H <<<"$(ffprobe -v error -select_streams v -show_entries stream=width,height -of csv=p=0 "$v")"
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$v" | cut -d. -f1)
th="${TMPDIR:-/tmp}/$(basename "$v").thumb.jpg"
if [ "$W" -gt "$H" ]; then sc="320:-2"; else sc="-2:320"; fi
ffmpeg -v error -y -ss 3 -i "$v" -frames:v 1 -vf scale=$sc -q:v 4 "$th"
curl -s -m 900 -F chat_id="$RAM_NOTI_TG_CHAT_ID" -F caption="$cap" -F supports_streaming=true \
  -F width=$W -F height=$H -F duration=$dur -F thumbnail=@"$th" -F video=@"$v" \
  "https://api.telegram.org/bot$RAM_NOTI_TG_TOKEN/sendVideo" | python3 -c 'import sys,json;r=json.load(sys.stdin);v=r.get("result",{}).get("video",{});print(r.get("ok"),r.get("description",""),v.get("width"),v.get("height"))'
