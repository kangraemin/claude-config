---
name: reboot-reconnect
description: 맥을 껐다 켠 뒤(재부팅·정전·업데이트) 돌던 Claude 세션 전부를 로그인 확인 후 리모트(Remote Control)로 다시 붙이고, 공모전 텔레그램 세션과 job 대기열까지 되살린다. 사용자가 재부팅·전원("재부팅했어", "컴터 껐다 켰어", "정전", "업데이트하고 다시 켰어")을 **직접 말했을 때만** 쓴다. "세션 연결", "리모트 붙여"처럼 재부팅 언급이 없는 말에는 쓰지 않는다(꺼진 세션 수십 개를 다시 띄우고 일을 재개시킨다).
---

# 재부팅 뒤 세션 전부 재연결

사용자 요청(2026-10-22): "컴터가 껐다 켜져도, 내가 말 한 번 하면 지금 돌아가고 있는 세션들 전부 클로드 리모트 연결할 수 있게(로그인 확인 후에)". 사용자는 폰에서 본다 — 맥에서 뭘 하라고 시키지 않는다.

## 언제 쓰나 (먼저 확인)
- 사용자가 재부팅·전원 꺼짐을 직접 말했을 때만 돈다.
- "세션 연결좀해바"처럼 재부팅 언급 없이 연결을 말하면 이 스킬이 아니다. 지금 이 세션의 리모트나 특정 세션 하나를 뜻할 수 있으니 무엇을 붙일지 확인한다.
  - 2026-10-25 사고: "세션 연결좀해바"에 이 스킬을 돌려 꺼져 있던 세션 13개가 다시 떠서 작업을 재개했다. 사용자 "방금니가 다른거킨것들 다 리모트끊어".
- 스크립트도 부팅 후 90분이 지났으면 `BLOCKED`로 멈춘다. 사용자가 재부팅을 말했는데 90분이 지났으면 `--force`로 돌린다.

## 순서
1. `~/.claude/skills/reboot-reconnect/scripts/after_reboot.sh` 를 백그라운드로 돌린다(세션 수십 개라 몇 분 걸림). 출력은 `| tail` 로 자르지 말고 파일 전체를 읽는다.
   - 안에서: `claude-account status` → `remotes discover` → `remotes reconnect`(멈춘 세션도 tmux로 띄우고 `--resume`, 이어받기 프롬프트 자동 전송) → `remotes status` → contest-tg(launchd `com.ram.contest-tg`) 확인 → 현황판 running 카드 목록 출력 → `run_queue.sh` 재가동.
   - `.started`는 절대 지우지 않는다(10/22 테스트에서 끝난 제출 job까지 다시 뜰 뻔함 — 중복 제출 위험). 끊긴 job은 running 카드 목록을 보고 job md를 읽은 뒤 하나씩 `.started`를 지워 다시 띄운다(제출 job은 `.done`·lock·현황판 submitted 먼저 확인).
2. **로그인 먼저**: status에서 selected 프로필이 `authenticated: false`면 reconnect 결과는 믿지 말고 `claude-account-switch` 스킬(Codex 쪽 `~/.codex/skills/claude-account-switch/SKILL.md`)의 로그인 절차대로 `claude-account login <계정>`을 PTY로 띄워 OAuth 링크를 채팅으로 주고, 받은 코드를 넣은 뒤 이 스크립트를 다시 돌린다.
3. 결과 보고: 연결된 세션은 `이름 — 링크` 한 줄씩, `disconnected`/`deferred`는 이유와 함께. 바쁜 세션(deferred)은 끝나면 `claude-account remotes reconnect <이름>`으로 다시.

## 명단
- 재연결 대상은 `~/.config/claude-accounts/remotes.json`. 재부팅 뒤엔 살아 있는 프로세스가 없어 discover가 못 찾으므로, **새 세션을 리모트로 띄우면 그때 바로 `claude-account remotes discover`로 명단에 넣어 둔다.**
- 리모트 세션 계정은 personal(CLAUDE_CONFIG_DIR=personal) — 결정 `decisions/_global/process/claude-account-switch-from-phone.md`.

## 하지 않는 것
- `--continue` 금지(다른 대화를 집음). 바쁜 세션 강제 종료 금지.
- 세션 상황판(session-board.py) 텔레그램 알림은 사용자가 꺼라 했다(10/22 "보내지마") — 되살리지 않는다.
