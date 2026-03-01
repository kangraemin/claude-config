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
| `git` | `.worklogs/YYYY-MM-DD.md`에 저장, WORKLOG_GIT_TRACK에 따라 git 추적 |
| `notion` | 로컬 저장 + Notion DB에 엔트리 생성 (`both`와 동일, 하위 호환) |
| `notion-only` | Notion에만 기록, 로컬 파일 없음 |

### 통합 모드 (WORKLOG_DEST + WORKLOG_GIT_TRACK 조합)

| 모드 | WORKLOG_DEST | WORKLOG_GIT_TRACK | 설명 |
|------|-------------|-------------------|------|
| `notion-only` | `notion-only` | `false` | Notion에만 기록 (로컬 파일 없음) |
| `git` | `git` | `true` | 파일만, git 추적 |
| `git-ignore` | `git` | `false` | 파일만, git 미추적 |
| `both` | `notion` | `true` | 파일 + Notion (기본) |

- `NOTION_TOKEN`: 글로벌 `~/.claude/.env`에 설정 (워크스페이스 공통)
- `NOTION_DB_ID`: 글로벌 `~/.claude/settings.json` env에 설정 (전체 프로젝트 공용 DB 하나)
- `notion-worklog.sh`가 `~/.claude/.env`를 자동 source하므로 별도 export 불필요
- Notion 전송 실패 시 로컬 저장은 유지, 에러 메시지 출력
- **`notion-only` 모드**: 로컬 파일 write 스킵. 스냅샷(`.worklogs/.snapshot`)은 유지.
- Content 본문은 마크다운 → Notion 블록 자동 변환 (`###` → heading_3, `- ` → bulleted_list_item)
- Notion 페이지 아이콘: 📚 (notion-worklog.sh에서 자동 설정)
- **Notion DB 컬럼**: Title, Date, Project, Tokens, Cost, Duration, Model, Daily Tokens, Daily Cost
- **Notion 엔트리 포맷**:
  - Title: 작업 내용 한 줄 요약 (시간 포함 X)
  - Content (페이지 본문): 워크로그 상세 (요청사항, 작업내용, 변경파일, 토큰) — git 워크로그와 동일 수준
  - Cost / Daily Cost: 소숫점 그대로 전달 (반올림 금지)
  - Model: 사용 모델 (예: claude-opus-4-6)
  - Daily Tokens / Daily Cost: 일일 누적 토큰/비용

## Git 추적 (`WORKLOG_GIT_TRACK`)

| 값 | 동작 |
|---|---|
| `true` | `.worklogs/`를 git add (기본) |
| `false` | `.worklogs/`를 git add하지 않음 |

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
