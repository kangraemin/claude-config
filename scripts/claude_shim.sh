#!/bin/bash
# ~/.local/bin/claude 자리에 놓는 얇은 앞단. -p(headless) 호출만 headless_guard.py로 세고 상한을 넘으면 막는다.
# 왜: 11/3~4 젠더 AI 측정 judge.py가 --setting-sources ''로 훅을 건너뛰고 Opus -p를 약 2만 번 호출해 주간 한도 40%를 썼다.
# 설정 훅은 그 플래그로 우회되므로 실행 파일 자리에서 센다. 대화형 실행은 그대로 통과한다.
for a in "$@"; do case "$a" in -p|--print) H=1; break;; esac; done
REAL=$(cat "$HOME/.claude/.headless-real" 2>/dev/null)
[ -x "$REAL" ] || REAL=$(ls -t "$HOME"/.local/share/claude/versions/* 2>/dev/null | head -1)
if [ -n "$H" ]; then
  /usr/bin/python3 -I "$HOME/.claude/scripts/headless_guard.py" "$@"
  [ $? -eq 75 ] && exit 75
fi
exec "$REAL" "$@"
