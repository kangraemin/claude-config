# Global Rules

## 세션 시작 시 필수
- 작업 시작 전 반드시 `~/.claude/settings.json` 글로벌 설정을 확인하고 hooks, env 등 설정을 파악할 것
- 프로젝트 로컬 설정만 보지 말고 글로벌 설정도 함께 확인

## 스킬 우선 사용
- 작업 시작 전 available skills 목록을 확인하고, 매칭되는 스킬이 있으면 반드시 Skill 도구로 실행한다. 직접 수행 금지.
- 세션을 이어받을 때도 동일하게 스킬/에이전트 매칭을 재점검한다.


## 토큰 절약
- 단순 셸 명령(ls, pwd, which 등)은 `!` prefix로 직접 실행. Claude 컨텍스트 소비 불필요.
- 컨텍스트가 무거워지면 `/compact` 또는 세션 정리 후 `/clear`.

## 환경변수 조회 순서
- 환경변수가 없다고 바로 포기하지 말고 프로젝트 `.env` → `~/.claude/.env` 순으로 직접 뒤져라.
- 빌드/배포 스크립트 실행 시 `source .env && <명령>` 으로 환경변수 주입 후 실행한다.

## 공식 문서 우선
- 기능/설정을 적용하기 전에 **공식 문서에서 지원 여부를 확인**한다. 학습 데이터 기반 추측으로 적용 금지.
- 확인 불가 시 사용자에게 "공식 확인 안 됨"을 명시한다.

## 규칙 우선순위
- 프로젝트 `.claude/rules/git-rules.md` > 글로벌 `~/.claude/rules/git-rules.md`
- 프로젝트 `.claude/settings.json` env 값 > 글로벌 env 값
- `COMMIT_LANG=en`이면 커밋 메시지를 영어로 작성 (기본: 한글)

## Hook 차단 시 금지 행동
- bash-gate, plan-gate, completion-gate 등 ai-bouncer hook이 차단하면 **임의로 state.json을 수정하거나 .active 파일을 삭제하지 않는다.**
- 차단된 이유를 사용자에게 그대로 보고하고, 어떻게 처리할지 지시를 받는다.
- 다른 세션의 작업일 수 있으므로 절대 임의 판단으로 cancelled/done 처리 금지.

## 소통 스타일
- 핵심만 간결하게 답한다. 장황한 설명 금지.
- 선택지를 줄 때는 추천 순서로 정렬하고, 최선이 명확하면 바로 추천한다.

## 규칙 파일
- git/커밋: `~/.claude/rules/git-rules.ref`
- 자동커밋: `~/.claude/rules/auto-commit-rules.ref`
- 워크로그: `~/.claude/rules/worklog-rules.ref`
- 코드리뷰: `~/.claude/rules/review-rules.ref`
- 글쓰기: `~/.claude/rules/writing-style.ref`

## Library 시스템
참조: `~/.claude/.claude-library/GUIDE.md`

# --- ai-bouncer-rule start ---
## ai-bouncer 필수 규칙

**절대 금지**: `/dev-bounce` 스킬 호출 없이 Edit / Write / Bash로 소스 파일을 수정하는 것.

- 코드 수정 / 기능 구현 / 버그 수정 / 파일 변경 등 **모든 개발 작업** 전에 반드시 `Skill("dev-bounce")`를 호출한다.
- 사용자 메시지에 `/dev-bounce`가 포함되어 있으면 **가장 먼저** Skill 도구로 실행한다. 다른 어떤 행동보다 우선.
# --- ai-bouncer-rule end ---
