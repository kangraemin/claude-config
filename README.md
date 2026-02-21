# Claude Code Global Config

Claude Code 글로벌 설정 — 모든 프로젝트에 공통 적용되는 에이전트, 커맨드, 규칙, 훅.

## 설치

```bash
bash <(curl -sL https://raw.githubusercontent.com/kangraemin/claude-config/main/install.sh)
```

- 전역 설치: `~/.claude/`에 클론
- 로컬 설치: 현재 레포 `.claude/`에 agents/commands/rules만 복사 (`bash install.sh --local`)

### 의존성

| 도구 | 용도 |
|------|------|
| `git` | 버전 관리 |
| `node` | ccusage 실행 |
| `jq` | hooks 데이터 처리 |
| `gh` | GitHub PR/이슈 |
| `ccusage` | 토큰 사용량 추적 (install.sh에서 자동 설치) |

## 구조

```
~/.claude/
├── CLAUDE.md                # 글로벌 규칙 (세션 시작 시 자동 로드)
├── settings.json            # hooks, env, permissions, statusLine
├── install.sh               # 원라인 설치 스크립트
│
├── agents/                  # 에이전트 역할 정의
│   ├── lead.md              #   리드 — 단계 설계, 태스크 할당
│   ├── dev.md               #   개발 — 구현, 워크로그 작성
│   ├── qa.md                #   QA — 테스트, 빌드 검증
│   ├── reviewer.md          #   리뷰어 — 코드 리뷰, PR 코멘트
│   └── git.md               #   Git — 복잡한 git 워크플로우
│
├── commands/                # 슬래시 커맨드 (/이름 으로 실행)
│   ├── commit.md            #   /commit — 커밋 + 워크로그 + 푸시
│   ├── push.md              #   /push — 안전한 푸시
│   ├── pr.md                #   /pr — PR 생성
│   ├── review.md            #   /review — 코드 리뷰
│   ├── test.md              #   /test — 프로젝트별 테스트 실행
│   ├── status.md            #   /status — 현재 상태 요약
│   ├── dev.md               #   /dev — 에이전트 팀으로 개발 시작
│   ├── init-project.md      #   /init-project — 개발 가이드 생성
│   ├── worklog.md           #   /worklog — 워크로그 작성
│   └── reflection.md        #   /reflection — 세션 회고 + 설정 개선
│
├── rules/                   # 규칙 (커맨드/에이전트가 참조)
│   ├── git-rules.md         #   커밋, 푸시, PR, 브랜치 규칙
│   ├── worklog-rules.md     #   워크로그 생성/구조/토큰 추적
│   └── review-rules.md      #   코드 리뷰 관점, 심각도, 원칙
│
├── hooks/                   # Claude Code hooks (settings.json에서 등록)
│   ├── worklog.sh           #   PostToolUse — 도구 사용 수집
│   ├── auto-commit.sh       #   Stop — 미커밋 변경사항 → /commit 실행
│   └── session-end.sh       #   SessionEnd — 수집 데이터 정리
│
├── git-hooks/               # Git hooks (core.hooksPath로 글로벌 적용)
│   └── pre-commit           #   워크로그 fallback 생성 + git add
│
└── .worklogs/               # 워크로그 저장소
    ├── YYYY-MM-DD.md        #   날짜별 워크로그 (커밋마다 append)
    └── .snapshot            #   토큰/시간 스냅샷 (git 추적 안 함)
```

## 커맨드

| 커맨드 | 설명 |
|--------|------|
| `/commit` | git-rules.md 기반 커밋 → 워크로그 → 푸시 |
| `/push` | 안전한 푸시 (force 금지, upstream 확인) |
| `/pr` | 한글 PR 생성 (리뷰 포인트, 변경 요약 포함) |
| `/review [PR번호]` | 코드 리뷰. PR 번호 주면 PR 인라인 코멘트, 없으면 로컬 diff 리뷰 |
| `/test` | 프로젝트 타입 자동 감지 후 테스트 실행 |
| `/status` | git + 프로젝트 상태 요약 |
| `/dev` | 에이전트 팀(lead/dev/qa) 스폰 → 개발 시작. 가이드 없으면 자동 생성 |
| `/init-project` | 대화하며 DEVELOPMENT_GUIDE.md + docs/ 생성 |
| `/worklog` | 요청사항, 작업내용, 변경통계, 토큰 delta 기록 |
| `/reflection` | 세션 대화를 분석하고 CLAUDE.md/rules/settings 개선 제안 |

