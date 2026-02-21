# Claude Code Global Config

Claude Code 글로벌 설정 — 모든 프로젝트에 공통 적용.

## 설치

```bash
bash <(curl -sL https://raw.githubusercontent.com/kangraemin/claude-config/main/install.sh)
```

- 전역 설치: `~/.claude/`에 클론
- 로컬 설치: 현재 레포 `.claude/`에 agents/commands/rules만 복사

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
├── CLAUDE.md              # 글로벌 규칙 (세션 시작 시 자동 로드)
├── settings.json          # hooks, env, statusLine 설정
├── install.sh             # 원라인 설치 스크립트
│
├── agents/                # 에이전트 역할 정의
│   ├── lead.md            #   리드 — 단계 설계, 태스크 할당, 리뷰
│   ├── dev.md             #   개발 — 구현, 컨벤션 준수
│   ├── qa.md              #   QA — 테스트, 빌드 검증, 통과/반려
│   └── git.md             #   Git — 복잡한 git 워크플로우
│
├── commands/              # 슬래시 커맨드
│   ├── commit.md          #   /commit — 커밋 + 워크로그 + 푸시
│   ├── push.md            #   /push — 안전한 푸시
│   ├── pr.md              #   /pr — PR 생성
│   ├── test.md            #   /test — 프로젝트별 테스트 실행
│   ├── status.md          #   /status — 현재 상태 요약
│   └── worklog.md         #   /worklog — 워크로그 작성
│
├── rules/                 # 규칙 (커맨드/에이전트가 참조)
│   ├── git-rules.md       #   커밋, 푸시, PR, 브랜치 규칙
│   └── worklog-rules.md   #   워크로그 생성/구조/토큰 추적 규칙
│
├── hooks/                 # Claude Code hooks (settings.json에서 등록)
│   ├── worklog.sh         #   PostToolUse — 도구 사용 수집
│   ├── session-end.sh     #   SessionEnd — 수집 데이터 정리
│   ├── auto-commit.sh     #   SessionEnd — 미커밋 변경사항 자동 커밋
│   └── view-worklog.sh    #   워크로그 조회 CLI
│
├── git-hooks/             # Git hooks (core.hooksPath로 글로벌 적용)
│   └── pre-commit         #   워크로그 fallback 생성 + git add
│
└── .worklogs/             # 워크로그 저장소
    ├── YYYY-MM-DD.md      #   날짜별 워크로그 (커밋마다 append)
    └── .snapshot           #   토큰/시간 스냅샷 (git 추적 안 함)
```

## 주요 기능

### 커맨드

| 커맨드 | 설명 |
|--------|------|
| `/commit` | git-rules.md 기반 커밋 → /worklog → 푸시 |
| `/worklog` | 요청사항, 작업내용, 변경통계, 토큰(delta) 기록 |
| `/push` | 안전한 푸시 (force 금지, upstream 확인) |
| `/pr` | 한글 PR 생성 (리뷰 포인트, 변경 요약 포함) |
| `/test` | 프로젝트 타입 자동 감지 후 테스트 실행 |
| `/status` | git + 프로젝트 상태 요약 |

### 에이전트 팀

`lead` → `dev` → `qa` → `lead` 사이클로 작업.

- **lead**: 단계 설계, 태스크 분배, 코드 리뷰, 최종 승인
- **dev**: DEVELOPMENT_GUIDE.md 기반 구현, git-rules.md 준수
- **qa**: 테스트 작성, 빌드 검증, 통과/반려 판정
- **git**: 복잡한 rebase, merge conflict 등 git 전문 작업

에이전트는 글로벌(역할)이고, 프로젝트별 규칙은 각 레포의 `DEVELOPMENT_GUIDE.md`에 정의.

### Hooks

```
[PostToolUse] worklog.sh → .collecting/에 도구 사용 기록
[SessionEnd]  session-end.sh → 수집 데이터 정리
[SessionEnd]  auto-commit.sh → 미커밋 변경사항 자동 커밋 + 푸시
[pre-commit]  git-hooks/pre-commit → 워크로그 fallback + git add
```

### 워크로그 시스템

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

- **Claude 커밋**: `/worklog`이 요청사항 + 작업내용 + ccusage 토큰 delta 기록
- **auto-commit**: pre-commit 훅이 변경통계만 기록 (fallback)
- **토큰 delta**: `.worklogs/.snapshot`에 이전 값 저장 → 차이 계산

### 커밋 규칙 (요약)

- **한글** 커밋 메시지, type만 영어: `feat(검색): 자연어 검색 기능 추가`
- scope 선택, 50자 이내, HEREDOC 사용
- `git add .` 금지, 파일 개별 staging
- 커밋과 푸시는 항상 세트

## 업데이트

```bash
cd ~/.claude && git pull
```

## 프로젝트별 설정

각 프로젝트 레포에 `DEVELOPMENT_GUIDE.md`를 두면 에이전트가 프로젝트별 규칙을 따름.

로컬 설치로 agents/commands/rules만 복사 가능:

```bash
bash install.sh --local
```
