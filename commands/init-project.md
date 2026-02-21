# /init-project

새 프로젝트의 개발 가이드를 대화를 통해 생성한다.

---

## 실행 흐름

### Step 1: 프로젝트 정보 수집

사용자와 대화하며 다음 정보를 파악한다:

- **앱 이름** (예: Stash)
- **플랫폼** (iOS / Android / Web / 기타)
- **주요 기술 스택** (아키텍처, UI 프레임워크, DB, 테스트 등)
- **번들 ID / 패키지명** (예: com.kangraemin.stash)
- **GitHub 레포** (있으면)
- **최소 타겟 버전**
- **코딩 스타일 가이드** (있으면)
- **기타 특이사항**

모든 항목을 한 번에 묻지 말고, 플랫폼 선택 → 스택 논의 → 세부 설정 순서로 자연스럽게 대화한다.

### Step 2: docs/ 상세 가이드 생성

수집한 정보를 바탕으로 프로젝트 루트에 `docs/` 디렉토리를 만들고, 플랫폼과 스택에 맞는 상세 가이드를 생성한다.

**일반적으로 포함되는 문서:**

| 문서 | 내용 |
|------|------|
| `docs/ARCHITECTURE.md` | 아키텍처 패턴, DI, 프로젝트 폴더 구조 |
| `docs/CODING_CONVENTIONS.md` | 네이밍, 스타일, 주석 규칙 |
| `docs/TESTING.md` | 테스트 프레임워크, Mock, 빌드 검증 명령 |

**플랫폼별 추가 문서 예시:**

- iOS: `docs/SWIFTUI_GUIDE.md` (SwiftUI 컨벤션, View 패턴)
- Android: `docs/COMPOSE_GUIDE.md` (Compose 컨벤션)
- Web: `docs/COMPONENT_GUIDE.md` (컴포넌트 패턴)

문서 구성은 고정이 아니라 스택에 따라 유연하게 결정한다. 사용자와 논의하며 필요한 문서를 정한다.

### Step 3: DEVELOPMENT_GUIDE.md 허브 생성

프로젝트 루트에 `DEVELOPMENT_GUIDE.md`를 생성한다. 이 파일은 **허브 역할만** 한다.

```markdown
# {앱 이름} - Development Guide

프로젝트 전체 규칙의 허브. 모든 에이전트(`~/.claude/agents/`)가 이 문서를 먼저 읽는다.

---

## 1. 프로젝트 개요

| 항목 | 선택 |
|------|------|
| 앱 이름 | **{앱 이름}** |
| ... | ... |

---

## 2. 상세 가이드

| 문서 | 내용 |
|------|------|
| [Architecture](docs/ARCHITECTURE.md) | ... |
| [Coding Conventions](docs/CODING_CONVENTIONS.md) | ... |
| [Testing](docs/TESTING.md) | ... |
| [단계별 개발 원칙](~/.claude/guides/common/phase-development.md) | Phase/Step 구조, 완료 조건 (글로벌) |
| [팀 워크플로우](~/.claude/guides/common/team-workflow.md) | Lead/Dev/QA 역할 (글로벌) |
| [Git Rules](~/.claude/rules/git-rules.md) | 커밋, 푸시, PR 규칙 (글로벌) |

---

## 3. Git 컨벤션

`~/.claude/rules/git-rules.md` 참조. 추가로 이 프로젝트에서는:

- `develop` 브랜치를 개발 통합 브랜치로 사용
- `feature/<단계명>` 브랜치로 각 Step 작업
- 단계 완료 시 `develop`에 머지 후 태그: `phase-X.step-Y`
```

### Step 4: 확인

생성 완료 후 전체 구조를 사용자에게 보여주고, 수정할 부분이 있는지 확인한다.

---

## 주의사항

- 공통 규칙(단계별 개발 원칙, 팀 워크플로우)은 `~/.claude/guides/common/`에 이미 있다. 프로젝트에 복사하지 않고 **참조만** 한다.
- Git 규칙은 `~/.claude/rules/git-rules.md`에 이미 있다. 프로젝트에 복사하지 않는다.
- `docs/`의 내용은 해당 프로젝트의 스택에 맞게 작성한다. 다른 프로젝트의 가이드를 그대로 복사하지 않는다.
- DEVELOPMENT_GUIDE.md는 허브 역할만 한다. 상세 규칙은 반드시 별도 문서로 분리한다.