## 에이전트

`/dev`로 팀을 스폰하면 아래 에이전트가 협업합니다.

```
Lead: Phase 설계 → 사용자 승인 → 태스크 생성/배정
  ↓
Dev: 태스크 구현 → 커밋 + 워크로그 → 완료 보고
  ↓
QA: 테스트/빌드 검증 → 통과/반려
  ↓
Lead: Step 완료 확인 → 다음 Step 또는 Phase
```

| 에이전트 | 역할 |
|----------|------|
| **lead** | 단계 설계, 태스크 분배, 최종 승인 |
| **dev** | DEVELOPMENT_GUIDE.md 기반 구현, git-rules.md 준수 |
| **qa** | 테스트 작성, 빌드 검증, 통과/반려 판정 |
| **reviewer** | 코드 리뷰, 심각도 분류, PR 인라인 코멘트 |
| **git** | 복잡한 rebase, merge conflict 등 git 전문 작업 |

에이전트는 글로벌(역할)이고, 프로젝트별 규칙은 각 레포의 `DEVELOPMENT_GUIDE.md`에 정의.

## 규칙

### 커밋 규칙 (git-rules.md)

- **한글** 커밋 메시지, type만 영어: `feat: 자연어 검색 기능 추가`
- 50자 이내, HEREDOC 사용
- `git add .` 금지, 파일 개별 staging
- 커밋과 푸시는 항상 세트
- Co-Authored-By 자동 추가

### 리뷰 규칙 (review-rules.md)

7가지 관점 우선순위: 버그 > 보안 > 에러 핸들링 > 성능 > 설계 > 테스트 > 가독성

심각도 3단계:
- **Critical**: 버그, 보안, 데이터 손실 → 반드시 수정
- **Important**: 설계, 에러 핸들링, 성능 → 수정 권장
- **Minor**: 네이밍, 스타일, 개선 제안 → 선택

### 권한 (settings.json)

3단계 권한 모델:
- **allow**: WebSearch, WebFetch, Bash, Read, Write, Edit
- **deny**: `rm -rf`, `rm -fr` (차단)
- **ask**: sudo, 민감파일 읽기 (.env, .ssh, .aws, credentials, .pem, .key)

## Hooks

| 이벤트 | 훅 | 동작 |
|--------|-----|------|
| PostToolUse | `worklog.sh` | 도구 사용 기록 수집 |
| Stop | `auto-commit.sh` | 미커밋 변경사항 → `/commit` 플로우 실행 |
| SessionEnd | `session-end.sh` | 수집 데이터 정리 |
| pre-commit (git) | `git-hooks/pre-commit` | 워크로그 fallback + git add |

## 워크로그 시스템

커밋마다 `.worklogs/YYYY-MM-DD.md`에 기록:

```markdown
## 13:37

### 요청사항
- 사용자 요청 정리

### 작업 내용
- 작업 요약

### 변경 통계
(git diff --cached --stat)

### 토큰 사용량
- 이번 작업: 1,234,567 토큰 / $1.23
- 소요 시간: 15분
- 일일 누적: 29,760,365 토큰 / $17.87
```

- **`/commit` 경유**: 요청사항 + 작업내용 + ccusage 토큰 delta 기록
- **auto-commit (fallback)**: pre-commit 훅이 변경통계만 기록
- **토큰 delta**: `.worklogs/.snapshot`에 이전 값 저장 → 차이 계산

## 업데이트

```bash
cd ~/.claude && git pull
```

## 프로젝트별 설정

각 프로젝트 레포에 `DEVELOPMENT_GUIDE.md`를 두면 에이전트가 프로젝트별 규칙을 따름.
`/dev` 실행 시 가이드가 없으면 자동으로 `/init-project` 플로우로 생성.
