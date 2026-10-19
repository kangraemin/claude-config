# Global Rules

## 세션 시작 시 필수 <!-- why: decisions/_global/process/session-start-global-settings-and-library.md -->
- 작업 시작 전 반드시 `~/.claude/settings.json` 글로벌 설정을 확인하고 hooks, env 등 설정을 파악할 것
- 프로젝트 로컬 설정만 보지 말고 글로벌 설정도 함께 확인
- 기술 작업 시작 전: `ToolSearch("select:mcp__claude-library__library_search")` 로드 후 작업 키워드로 `library_search()` 호출

## 스킬 우선 사용 <!-- why: decisions/_global/process/use-matching-skills-before-custom-work.md -->
- 작업 시작 전 available skills 목록을 확인하고, 매칭되는 스킬이 있으면 반드시 Skill 도구로 실행한다. 직접 수행 금지.
- 세션을 이어받을 때도 동일하게 스킬/에이전트 매칭을 재점검한다.
- 웹·콘솔 조작(Chrome 직접·Codex 위임)이 들어간 작업을 끝내면 `web-scriptify` 스킬로 그 과정을 스크립트화한다(불가능하면 안 함).

## ralph-x in-session 루프 — 절대 멈추지 말 것 <!-- why: decisions/_global/process/ralph-x-continue-until-declared-exit.md -->
- ralph-x in-session 루프(`ralph-x-runs/*/session-state.json`에 `active=true`) 진행 중에는 **절대 멈추지 않는다**.
- **종료 조건은 단 두 가지**: `current_iteration >= max_iterations` OR checklist의 모든 항목 `[x]`. 그 전에 종료/대기 금지.
- 결과 fail이든 success든, 가설이 막혀 보이든, 사용자가 질문하든 — **무조건 같은 응답에서 다음 iter Write/Bash로 즉시 진행**.
- **금지**: "어떻게 갈지 정해주면", "방향 전환 필요", "이거 의미 있나", "계속 진행할까요?" 등 사용자 컨펌 요청.
- **금지**: fail N개 누적 후 "남은 X개 같은 패턴 반복 무의미" 자체 판단으로 멈추기.
- **필수**: 결과 짧게 보고 → 즉시 다음 가설 코드 작성·실행. 가설 떨어지면 시도 안 한 영역 자체 발굴(레버리지/단일주식/시간대/매크로/페어/ML 등).
- **사용자 명시 룰**: "갯수 다 돌 때까지 사용자 컨펌 절대 받지 말고 니 알아서 판단·수정·결과 내라"

## 블로그 글 발행은 허가 후 <!-- why: decisions/_global/process/blog-post-publish-needs-user-approval-via-telegram.md -->
- 블로그(사용자 이름으로 공개되는 글)에 새 글 발행·기존 글 본문 수정은 **사용자 허가 없이 금지**. 초안 작성까지만 한다.
- 허가 요청은 텔레그램으로: `source ~/.claude/.env; curl -s -d chat_id=$CONTEST_TG_CHAT_ID --data-urlencode text="[블로그 발행 허가 요청] 제목/요약/초안 위치" https://api.telegram.org/bot$CONTEST_TG_TOKEN/sendMessage`
- 승인 답장(텔레그램 또는 대화창) 받은 뒤에만 커밋·push·게시. 답 없으면 발행하지 않고 보고.

## 토큰 절약 <!-- why: decisions/_global/process/reduce-session-context-overhead.md -->
- 단순 셸 명령(ls, pwd, which 등)은 `!` prefix로 직접 실행. Claude 컨텍스트 소비 불필요.
- 컨텍스트가 무거워지면 `/compact` 또는 세션 정리 후 `/clear`.

## 환경변수 조회 순서 <!-- why: decisions/_global/process/lookup-project-then-global-env.md -->
- 환경변수가 없다고 바로 포기하지 말고 프로젝트 `.env` → `~/.claude/.env` 순으로 직접 뒤져라.
- 빌드/배포 스크립트 실행 시 `source .env && <명령>` 으로 환경변수 주입 후 실행한다.

