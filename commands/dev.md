---
description: 에이전트 팀으로 개발 시작
---

# /dev

에이전트 팀을 생성하고 개발을 시작한다.

---

## 사전 확인

피처 모드일 때 `$ARGUMENTS`가 비어있거나 작업 내용이 불충분하면, **반드시 사용자에게 무엇을 구현할지 되물어본다.** 충분한 정보를 얻은 후 진행한다.

## 모드 판별

프로젝트 루트에 `DEVELOPMENT_GUIDE.md`가 있는지 확인한다.

- **없음** → **신규 모드**: 프로젝트 초기 설정부터 시작
- **있음** → **피처 모드**: 사용자 지시를 피처 태스크로 바로 진행

---

## 신규 모드 (DEVELOPMENT_GUIDE.md 없음)

### Step 1: 프로젝트 초기화

`/init-project` 플로우를 먼저 실행한다 (대화하며 가이드 생성). 완료 후 Step 2로 진행.

### Step 2: 팀 생성

TeamCreate로 팀을 생성한다.

```
team_name: "<프로젝트명>-dev"
```

### Step 3: Lead 스폰

Lead 에이전트를 스폰한다 (`~/.claude/agents/lead.md`).

Lead에게 전달할 지시:
- `DEVELOPMENT_GUIDE.md`와 참조 문서들을 읽어라.
- `docs/PHASES.md`가 없으면: 전체 Phase 계획을 설계하고, 사용자에게 승인을 요청하라.
- `docs/PHASES.md`가 있으면: 현재 Phase에서 미완료 Step을 확인하고 이어서 진행하라.
- 사용자 승인 후 현재 Phase의 Step을 TaskCreate로 생성하라.

### Step 4: Dev / QA 스폰

Lead가 태스크를 생성하면 Dev, QA 에이전트를 스폰한다.

- **Dev** (`~/.claude/agents/dev.md`): 구현 담당
- **QA** (`~/.claude/agents/qa.md`): 테스트/검증 담당

### Step 5: 개발 루프

```
Lead: Phase 설계 → 사용자 승인 → 태스크 생성/배정
  ↓
Dev: 태스크 구현 → 완료 보고
  ↓
QA: 테스트/빌드 검증 → 통과/반려
  ↓
Lead: Step 완료 확인 → PHASES.md 업데이트
  ↓
(다음 Step 또는 다음 Phase)
```

---

## 피처 모드 (DEVELOPMENT_GUIDE.md 있음)

### Step 1: 팀 생성

TeamCreate로 팀을 생성한다.

```
team_name: "<프로젝트명>-dev"
```

### Step 2: Lead 스폰

Lead 에이전트를 스폰한다 (`~/.claude/agents/lead.md`).

Lead에게 전달할 지시:
- `DEVELOPMENT_GUIDE.md`와 참조 문서들을 읽어라.
- **피처 모드**로 동작하라.
- 사용자의 요청 내용: `$ARGUMENTS`
- 기존 코드베이스를 분석하고, 요청을 Step 단위 태스크로 분해하라.
- 사용자에게 구현 계획을 승인받은 후 TaskCreate로 생성하라.

### Step 3: Dev / QA 스폰

Lead가 태스크를 생성하면 Dev, QA 에이전트를 스폰한다.

- **Dev** (`~/.claude/agents/dev.md`): 구현 담당
- **QA** (`~/.claude/agents/qa.md`): 테스트/검증 담당

### Step 4: 개발 루프

```
Lead: 피처 분석 → 구현 계획 → 사용자 승인 → 태스크 생성/배정
  ↓
Dev: 태스크 구현 → 완료 보고
  ↓
QA: 테스트/빌드 검증 → 통과/반려
  ↓
Lead: Step 완료 확인 → 다음 태스크 진행
```

---

## 주의사항

- 구현 계획은 **반드시 사용자 승인** 후 진행한다.
- 신규 모드: 한 번에 하나의 Phase만 진행. Phase 완료 시 다음 Phase 진행 여부 확인.
- 피처 모드: PHASES.md 생성/수정하지 않음. 피처 완료 시 사용자에게 보고.
- 커밋은 `~/.claude/rules/git-rules.md` 규칙을 따른다.
