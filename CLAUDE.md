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

## 글쓰기 스타일
- LinkedIn 포스트, 블로그 등 글 작성 시 `~/.claude/rules/writing-style.md` 를 따른다.


## Library 시스템

참조: `~/.claude/.claude-library/GUIDE.md`

### 읽기
- 새 실험/전략 제안 전, 막히는 상황에서 `~/.claude/.claude-library/LIBRARY.md`를 읽는다
- 관련 카테고리/주제 폴더의 `index.md`를 찾아 읽는다
- 참조한 항목이 있으면 한 줄로 알린다: `📚 library 참조: [경로]`
- 이미 기록된 방향은 재제안하지 않는다

### 쓰기
아래 경우 library에 기록한다:
- 실험/백테스트 결론이 났을 때
- 아티클에서 유효한 인사이트를 얻었을 때
- 사용자가 접근법을 수정했을 때
- 더 나은 방법을 발견했을 때
- **개발 중 삽질로 알게 된 API/라이브러리 동작** — 에러로 발견한 것, 문서에 없는 것, 다음에 또 삽질할 것 같은 것. 발견 즉시 기록한다. 사용자가 요청하기 전에.

기록 방법:
1. 카테고리 판단 (equity, crypto, ml, macro, claude 등)
2. 주제 폴더 확인/생성: `~/.claude/.claude-library/library/[카테고리]/[주제]/`
3. 지식 파일 생성 (내용 설명하는 이름, 날짜 없음)
4. 주제 `index.md` 생성/업데이트
5. `~/.claude/.claude-library/LIBRARY.md` 업데이트
6. 즉시 commit/push:
   ```
   git -C ~/.claude/.claude-library add -A
   git -C ~/.claude/.claude-library commit -m "feat: [주제] 추가"
   git -C ~/.claude/.claude-library push
   ```
7. 한 줄로 알린다: `📚 library에 추가: [경로]`

미결 상태는 기록하지 않는다.

## Project Doc 자동 제안

아래 중 하나라도 해당하는 작업을 마쳤으면, PROJECT.md 갭을 체크하고 제안한다:
- 새 기능/모듈 완성
- 파일·폴더 구조 변경
- 접근법을 바꿈 (pivot)
- 삽질 끝에 중요한 것을 알게 됨

PROJECT.md가 없으면: "PROJECT.md 없는데 만들까?" 한 줄만 제안.
PROJECT.md가 있으면: 반영 안 된 내용이 있을 때만 "이번 작업 PROJECT.md에 반영할까?" 제안.
없으면 아무 말도 하지 않는다.