## 공식 문서 우선 <!-- why: decisions/_global/process/verify-support-in-official-docs.md -->
- 기능/설정을 적용하기 전에 **공식 문서에서 지원 여부를 확인**한다. 학습 데이터 기반 추측으로 적용 금지.
- 확인 불가 시 사용자에게 "공식 확인 안 됨"을 명시한다.

## 규칙 우선순위 <!-- why: decisions/_global/convention/project-rules-override-global.md -->
- 프로젝트 `.claude/rules/git-rules.md` > 글로벌 `~/.claude/rules/git-rules.md`
- 프로젝트 `.claude/settings.json` env 값 > 글로벌 env 값
- `COMMIT_LANG=en`이면 커밋 메시지를 영어로 작성 (기본: 한글)

## Hook 차단 시 금지 행동 <!-- why: decisions/_global/process/preserve-blocked-hook-state.md -->
- bash-gate, plan-gate, completion-gate 등 ai-bouncer hook이 차단하면 **임의로 state.json을 수정하거나 .active 파일을 삭제하지 않는다.**
- 차단된 이유를 사용자에게 그대로 보고하고, 어떻게 처리할지 지시를 받는다.
- 다른 세션의 작업일 수 있으므로 절대 임의 판단으로 cancelled/done 처리 금지.

## 소통 스타일 <!-- why: decisions/_global/convention/concise-communication-without-repeat-options.md -->
- 핵심만 간결하게 답한다. 장황한 설명 금지.
- 선택지를 줄 때는 추천 순서로 정렬하고, 최선이 명확하면 바로 추천한다.
- 이미 사용자가 선택한 옵션을 다시 옵션 목록으로 되묻지 않는다. 결정됐으면 실행한다.

## 설명 UI 글쓰기 <!-- why: decisions/_global/convention/explainer-ui-one-sentence-per-line.md -->
- 안내·소개·도움말 등 설명하는 UI 글은 `짧은 제목` 아래 `- 문장` 줄로 쓴다.
- 한 줄에 의미(문장) 하나만. 문단으로 이어 쓰기 금지.

## 실행 원칙 <!-- why: decisions/_global/process/execute-authorized-actions-in-same-turn.md -->
- "권장 조치", "추가할 만한", "추천합니다", "제안드립니다", "고려해볼 만" 식으로 할 일을 나열만 하고 응답 끝내는 거 금지.
- 파일 변경 / library 저장 / 커밋 / 설정 갱신 등 **실행 가능한 항목은 그 응답 안에서 즉시 실행**한다. 사용자가 "그래서 해" 라고 다시 말하게 만들지 않는다.
- 위험하거나 되돌리기 어려운 작업(force push, prod 배포·DB 변경, 외부 메시지 발송 등)만 사전 확인. 그 외엔 실행 후 결과 보고.
- 분석/조사 결과를 번호 목록으로 정리했다고 해서 "리포트 모드"로 빠지지 않는다. 정리 + 실행을 같은 턴에 끝낸다.

## 규칙 파일 <!-- why: decisions/_global/convention/reference-rule-files-on-demand.md -->
- git/커밋: `~/.claude/rules/git-rules.ref`
- 자동커밋: `~/.claude/rules/auto-commit-rules.ref`
- 워크로그: `~/.claude/rules/worklog-rules.ref`
- 코드리뷰: `~/.claude/rules/review-rules.ref`
- 글쓰기: `~/.claude/rules/writing-style.ref`

## Library 시스템 <!-- why: decisions/_global/architecture/library-catalog-and-marker-owned-rules.md -->

참조: `~/claude-library/GUIDE.md`

