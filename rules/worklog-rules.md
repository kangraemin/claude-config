# Worklog Rules

워크로그 자동 생성 및 관리 규칙.

---

## 1. 생성 시점

- **git pre-commit hook**에서 자동 생성
- 커밋과 같은 트랜잭션에 포함됨 (별도 커밋 없음)
- staged 파일이 `.worklogs/`뿐이면 스킵 (무한루프 방지)

## 2. 저장 위치

```
<프로젝트>/.worklogs/
  └── YYYY-MM-DD/
      └── HH:MM:SS.md
```

- 각 프로젝트 레포 루트의 `.worklogs/` 디렉토리
- 날짜별 하위 디렉토리
- 파일명은 커밋 시각 (초 단위)

## 3. 워크로그 내용

| 섹션 | 내용 | 소스 |
|------|------|------|
| 헤더 | 프로젝트명, 날짜/시각 | `basename $REPO_ROOT`, `date` |
| 변경된 파일 | staged 파일 목록 + 개수 | `git diff --cached --name-only` |
| 변경 통계 | 파일별 추가/삭제 줄 수 | `git diff --cached --stat` |
| Diff | 실제 변경 내용 (200줄 제한) | `git diff --cached` |

- 불필요한 정보 넣지 않음 (세션 전체 통계 등)
- **이 커밋에서 뭘 바꿨는지**에 집중

## 4. .gitignore 설정

워크로그를 git 추적하려면 프로젝트 `.gitignore`에서 제외하지 않아야 함.

화이트리스트 방식 레포의 경우:
```gitignore
!.worklogs/
!.worklogs/**
```

일반 레포의 경우: 별도 설정 불필요 (기본 추적됨).

## 5. 제한 사항

- diff가 200줄 초과 시 잘라내고 전체 줄 수 표기
- pre-commit hook은 항상 `exit 0` (워크로그 실패가 커밋을 막으면 안 됨)

## 6. 구현 위치

- **hook**: `~/.claude/git-hooks/pre-commit`
- **글로벌 적용**: `git config --global core.hooksPath ~/.claude/git-hooks`
