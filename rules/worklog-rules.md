# Worklog Rules

## 생성 시점 (`WORKLOG_TIMING`)

| 값 | 동작 |
|---|---|
| `each-commit` | `/commit` 실행 시마다 자동 작성 (기본) |
| `session-end` | 세션 종료 전 오늘 워크로그 없으면 Stop 훅이 요청 |
| `manual` | `/worklog` 직접 실행할 때만 작성 |

## 저장 대상 (`WORKLOG_DEST`)

| 값 | 동작 |
|---|---|
| `git` | `.worklogs/YYYY-MM-DD.md`에 저장 (기본) |
| `notion` | 로컬 저장 + Notion DB에 엔트리 생성 |

- `NOTION_TOKEN`: 글로벌 `~/.claude/.env`에 설정 (워크스페이스 공통)
- `NOTION_DB_ID`: 프로젝트별 `.claude/settings.json` env에 설정 (프로젝트마다 다른 DB)
- `NOTION_DB_ID` 없으면 `notion-create-db.sh`로 자동 생성 후 settings.json에 저장
- DB 네이밍: `{프로젝트명}) worklog` (예: `.claude) worklog`, `my-app) worklog`)
- `notion-worklog.sh`가 `~/.claude/.env`를 자동 source하므로 별도 export 불필요
- Notion 전송 실패 시 로컬 저장은 유지, 에러 메시지 출력

## Git 추적 (`WORKLOG_GIT_TRACK`)

| 값 | 동작 |
|---|---|
| `true` | `.worklogs/`를 git add (기본) |
| `false` | `.worklogs/`를 git add하지 않음 |

## 조합 매트릭스

| DEST | GIT_TRACK | 동작 |
|------|-----------|------|
| `git` | `true` | 기본값: 로컬 저장 + git add |
| `git` | `false` | 로컬 저장, git add 스킵 |
| `notion` | `true` | 로컬 + Notion + git add |
| `notion` | `false` | 로컬 + Notion, git add 스킵 |

## 모드 체크

- `WORKLOG_TIMING=manual`이면 `/worklog` 스킬 시작 시 "워크로그 비활성화 상태" 출력 후 종료

## 저장 위치

- `<프로젝트>/.worklogs/YYYY-MM-DD.md` — 날짜별 단일 파일, append
- `<프로젝트>/.worklogs/.snapshot` — 토큰/시간 스냅샷 (git 추적 안 함)

## 엔트리 포맷

```markdown
## HH:MM

### 요청사항
- 사용자 요청

### 작업 내용
- 작업 요약 (3줄 이내)

### 변경 파일
- `파일명`: 한 줄 설명

### 토큰 사용량
- 모델: claude-opus-4-6
- 이번 작업: N 토큰 / $N
- 소요 시간: N분
- 일일 누적: N 토큰 / $N
```

auto-commit fallback: `## HH:MM (auto)` + 변경 파일 목록만.

## 토큰 delta 계산

스냅샷: `{"timestamp":UNIX,"totalTokens":N,"totalCost":N}`

1. `date +%s` → 현재 timestamp
2. `ccusage session --json` (없으면 `npx ccusage@latest session --json`)
3. `.worklogs/.snapshot` 읽기
4. 토큰/비용 delta = 현재값 - 스냅샷값
5. **소요 시간** = `python3 ~/.claude/scripts/duration.py <스냅샷_timestamp> <프로젝트_cwd>`
   - 출력: `초,분` → 분 값 사용. 실제 Claude 작업 시간 (벽시계 시간 아님)
6. 워크로그 작성 후 스냅샷 갱신

- 스냅샷 없으면 전체값 표시 후 생성
- JSONL 읽기 실패 시 "측정 불가"
- ccusage 실패 시 "데이터 없음"

## 제한

- pre-commit hook은 항상 `exit 0` (워크로그 실패 → 커밋 차단 금지)
- Claude가 워크로그 staged하면 훅 fallback 생략
