# Global Rules

## 스킬 우선 사용 <!-- why: decisions/_global/process/use-matching-skills-before-custom-work.md -->
- 웹·콘솔 조작(Chrome 직접·Codex 위임)이 들어간 작업을 끝내면 `web-scriptify` 스킬로 그 과정을 스크립트화한다(불가능하면 안 함).

## 묻지 말고 끝까지 한다 <!-- why: decisions/_global/process/finish-to-the-end-without-asking-user.md -->
- 시킨 일은 중간에 "할까요?", "괜찮으면 '올려'라고 해 주세요", "어떻게 할지 정해 주세요"로 멈추지 않고 끝까지 한다.
- 사용자가 결과물(사진·화면)을 보고 싶다고 한 경우에도 보여 주고 바로 다음 단계로 간다. 답을 기다리지 않는다.
- **사용자 사전 동의(2026-10-22): "앞으로 니가 하는 거 전부 다 동의할 테니까 멈추지 마라."** 출시 버튼, 콘솔 약관·동의 체크, 서명형 확인 체크박스, 공개 글 발행까지 묻지 않고 진행한다.
- 남는 예외는 물리적으로 사람만 할 수 있는 단계뿐이다: 결제 본인인증, 문자 인증번호, 토스 앱에서 직접 열기, 실물 도장.
- 플랫폼이 사람 손을 요구하는 단계(토스 앱에서 열기, 문자 인증번호)만 짧게 요청하고, 나머지는 그 전후로 다 해 둔다.

## 사용자에게 넘기기 전 기존 스크립트부터 찾는다 <!-- why: decisions/_global/process/search-existing-scripts-before-handing-step-to-user.md -->
- 로그인·본인인증(PASS/문자)·보안문자·결제 전 단계처럼 "사람이 해야 할 것 같은" 단계를 사용자에게 넘기기 **전에** 아래를 먼저 찾는다.
- 스크립트 위치: `~/.claude/skills/chrome-direct/scenarios/`(웹 조작 시나리오, 목록은 같은 폴더 `../SKILL.md` Scenarios 표), `~/.claude/skills/*/scripts/`.
- 찾는 법: `grep -rli "<키워드>" ~/.claude/skills/*/scripts ~/.claude/skills/chrome-direct/scenarios ~/.claude/skills/chrome-direct/SKILL.md` (예: 본인인증·통신사·문자·mobile-ok·로그인).
- 개인정보 쪽 지시도 확인: `~/Documents/oguri-works/개인정보.md`에 통신사·인증 방식 같은 처리법이 적혀 있다.
- 스토어·광고 개발자 계정(AdMob·Play Console·Apple Developer) 로그인과 남은 인증 단계: `~/Documents/oguri-works/계정.md` '스토어·광고 개발자 계정' 표.
- 본인인증(문자)은 통신사·이름·생년월일·번호를 내가 넣고, 사용자에게는 **문자로 온 인증번호만** 묻는다.

## ralph-x in-session 루프 — 절대 멈추지 말 것 <!-- why: decisions/_global/process/ralph-x-continue-until-declared-exit.md -->
- `ralph-x-runs/*/session-state.json`이 `active=true`면 종료 조건(`current_iteration >= max_iterations` 또는 체크리스트 전부 `[x]`) 전에는 멈추지 않는다. fail이 쌓여도 사용자 컨펌 없이 결과 한 줄 보고 후 같은 응답에서 다음 가설을 실행한다(Stop 훅 `ralph-x-gate.sh`가 강제).

## Codex 사용 범위 <!-- why: decisions/_global/process/codex-only-for-image-web-computer-use-or-when-claude-cannot.md -->
- Codex는 이미지 생성·웹 작업·컴퓨터 유즈에만 쓴다.
- 웹 작업은 LLM 없이 도는 기존 웹 조작 스크립트(`chrome-direct` scenarios, `~/.claude/skills/*/scripts/`)를 먼저 찾아 쓴다. 스크립트가 없어도 chromectl 등으로 스크립트 조작이 가능하면 그걸로 한다. 그게 안 될 때만 Codex로 조작한다.
- 요약·추출·글쓰기·개발 등 나머지는 Claude가 한다.
- Claude가 못 하는 일이면 Codex를 쓴다.
- 사용자가 "코덱스로 해"라고 하면 그때 Codex로 한다.
- Claude 한도 초과 시 Codex로 자동 전환(fallback) 금지.

## Anthropic API 크레딧 <!-- why: decisions/_global/process/anthropic-api-credit-shared-100usd-avoid-in-tests-benchmark-in-prod.md -->
- 매달 받는 API 크레딧은 월 $200 한도 안에서 돈 되는 상용 서비스들이 나눠 쓴다. API가 없어서 못 만드는 서비스가 없게 한다.
- 개발·테스트에선 최대한 피한다: 목업·녹화 응답·규칙·`claude -p`·로컬 LLM. 실제 호출 테스트는 최소 건수만.
- 상용은 실제 입력 표본으로 모델(Haiku·Sonnet·Opus 등)을 벤치마크해 품질 기준을 넘는 것 중 가장 적절한 것을 쓴다. 서비스별 키·월 예산 상한을 둔다.

