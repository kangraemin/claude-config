# Worklog Rules

워크로그 자동 생성 및 관리 규칙.

---

## 1. 생성 주체

| 상황 | 작성자 | 내용 |
|------|--------|------|
| `/commit` 또는 Claude 커밋 | Claude | 요청사항, 작업내용, 변경통계, 토큰 |
| auto-commit (SessionEnd) | pre-commit 훅 | 변경파일, 변경통계만 (fallback) |

## 2. 저장 위치

```
<프로젝트>/.worklogs/
  └── YYYY-MM-DD.md    ← 날짜별 단일 파일, 커밋마다 append
```

## 3. 파일 구조

```markdown
# Worklog: <프로젝트명> — YYYY-MM-DD

---

## HH:MM

### 요청사항
- 사용자가 요청한 내용 정리

### 작업 내용
- 어떤 작업을 했는지 요약
- 주요 변경점

### 변경 통계
\`\`\`
(git diff --cached --stat)
\`\`\`

### 토큰 사용량
- 모델: claude-opus-4-6
- 총 토큰: 1,234,567
- 비용: $1.23

---

## HH:MM (auto)          ← fallback (auto-commit)

### 변경된 파일 (N개)
### 변경 통계
```

## 4. 워크로그 내용

| 섹션 | 내용 | 소스 |
|------|------|------|
| 요청사항 | 사용자가 이 커밋 범위에서 요청한 것 | Claude 대화 컨텍스트 |
| 작업 내용 | 무슨 작업을 했는지 + 주요 변경점 | Claude 분석 + diff |
| 변경 통계 | 파일별 추가/삭제 줄 수 | `git diff --cached --stat` |
| 토큰 사용량 | 모델, 토큰 수, 비용 | `npx ccusage@latest session --json` |

## 5. 토큰 데이터

```bash
npx ccusage@latest session --json
```

- 세션별 토큰 사용량 (input/output/cache/total)
- 비용 (USD)
- 사용 모델
- ccusage 실패 시 "데이터 없음" 표기

## 6. .gitignore 설정

화이트리스트 방식 레포:
```gitignore
!.worklogs/
!.worklogs/**
```

일반 레포: 별도 설정 불필요.

## 7. 제한 사항

- pre-commit hook은 항상 `exit 0` (워크로그 실패가 커밋을 막으면 안 됨)
- Claude가 워크로그를 staged하면 훅은 fallback 생략
- 토큰 데이터는 일일 누적 스냅샷

## 8. 구현 위치

- **hook (fallback)**: `~/.claude/git-hooks/pre-commit`
- **커맨드**: `~/.claude/commands/commit.md`
- **글로벌 적용**: `git config --global core.hooksPath ~/.claude/git-hooks`
