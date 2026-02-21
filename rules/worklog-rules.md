# Worklog Rules

워크로그 자동 생성 및 관리 규칙.

---

## 1. 생성 주체

| 상황 | 작성자 | 내용 |
|------|--------|------|
| `/commit` 또는 Claude 커밋 | Claude (`/worklog`) | 요청사항, 작업내용, 변경통계, 토큰(delta), 소요시간 |
| auto-commit (SessionEnd) | pre-commit 훅 | 변경파일, 변경통계만 (fallback) |

## 2. 저장 위치

```
<프로젝트>/.worklogs/
  ├── YYYY-MM-DD.md    ← 날짜별 단일 파일, 커밋마다 append
  └── .snapshot         ← 토큰/시간 스냅샷 (git 추적 안 함)
```

## 3. 파일 구조

```markdown
# Worklog: <프로젝트명> — YYYY-MM-DD

---

## HH:MM

### 요청사항
- 사용자가 요청한 내용

### 작업 내용
- 간결한 작업 요약

### 변경 통계
\`\`\`
(git diff --cached --stat)
\`\`\`

### 토큰 사용량
- 모델: claude-opus-4-6
- 이번 작업: 500,000 토큰 / $0.50
- 소요 시간: 12분
- 일일 누적: 29,760,365 토큰 / $17.87
```

## 4. 토큰/시간 delta 계산

### 스냅샷 파일: `.worklogs/.snapshot`

```json
{
  "timestamp": 1740100000,
  "totalTokens": 29760365,
  "totalCost": 17.87
}
```

### 계산 방법

1. `npx ccusage@latest session --json`으로 현재 토큰 수집
2. `.worklogs/.snapshot` 읽기
3. **토큰 delta** = 현재 - 스냅샷
4. **비용 delta** = 현재 - 스냅샷
5. **소요 시간** = 현재 timestamp - 스냅샷 timestamp
6. 워크로그 작성 후 스냅샷 갱신

스냅샷이 없으면 (첫 실행) delta 대신 전체값 표시.

## 5. .gitignore 설정

화이트리스트 방식 레포:
```gitignore
!.worklogs/
!.worklogs/**
```

`.worklogs/.snapshot`은 git 추적하지 않음:
```gitignore
.worklogs/.snapshot
```

## 6. 제한 사항

- pre-commit hook은 항상 `exit 0` (워크로그 실패가 커밋을 막으면 안 됨)
- Claude가 워크로그를 staged하면 훅은 fallback 생략
- ccusage 실패 시 "데이터 없음" 표기

## 7. 구현 위치

- **커맨드**: `~/.claude/commands/worklog.md`
- **hook (fallback)**: `~/.claude/git-hooks/pre-commit`
- **글로벌 적용**: `git config --global core.hooksPath ~/.claude/git-hooks`
