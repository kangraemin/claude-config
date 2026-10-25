#!/bin/zsh
# 재부팅 뒤 한 번에 복구: 로그인 확인 → 등록된 세션 전부 리모트 재연결 → 공모전 텔레그램 세션·job 대기열 재가동.
# 사용: after_reboot.sh [--force] [--no-resume]
ACC=~/.local/bin/claude-account
# 재부팅 직후가 아니면 멈춘다. 2026-10-25 "세션 연결좀해바"(재부팅 아님)에 이 스크립트가 돌아
# 꺼져 있던 세션 13개를 --resume으로 띄우고 이어받기 프롬프트까지 보냈다(사용자 "ai bouncer만키랫자나").
# 부팅 후 MAX_UP_MIN(기본 90분)이 지났으면 --force 없이는 아무것도 안 한다.
if [[ "$1" == "--force" ]]; then shift
else
  boot=$(sysctl -n kern.boottime | sed -E 's/^\{ sec = ([0-9]+),.*/\1/')
  up=$(( ($(date +%s) - boot) / 60 ))
  if (( up > ${MAX_UP_MIN:-90} )); then
    echo "BLOCKED 부팅 후 ${up}분 지남 — 재부팅 직후가 아니다. 사용자가 재부팅을 말했을 때만 --force로 돌린다."
    exit 3
  fi
fi
C=/Users/ram/programming/vibecoding/공모전
echo "== 로그인"
$ACC status
echo "== 리모트 재연결"
$ACC remotes discover >/dev/null
$ACC remotes reconnect "$@"
echo "== 재연결 결과"
$ACC remotes status
echo "== 공모전 텔레그램 세션"
tmux has-session -t contest-tg 2>/dev/null || launchctl kickstart -k gui/$(id -u)/com.ram.contest-tg
sleep 3; tmux has-session -t contest-tg 2>/dev/null && echo "contest-tg up" || echo "contest-tg DOWN"
echo "== 공모전 job 대기열"
cd $C
# 끊긴 job은 지우지 않고 목록만 낸다. .started를 지우면 이미 끝난 제출 job까지 다시 떠서 중복 제출 위험(10/22 사고).
# 재부팅 직전에 돌던 job 이름은 tmux 기록이 없으니 현황판 running=true 카드와 대조해 지휘 세션이 하나씩 판단한다.
for c in _radar/db/contests/*.json(N); do python3 -c "import json,sys;d=json.load(open(sys.argv[1]));d.get('running') and print('돌던 카드(job 확인 필요):',d.get('name'))" $c; done
if pgrep -f "_radar/jobs/run_queue.sh" >/dev/null; then echo "run_queue already running"
else MAX=${MAX:-6} nohup zsh _radar/jobs/run_queue.sh >> _radar/jobs/run_queue.log 2>&1 & echo "run_queue started pid $!"; fi