## 토스 테스트 배포는 링크로 준다 <!-- why: decisions/_global/process/toss-test-deploy-always-send-tappable-link.md -->
- `ait deploy` 후에는 QR만 보내지 말고 **누르면 열리는 링크를 항상 같이** 준다.
- 형식: `https://httpbin.org/redirect-to?url=<ait deploy가 출력한 intoss-private:// 링크를 URL 인코딩>`
- 배포마다 deploymentId가 바뀌므로 매번 새 링크를 준다.

## 블로그 글 발행은 허가 후 <!-- why: decisions/_global/process/blog-post-publish-needs-user-approval-via-telegram.md -->
- 개인 개발 블로그(kangraemin.github.io)는 사용자가 "올려"라고 콕 집은 글만 발행한다(10/22). 사전 동의 해당 없음.
- (2026-10-22 사용자 전면 사전 동의로 대체) 개인 블로그 외 발행은 묻지 않고 진행한다. 발행한 뒤 텔레그램으로 알림만 보낸다.

## SNS 게시 알림은 텔레그램 SNS 봇으로 <!-- why: decisions/_global/process/telegram-notify-after-every-sns-upload.md -->
- **SNS에 무엇이든 올리기 전에 `sns-post` 스킬을 먼저 연다**(계정·프로필, 하루 1개·출시 큐, 중복 확인, 게시 스크립트, 알림). 어느 세션·레포든 같다.
- SNS(인스타·스레드·X·유튜브·블로그·답글 등, 모든 계정)에 올리면 바로 @sns_daily_noti_bot으로 "[업로드 완료] 서비스 계정 링크" + 본문 + 사진·영상을 보낸다.
- 올리기 전 확인 요청도 같은 봇으로 "[게시 확인 요청]"을 보낸다.
- 도구: `python3 ~/.claude/scripts/sns_tg.py done|ask --msg "..." [--text-file f] [사진·영상]`. my-sns·insta-web 게시 스크립트는 성공 시 자동으로 보낸다.
- 키: `~/.claude/.env`의 SNS_UPLOAD_TG_TOKEN / SNS_UPLOAD_TG_CHAT_ID. 공모전 봇(CONTEST_TG)으로 보내지 않는다.

## 환경변수 조회 순서 <!-- why: decisions/_global/process/lookup-project-then-global-env.md -->
- 환경변수는 프로젝트 `.env` → `~/.claude/.env` 순으로 찾고, `source .env && <명령>`으로 주입한다.

## 공식 문서 우선 <!-- why: decisions/_global/process/verify-support-in-official-docs.md -->
- 기능/설정을 적용하기 전에 **공식 문서에서 지원 여부를 확인**한다. 학습 데이터 기반 추측으로 적용 금지.
- 확인 불가 시 사용자에게 "공식 확인 안 됨"을 명시한다.

## 규칙 우선순위 <!-- why: decisions/_global/convention/project-rules-override-global.md -->
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
- 기술 질문에 답하거나, 구현을 시작하거나, 에러가 나면 `library_search(query)`를 부른다. deferred tool이라 먼저 `ToolSearch("select:mcp__claude-library__library_search")`로 로드한다.
- 결과가 있으면 `📚 library 참조: [topic]`로 시작하고 저장된 내용을 따른다. 이미 기록된 방향은 재제안하지 않는다.
- 결정사항(`decisions/`)은 SessionStart에 자동 주입된다. 전문은 `decision_read`, 세션 중 추가분은 `decision_search`.

### 쓰기
- 기록 대상: 실험·백테스트 결론, 삽질로 알게 된 API·라이브러리 동작, 사용자 교정("그게 아니야"), 더 나은 방법. 묻지 말고 그 자리에서 기록한다.
- 먼저 가른다: 남의 프로젝트에도 참이면 지식 `library/<카테고리>/...`(TAXONOMY.md 먼저 확인), 우리가 정한 것이면 결정 `decisions/<레포|_global>/<architecture|stack|convention|process|scope>/<slug>.md`.
- 사용자가 정한 결정은 메모리에만 두지 않는다. 한 프로젝트 전용이어도 decisions/에 쓰고 메모리엔 포인터만 둔다.
- 형식(OKF v0.2 프론트매터, `type` 필수)은 `~/claude-library/GUIDE.md`를 따른다. 파일명은 교훈이 드러나게, 날짜 없이. `index.md`·`LIBRARY.md`는 자동 생성이라 손대지 않는다.
- 저장 후 `CATALOG.md`에 한 줄 추가 → `git -C ~/claude-library add -A && git -C ~/claude-library commit -m "feat: [주제] 추가" && git -C ~/claude-library push` → `📚 library에 추가: [경로]` 한 줄로 알린다.
- 미결 상태는 기록하지 않는다.
<!-- learnings-for-claude:rules end -->


# --- ai-bouncer-rule start ---
## ai-bouncer 필수 규칙 <!-- why: decisions/_global/process/dev-bounce-before-development.md -->

**절대 금지**: `/dev-bounce` 스킬 호출 없이 Edit / Write / Bash로 소스 파일을 수정하는 것.

- 코드 수정 / 기능 구현 / 버그 수정 / 파일 변경 등 **모든 개발 작업** 전에 반드시 `Skill("dev-bounce")`를 호출한다.
- 사용자 메시지에 `/dev-bounce`가 포함되어 있으면 **가장 먼저** Skill 도구로 실행한다. 다른 어떤 행동보다 우선.
# --- ai-bouncer-rule end ---
