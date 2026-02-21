# /dev

에이전트 팀을 생성하고 개발을 시작한다.

---

## 실행 흐름

### Step 1: 사전 확인

1. 프로젝트 루트에 `DEVELOPMENT_GUIDE.md`가 있는지 확인한다.
   - 없으면: "DEVELOPMENT_GUIDE.md가 없습니다. `/init-project`로 먼저 프로젝트를 셋업하세요." 안내 후 중단.
2. `docs/PHASES.md`가 있는지 확인한다.
   - 있으면: 현재 진행 상태를 파악하고 이어서 진행.
   - 없으면: Step 2로 (Phase 설계부터).

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

## 주의사항

- Phase 계획은 **반드시 사용자 승인** 후 진행한다.
- 한 번에 하나의 Phase만 진행한다.
- Phase 완료 시 사용자에게 보고하고 다음 Phase 진행 여부를 확인한다.
- 커밋은 `~/.claude/rules/git-rules.md` 규칙을 따른다.