### 목차
- finance — **주식 진입타이밍 알파 0**·리스크오버레이/분산, **중첩거래·MTF 룩어헤드 금지**, **금 레버 금지·레버 월간 리밸런스**, 시장급락 반등·fold 검증 — `~/claude-library/CATALOG.md` 참조
- tooling — **그래프DB 소규모엔 과잉**·하이브리드 검색/무주입 기본, **재생성 무손실·멱등성·원문 보존**, **테스트 초록≠시각 정합**·Granite 폰트 번들 불가, **게이트 면제 구멍·fail-closed·탈출구 독립**, **uvx는 PyPI판**·Workflow 세션 한도, **영상 템플릿 무인자동화=Remotion/AE(Premiere·CapCut 부적합)**, **검증은 원본대조와 결론과장 감사 분리** — `~/claude-library/CATALOG.md` 참조
- api — 앱인토스 **광고 사업자 필수**·공유 실유입 별도 추적, **목록 0건≠빈 시장**·비게임 3D 제약, YouTube uploads 순서 미보장, **HTTP 200≠유효 payload**·Xotelo 실키 — `~/claude-library/CATALOG.md` 참조
- database — 부분인덱스·RPC 집계, SSR seed, 정렬 tie-break, **pg_bigm 긴 문서 탈락**·필드가중/IDF — `~/claude-library/CATALOG.md` 참조
- product — 기능 기본값, 필터 반환 컬럼, 검색/SSR 경로 정합 — `~/claude-library/CATALOG.md` 참조
- testing — Babel 별칭 rewrite, Jest mock 무력화, inline jest.mock — `~/claude-library/CATALOG.md` 참조
- concurrency — in-flight 시간 상한, **동일 수치 반복=판정식 의심**, **큐 0≠처리 완료**, claim 순서, 뒷단 독립 스케줄/deadline — `~/claude-library/CATALOG.md` 참조
- data-pipeline — **소스 라벨≠실제 내용**, 제목 표본 분류, 보존창, 요약 보유/미보유 구분 — `~/claude-library/CATALOG.md` 참조
- mobile — iOS inactive 복귀, Android 폰트 축소, RN 플랫폼 차이 — `~/claude-library/CATALOG.md` 참조
- web-scraping — **중간 소프트 스로틀**, 연속 실패 차단/런 상한, **프로세스 생존≠건강**, **md5 빈도·내용 기준 월별 감사**, **크몽 옵션가=로그인 주문화면 전용(미결제 주문 생성)·스마트스토어 IP 429** — `~/claude-library/CATALOG.md` 참조
- game — Unity 라이선스/batchmode, WebGL swiftshader, 코루틴 scale/좌표 — `~/claude-library/CATALOG.md` 참조
- infra — **Supabase 직결 'tenant not found'=풀러 aws-0→aws-1 이전**(REST 대량배치 오진 금지), **Turso --from-dump 0B·shell 70초 끊김·unistr()** — `~/claude-library/CATALOG.md` 참조

<!-- learnings-for-claude:rules start -->

### 읽기
- 툴: `library_search` `library_read` `library_list` / `decision_list(repo)` `decision_search` `decision_read`
- `library_search`는 **deferred tool** — 매 세션/작업 시작 시 반드시 먼저 `ToolSearch("select:mcp__claude-library__library_search")`로 로드한 뒤 사용한다
- 아래 상황에서 **반드시** `library_search(query)`를 호출한다:
  - 기술 질문에 답하거나 접근법을 제안할 때
  - 구현을 시작할 때
  - 에러/삽질이 발생했을 때 — 이미 기록된 해결책이 있을 수 있다
- 결과가 있으면 `📚 library 참조: [topic]`로 시작하고 저장된 내용을 따른다
- 결과가 없으면 별도 언급 없이 진행한다
- 관련 주제가 발견되면 `library_read(path)`로 index.md를 읽어 상세 확인
- 이미 기록된 방향은 재제안하지 않는다

