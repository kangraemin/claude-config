---
name: chrome-tab-cleanup
description: 사용자의 실제 Chrome에 쌓인 쓸모없는 탭을 한 번에 닫는다. 페르소나 창마다 핵심 SNS 탭(X·인스타·스레드·링크드인·지메일 1개씩)과 얼굴 인증 같은 사람 몫 화면만 남기고, 중복 탭·끝난 작업(콘솔·결제·도움말·로그인 잔여) 탭을 닫는다. "크롬 탭 정리", "쓸모없는 크롬창 꺼", "탭 너무 많아", "창 좀 닫아", "여전히 많다" 같은 말이 나오면 직접 AppleScript를 짜지 말고 반드시 이 스킬을 쓴다.
---

# chrome-tab-cleanup

```
python3 ~/.claude/skills/chrome-tab-cleanup/scripts/tab_cleanup.py            # 미리보기(KEEP/CLOSE 표)
python3 ~/.claude/skills/chrome-tab-cleanup/scripts/tab_cleanup.py --apply    # 실제로 닫기
  [--keep <URL 일부>]...   # 이 탭은 남김(다른 세션이 쓰는 중인 탭 등)
  [--close <URL 일부>]...  # 핵심 규칙에 걸려도 닫음
```
마지막 줄 `RESULT: DRY-RUN|OK|BLOCKED ...`.

## 순서
1. 미리보기를 돌린다.
2. CLOSE 목록에서 **다른 세션이 지금 쓰는 탭**을 골라 `--keep`으로 지킨다.
   - 신호: 방금 전 목록에 없던 로그인·결제·콘솔 탭(LINE Login, 가비아, 앱인토스 등), `ps`에 그 일을 하는 `claude` 세션이 떠 있음.
   - 사용자가 "다 꺼"라고 했으면 지키지 않는다.
3. `--apply`로 닫고, 남은 탭 수와 닫은 종류를 짧게 보고한다.
4. 사용자가 "여전히 많다"고 하면 남은 KEEP 중에서 서비스별로 더 줄일 걸 `--close`로 추가한다. "이제 하나"라고 말하기 전에 다시 미리보기로 실제 수를 확인한다.

## 남기는 규칙 (창마다, 서비스당 첫 탭 1개)
- X 홈·프로필, X 가입 얼굴 인증 화면(사용자 몫), 인스타, 스레드 프로필, 링크드인 피드·회사 관리, 지메일.
- 나머지(피그마·앱인토스 콘솔·Supabase·도움말·약관·결제·localhost·file://·about:blank)는 닫는다. 필요하면 다시 열면 된다.
- 규칙은 스크립트 `KEEP` 표에 있다. 페르소나별 창·프로필은 my-sns `CLAUDE.md`와 `~/.claude/sns.env`의 `*_PROFILE`.

## 함정
- **창 1개·탭 1개만 보이면 가짜다.** 다른 세션의 Playwright가 실제 Chrome 바이너리를 두 번째 인스턴스(`--disable-field-trial-config ...`)로 띄우면 `tell application "Google Chrome"`이 가끔 그쪽을 잡는다. 스크립트는 여러 번 읽어 탭이 가장 많은 결과를 쓰고, 그래도 창이 1개면 `BLOCKED`로 멈춘다. 이걸 "탭이 이미 없다"로 보고하지 않는다(2026-10-20 사용자 "지금 존나많은데").
- 같은 이유로 `chromectl.py tabs`(창 번호 반복 방식)도 첫 창만 보고 끝날 수 있다. 정리할 땐 이 스크립트를 쓴다.
- 창 id가 2^29를 넘어 `tab id T of window id W` 리터럴이 실수로 바뀐다 → `first tab of (first window whose id = W) whose id = T` 형식으로 닫는다.
- Chrome 앱 자체는 끄지 않는다(Chrome·Claude·Codex·Ghostty·ChatGPT 앱 종료 금지).

## 검증
- 2026-10-20: 미리보기 실행 확인(15개 중 3개 CLOSE 판정). `--apply --keep access.line.me --keep gabia.com`으로 새로 연 about:blank 1개만 닫힘 확인(지킨 탭 유지).
