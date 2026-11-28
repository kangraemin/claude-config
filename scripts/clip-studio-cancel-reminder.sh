#!/bin/bash
# 클립스튜디오 PRO 월정액 3개월 무료 해지 알림 — 2027-01-11~01-18 매일 텔레그램 발송 (첫 청구 2027-01-19)
today=$(date +%Y%m%d)
[ "$today" -lt 20270111 ] && exit 0
if [ "$today" -gt 20270118 ]; then launchctl unload ~/Library/LaunchAgents/com.ram.clip-studio-cancel-reminder.plist; exit 0; fi
source ~/.claude/.env
left=$(( ( $(date -j -f %Y%m%d 20270119 +%s) - $(date -j -f %Y%m%d "$today" +%s) ) / 86400 ))
msg="[클립스튜디오 해지 알림] 첫 결제(₩5,000)까지 ${left}일 남음 (2027-01-19 청구). 지금 해지: https://accounts.clip-studio.com → 플랜/이용 현황 → 월정액 해지. 계정: 구글 remin1994@gmail.com"
curl -s -d chat_id="$CONTEST_TG_CHAT_ID" --data-urlencode "text=$(printf '%s' "$msg" | python3 ~/.claude/scripts/fmt_check.py --fix)" "https://api.telegram.org/bot$CONTEST_TG_TOKEN/sendMessage" >/dev/null