### 쓰기
아래 경우 library에 기록한다:
- 실험/백테스트 결론이 났을 때
- 아티클/논문에서 유효한 인사이트를 얻었을 때
- 사용자가 접근법을 수정했을 때
- 더 나은 방법을 발견했을 때
- **개발 중 삽질로 알게 된 API/라이브러리 동작** — 에러로 발견한 것, 문서에 없는 것, 다음에 또 삽질할 것 같은 것. 발견 즉시 기록한다. 사용자가 요청하기 전에.
- **틀린 내용을 교정받았을 때** — "그게 아니야"라고 교정받으면 그 자리에서 바로 저장. "저장할까요?" 묻지 않는다.


### 지식이냐 결정사항이냐 — 먼저 가른다

| | 지식 `library/` | 결정사항 `decisions/` |
|---|---|---|
| 판별 | **남의 프로젝트에도 그대로 참** | **우리가 이렇게 하기로 정한 것** |
| 예 | "Granite에 react-native-svg 이미 번들됨" | "우리는 통과조건을 셸로 표현한다" |
| 분류 | 카테고리/서브카테고리/주제 | **레포별 → 카테고리별** |
| 꺼내기 | `library_search` (pull) | SessionStart 자동 주입 (push) |

결정사항 카테고리 5개 고정: `architecture` `stack` `convention` `process` `scope`
경로: `~/claude-library/decisions/<레포명>/<카테고리>/<slug>.md` (레포명 = git remote basename)

### 형식 — OKF v0.2

모든 문서는 Open Knowledge Format v0.2 프론트매터를 갖는다. `type`이 유일한 필수 필드.
**상세 규칙·필드·이유는 `~/claude-library/GUIDE.md` 를 읽어라.** 여기에 중복 기술하지 않는다
(같은 규칙을 두 곳에 적어서 실제로 드리프트가 난 전례가 있다).

분류는 `~/claude-library/TAXONOMY.md`를 먼저 확인하고, 없으면 거기에 먼저 추가한다.

기록 방법:
1. **지식/결정사항 판별** → 저장소 결정
2. TAXONOMY.md 확인 (지식) 또는 레포·카테고리 확정 (결정사항)
3. 파일 생성 — OKF 프론트매터 + 교훈이 드러나는 파일명 (날짜 없음)
4. **`index.md` / `LIBRARY.md` 는 손대지 않는다.** 자동 생성 대상이다
5. **Synthesis 체크**: 같은 서브카테고리 3개 이상이면 종합 문서 검토 → `library/synthesis/`
6. `~/claude-library/CATALOG.md` 에 한 줄 요약 추가 (CLAUDE.md `### 목차`는 카테고리 요약만 — 새 카테고리·핵심 결론일 때만 갱신)
7. 즉시 commit/push:
   ```
   git -C ~/claude-library add -A
   git -C ~/claude-library commit -m "feat: [주제] 추가"
   git -C ~/claude-library push
   ```
8. 한 줄로 알린다: `📚 library에 추가: [경로]`

- **사용자가 정한 결정은 메모리에만 두지 않는다** — 자동 메모리(memory/*.md)는 그 프로젝트·계정 세션에만 보인다. "~하기로 함"·"~안 한다고 했잖아" 같은 결정은 한 프로젝트 전용이어도 `decisions/<레포|_global>/<카테고리>/`에 쓴다(메모리엔 포인터만).

미결 상태는 기록하지 않는다.
<!-- learnings-for-claude:rules end -->


# --- ai-bouncer-rule start ---
## ai-bouncer 필수 규칙 <!-- why: decisions/_global/process/dev-bounce-before-development.md -->

**절대 금지**: `/dev-bounce` 스킬 호출 없이 Edit / Write / Bash로 소스 파일을 수정하는 것.

- 코드 수정 / 기능 구현 / 버그 수정 / 파일 변경 등 **모든 개발 작업** 전에 반드시 `Skill("dev-bounce")`를 호출한다.
- 사용자 메시지에 `/dev-bounce`가 포함되어 있으면 **가장 먼저** Skill 도구로 실행한다. 다른 어떤 행동보다 우선.
# --- ai-bouncer-rule end ---
