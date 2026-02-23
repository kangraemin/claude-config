# Worklog Rules

## 생성 주체

| 상황 | 작성자 | 내용 |
|------|--------|------|
| `/commit` 또는 Claude 커밋 | `/worklog` | 요청사항, 작업내용, 변경파일, 토큰(delta) |
| auto-commit (SessionEnd) | pre-commit 훅 | 변경파일 목록 (fallback) |

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
