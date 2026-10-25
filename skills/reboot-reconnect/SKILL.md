---
name: reboot-reconnect
description: Claude 세션을 리모트(Remote Control)로 연다. (1) "<프로젝트> 세션 켜/열어/붙여", "ai bouncer 켜바", "세션 연결좀해바"처럼 프로젝트 세션 하나를 말하면 그 세션 하나만 연다(scripts/open_session.py). (2) 사용자가 재부팅·전원("재부팅했어", "컴터 껐다 켰어", "정전")을 직접 말했을 때만 등록된 세션 전부와 공모전 텔레그램 세션·job 대기열을 되살린다(scripts/after_reboot.sh). 재부팅 언급 없이 전부 재연결을 돌리지 않는다.
---

# 세션 열기 · 재부팅 뒤 전부 재연결

사용자 요청(2026-10-22): "컴터가 껐다 켜져도, 내가 말 한 번 하면 지금 돌아가고 있는 세션들 전부 클로드 리모트 연결할 수 있게(로그인 확인 후에)". 사용자는 폰에서 본다 — 맥에서 뭘 하라고 시키지 않는다.

## 프로젝트 세션 하나 열기 (기본)
```
python3 ~/.claude/skills/reboot-reconnect/scripts/open_session.py <프로젝트 키워드>   # 예: ai bouncer, mukmap, 공모전
```
- 키워드로 `~/programming/vibecoding/` 아래 폴더를 찾는다(대소문자·공백·하이픈 무시).
- 명단에 그 폴더 대화가 있으면 가장 최근 대화를 다시 붙인다. 이어받기 프롬프트는 보내지 않는다.
- 없으면 그 폴더에서 새 세션을 띄우고 명단에 넣는다.
- 마지막 줄 `RESULT OK <이름> <링크>`면 `이름 — 링크` 한 줄로 보고한다.
- `RESULT BLOCKED 폴더를 못 정함: a, b`면 후보가 여럿이다. 말한 맥락으로 고를 수 있으면 그 폴더 이름으로 다시 돌리고, 아니면 사용자에게 묻는다.
- "세션 연결좀해바"처럼 프로젝트 이름이 없으면 바로 앞 대화에서 말한 프로젝트를 쓴다. 그것도 없으면 묻는다.
- 검증(2026-10-25): `ai bouncer` → 이미 붙은 bouncer-opt 그대로 OK. `korail` → 후보 2개로 BLOCKED. 없는 이름 → BLOCKED. 새 세션 띄우기 경로는 아직 실제로 돌려 보지 않았다.

## 재부팅 뒤 전부 재연결 — 언제 쓰나 (먼저 확인)
- 사용자가 재부팅·전원 꺼짐을 직접 말했을 때만 돈다.
- "세션 연결좀해바", "ai bouncer 켜바"처럼 재부팅 언급 없이 말하면 전부 재연결이 아니라 위의 세션 하나 열기다.
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
