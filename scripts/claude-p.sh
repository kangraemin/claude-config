#!/bin/bash
# claude-p.sh — launchd·cron용 `claude -p`. 계정이 한도에 걸리면 다음 계정으로 다시 돌린다.
#   사용: claude-p.sh -p "프롬프트" --model ... (claude 인자 그대로)
#   순서: 개인 계정(~/.config/claude-accounts/personal) → 기본 계정(~/.claude).
# 왜: 계정 하나를 박아 두면 그 계정이 주간 한도에 걸린 날 레이더·작업 요약이 통째로 실패한다(10/16, 10/21).
EXE=/Users/ram/.local/bin/claude
OUT=$(mktemp); ERR=$(mktemp)
trap 'rm -f "$OUT" "$ERR"' EXIT
for CFG in /Users/ram/.config/claude-accounts/personal default; do
  if [ "$CFG" = default ]; then
    env -u CLAUDE_CONFIG_DIR "$EXE" "$@" > "$OUT" 2> "$ERR"
  else
    CLAUDE_CONFIG_DIR="$CFG" "$EXE" "$@" > "$OUT" 2> "$ERR"
  fi
  RC=$?
  if grep -qiE "hit your (weekly |session |usage )?limit|usage limit reached" "$OUT" "$ERR"; then
    echo "[claude-p] $CFG 한도 초과 → 다음 계정" >&2
    continue
  fi
  cat "$OUT"; grep -v "^Permission allow rule" "$ERR" >&2
  exit $RC
done
cat "$OUT"; cat "$ERR" >&2
echo "[claude-p] 모든 계정 한도 초과" >&2
exit 3
