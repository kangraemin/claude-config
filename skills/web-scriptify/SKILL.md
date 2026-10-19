---
name: web-scriptify
description: 웹·콘솔 조작이 들어간 작업(Chrome 직접 조작, Codex에 Chrome 맡김, 관리 콘솔 등록·제출·설정, 로그인 처리)이 끝나면 그 과정을 다음엔 LLM·Codex 없이 한 줄로 돌릴 수 있게 스크립트로 저장한다. 스크립트화할 수 없으면 만들지 않는다. 웹 조작이 포함된 작업을 마무리할 때마다 사용자가 말하지 않아도 이 스킬을 쓴다. "스크립트화해", "자산화", "코덱스 없이 되게", "다음엔 바로 되게", "재사용하게 저장" 등에도 사용.
---

# web-scriptify

웹 조작은 매번 화면을 보고 헤매면 느리고 틀린다. 한 번 성공한 순서를 스크립트로 남기면 다음엔 한 줄로 끝난다(예: 애드센스 등록 `adsense_add.py`, 구글 재로그인 `chromectl.google_relogin`).

## 1. 이번 작업에서 한 웹 조작을 적는다
- 들어간 주소, 누른 버튼·입력칸(셀렉터), 기다린 문구, 막힌 곳과 푼 방법.
- Codex가 했으면 Codex 출력·로그에서 같은 것을 뽑는다.
- 실패했다가 성공한 순서는 성공한 순서만 남긴다.

## 2. 스크립트로 만들 수 있는지 판단한다
만들지 않는 경우는 아래와 같다. 이때는 스크립트를 쓰지 않는다. 쓸모 있는 함정만 library에 Gotcha로 남기고 한 줄로 보고한다.
- 다시 할 일이 없는 일회성 작업(도메인 구매처럼 한 번 사면 끝나는 것).
- 매번 사람 판단이 필요한 작업(디자인 고르기, 글 내용 쓰기).
- 결제·본인인증·서명처럼 사용자만 할 수 있는 단계가 핵심인 작업. 앞뒤 단계만 스크립트로 만들 수 있으면 그 부분만 만든다.
- 화면이 매번 달라 셀렉터로 잡을 수 없는 경우(캔버스·이미지 기반 UI).

보안문자나 SMS 코드가 중간에 끼는 것은 만들 수 있다. 텔레그램으로 한 번 묻는 기존 패턴을 쓰면 된다(`naver_register.py`의 `captcha`).

## 3. 넣을 곳을 정한다
- 먼저 기존 스크립트를 찾는다: `ls ~/.claude/skills/*/scripts ~/.claude/skills/chrome-direct/scenarios`. 비슷한 게 있으면 새로 만들지 말고 그 파일을 고치거나 옵션을 더한다.
- 도메인 스킬이 있으면 그 `scripts/`에 넣는다(사이트 등록·검색·광고 → `site-launch`, 토스 콘솔 → `chrome-direct/scenarios/ait_*`).
- 없으면 `~/.claude/skills/chrome-direct/scenarios/`에 넣는다.

## 4. 이렇게 쓴다
- Chrome은 `chromectl`로 조작한다:
  - `sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct')); import chromectl as c`
  - 쓰는 함수: `new_tab(url, profile='Profile 1')`, `js_json`, `fill`, `press`, `rclick`, `goto`, `shot`, `close_tab`.
  - 탭은 `new_tab`이 준 `id:`로만 가리킨다. 다른 세션이 탭을 열고 닫아도 안 깨진다.
- 구글 콘솔은 `new_tab` 바로 뒤에 `c.google_relogin(t)`를 부른다. 로그아웃돼 있어도 패스키 시트까지 눌러 다시 로그인한다.
- Angular·Vue 화면은 백그라운드 탭에서 안 그려진다. 읽기 전에 `c.shot(t, png)`로 탭을 앞으로 띄운다.
- 누른 뒤 alert가 뜨는 버튼은 `run_js("setTimeout(()=>btn.click(),10)")`로 누른다.
- 멱등하게 만든다. 이미 등록·생성돼 있으면 새로 만들지 않고 남은 단계만 하거나 상태만 출력한다. 두 번 돌려도 중복이 생기면 안 된다.
- 제출·결제·공개 같은 되돌리기 어려운 단계는 `--dry-run`을 둔다. 아니면 chrome-direct의 Submit 규칙(`--submit`이 있을 때만 실행)을 따른다.
- 사전 조건은 시작 전에 확인하고 막는다(예: 사이트에 광고 코드가 배포됐는지).
- 출력의 마지막 줄은 `RESULT: <상태>`로 쓴다. 탭은 `finally`에서 닫는다.
- 재시도 루프 안에서 사용자에게 묻지 않는다(보안문자를 매번 다시 물으면 사용자가 매우 싫어한다).
- 비밀값은 `~/.claude/.env`의 env 이름으로만 읽는다. 개인정보는 `~/Documents/oguri-works/개인정보.md`에서 패턴으로만 뽑는다. 둘 다 출력하지 않는다.
- 파일 맨 위 docstring에 사용법 한 줄, 하는 일, 사전 조건, 왜 화면 조작인지(API가 막힌 이유 등)를 적는다.

## 5. 지금 돌려서 확인한다
- 읽기 경로나 이미 끝난 대상(멱등 경로), 또는 `--dry-run`으로 실제로 돌린다.
- 실제 제출을 확인하려고 한 번 더 제출하지 않는다.
- 못 돌린 경로(예: 로그아웃 상태)는 "미검증"으로 SKILL.md 표·보고에 적는다.

## 6. 문서에 적고 커밋한다
- 넣은 스킬의 SKILL.md에 사용법 한 줄과 함정을 적는다. chrome-direct면 Scenarios 표에 한 행을 넣고 Verified 칸을 채운다.
- 새 기능이면 그 스킬 description에 트리거 문구를 더한다(예: "애드센스", "광고 붙여").
- `~/.claude`에서 파일을 개별로 `git add`하고, `commit`과 `push`를 한다.
- 사용자에게는 짧게 보고한다. 형식: `스크립트화: <경로> — <한 줄 사용법> (검증: 됨/미검증 이유)`. 만들지 않았으면 `스크립트화 안 함: <이유>`.
