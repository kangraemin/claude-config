#!/bin/bash
# ~/.local/bin/claude 자리에 놓는 얇은 앞단. -p(headless) 호출만 headless_guard.py로 세고 상한을 넘으면 막는다.
# 왜: 11/3~4 젠더 AI 측정 judge.py가 --setting-sources ''로 훅을 건너뛰고 Opus -p를 약 2만 번 호출해 주간 한도 40%를 썼다.
# 설정 훅은 그 플래그로 우회되므로 실행 파일 자리에서 센다. 대화형 실행은 그대로 통과한다.
for a in "$@"; do case "$a" in -p|--print|-[A-Za-z]*p[A-Za-z]*) H=1; break;; esac; done
echo $$ >> "$HOME/.claude/.headless-pids" 2>/dev/null  # exec해도 PID가 같다. 여기 없는 -p 프로세스는 앞단을 건너뛴 것
REAL=$(cat "$HOME/.claude/.headless-real" 2>/dev/null)
[ -x "$REAL" ] || REAL=$(ls -t "$HOME"/.local/share/claude/versions/* 2>/dev/null | head -1)
if [ -n "$H" ]; then
  /usr/bin/python3 -I "$HOME/.claude/scripts/headless_guard.py" "$@"
  [ $? -ne 0 ] && exit 75  # 가드가 실패해도 -p는 막는다(대화형은 영향 없음)
fi
exec "$REAL" "$@"
