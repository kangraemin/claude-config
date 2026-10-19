#!/bin/bash
# 토스 비즈니스(앱인토스 콘솔) 로그인 — 휴대폰번호 + 문자 인증. Codex computer use로 실제 Chrome을 조작한다.
#   toss_business_login.sh send          → 인증 문자 요청까지 하고 멈춤. 발송이 화면에서 확인되면 $OUT/sms-sent 생성
#   toss_business_login.sh code 123456   → 인증번호를 JS로 바로 넣고 계정 선택까지. 성공하면 $OUT/logged-in 생성
#   toss_business_login.sh resend        → 시간이 지났을 때 인증번호 다시 받기 (press는 안 먹고 DOM click만 된다)
# 사람 몫은 폰에 온 6자리를 알려 주는 것 하나뿐이다. 통신사·이름·주민번호 뒤 첫 숫자는 아래에 고정.
# 개인정보.md는 TCC로 막히는 일이 많아 같은 값이 든 build_application.py INFO를 쓴다(번호는 출력하지 않는다).
set -u
OUT=${TOSS_LOGIN_OUT:-/tmp/toss-login}; mkdir -p "$OUT"
INFO_PY=/Users/ram/programming/vibecoding/공모전/2026-10_제천AI데이터분석/submission/build_application.py
RULES="computer use로 사용자의 실제 Mac Chrome을 조작한다(새 브라우저·프로필·Playwright 금지). 비밀번호 입력 금지. 번호·생년월일 전체를 출력하지 마라."
case "${1:-}" in
  send)
    rm -f "$OUT/sms-sent"
    codex exec --skip-git-repo-check "$RULES
1) Chrome에서 https://apps-in-toss.toss.im/ 를 열고 '콘솔 바로가기'(이미 business.toss.im 로그인 화면이면 그 탭)로 간다. 이미 콘솔(workspace)이 열리면 셸에서 touch $OUT/logged-in 하고 'ALREADY'로 끝.
2) '휴대폰번호 로그인'을 고른다. 통신사 'SKT 알뜰폰'(SK 알뜰폰/MVNO), 이름 강래민, 생년월일과 휴대폰번호는 $INFO_PY 의 INFO 값(5=생년월일, 9=전화), 주민번호 뒷자리 첫 숫자 1.
3) 필수 약관 동의 후 '인증번호 받기/요청'을 실제로 누른다. 인증번호 입력 칸이나 발송 안내가 화면에 실제로 뜬 것을 본 뒤에만 셸에서 touch $OUT/sms-sent 하고 'SMS_SENT'로 끝. 그 화면은 닫지 마라.
실패면 'FAILED: 화면 문구'." < /dev/null > "$OUT/send.out" 2>&1
    tail -3 "$OUT/send.out"; [ -f "$OUT/sms-sent" ] || [ -f "$OUT/logged-in" ] ;;
  code)
    # 인증번호 유효시간이 2분이라 Codex(1~3분)로는 늦는다(2026-10-19 실측: "입력 시간이 지났어요"). JS로 바로 넣는다.
    [[ "${2:-}" =~ ^[0-9]{6}$ ]] || { echo "usage: $0 code <6자리>"; exit 2; }
    rm -f "$OUT/logged-in"; C="python3 $(dirname "$0")/../chromectl.py"
    $C js --match business.toss.im "(()=>{const i=document.querySelector('input');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,'$2');i.dispatchEvent(new Event('input',{bubbles:true}));setTimeout(()=>document.querySelector('button[type=submit]').click(),300);return 'ok'})()" >/dev/null
    sleep 6
    # 계정 선택 화면(어떤 계정으로 로그인할까요?)이 나오면 앱인토스 사용 중 계정을 고른다
    $C tabs | grep -q select-account && { $C press --match select-account --text "remin1994@gmail.com" >/dev/null; sleep 6; }
    if $C tabs | grep -q "apps-in-toss.toss.im/workspace"; then touch "$OUT/logged-in"; echo LOGGED_IN
    else $C text --match business.toss.im | head -5; echo FAILED; exit 1; fi ;;
  resend)
    python3 "$(dirname "$0")/../chromectl.py" js --match business.toss.im "[...document.querySelectorAll('button')].find(b=>/다시 받기/.test(b.innerText)).click(),'RESENT'" ;;
  *) echo "usage: $0 send | code <6자리> | resend"; exit 2 ;;
esac
