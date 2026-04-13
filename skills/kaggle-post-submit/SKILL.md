---
name: kaggle-post-submit
description: Kaggle 제출 후 결과 확인 + 문서 자동 정리 + 다음 전략 제안 스킬. '제출했다', '제출 완료', '결과 확인해', 'reflection 써줘', '정리해줘', 'submit 했어', '점수 나왔어', 'score 확인', '다음 전략 뭐야', '뭐 시도해볼까', 'trial 만들어줘', 'sub 만들어줘', '다음 trial', 'best trial 골라줘' 등 Kaggle 제출/trial 관련 요청 시 반드시 이 스킬을 사용할 것.
---

# Kaggle Post-Submit

Kaggle 제출 후 결과 확인 → 문서 정리 → 커밋 + 다음 전략 제안까지.

---

## 핵심 규칙

1. **제출 1회 = sub 1개. 예외 없음.** 이전 sub 폴더를 덮어쓰거나 수정하지 않는다.
2. **trial 번호는 순번 증가.** `19b`, `20a` 같은 suffix 절대 금지. 이전이 19면 다음은 20.
3. **이전 reflection/meta.json은 수정 금지.** 새로 만든다.
4. **점수 나오기 전에 추측하지 않는다.** polling으로 확인 후 작성.

---

## 실행 전 필수 — 현황 파악

**가장 먼저** 아래 파일들을 읽는다. 읽지 않고 진행 금지.

1. **`TRIALS.md`** — 완료된 trials, val scores, key changes
2. **`SUBMISSIONS.md`** — 제출 이력, public scores
3. 최근 submission의 **`reflection.md`** — 버려야 할 것, 유지할 것, 다음 가설

읽은 후 확인:
- 현재 마지막 sub 번호 (N)
- 현재 마지막 trial 번호 (T) — suffix 포함된 것도 있으면 가장 높은 정수 추출
- 대회 slug (`SUBMISSIONS.md` 첫 줄 `# Submissions — {slug}`)

---

## 모드 1: 제출 후 정리 (Post-Submit)

**언제**: "제출했다", "결과 확인해", "정리해줘"

### Step 1: 결과 polling

```bash
kaggle competitions submissions <slug> | head -4
```

PENDING이면 2분마다 백그라운드 polling. 사용자가 점수를 이미 알려줬으면 생략.

### Step 2: 새 sub 폴더 + trial 폴더 생성

```
submissions/sub_{N+1}/trial_{T+1}_{name}/meta.json
submissions/sub_{N+1}/reflection.md
```

meta.json이 이미 있으면 건드리지 않는다.

### Step 3: TRIALS.md 업데이트

```
| {T+1} | {name} | **{N+1:02d}** | {val_score} | {public_score} | {key_changes} | {status} |
```

### Step 4: SUBMISSIONS.md 업데이트

```
| {N+1:02d} | {date} | trial_{T+1} | {base} | {public_score} | {status} |
```

### Step 5: reflection.md 작성

```markdown
## Submission {N+1:02d} Reflection

**Base**: {base 설명}
**Trial**: trial_{T+1}

### 결과
- Public: {점수 또는 에러 상태}

### 변경사항 (이전 sub 대비)
- {변경 1}

### 교훈
- {이번 시도에서 배운 것}

### 버려야 할 것
- {효과 없었거나 문제 있었던 것}

### 유지해야 할 것
- {효과 있었거나 계속 써야 할 것}

### 다음 가설
- {다음에 시도할 방향}
```

대화 컨텍스트에서 실패 원인, 디버깅 과정, 배운 점을 추출해서 구체적으로 작성. 빈 칸 금지.

### Step 6: 커밋 + 푸시

프로젝트 git-rules를 따른다.

### Step 7: 완료 보고

```
✅ sub_{N+1} 정리 완료
- Public: {점수}
- Trial: {trial 번호} {이름}
- Reflection: submissions/sub_{N+1}/reflection.md
```

---

## 모드 2: 다음 전략 제안

**언제**: "다음 뭐 해볼까", "전략 제안해줘", "다음 trial"

### 분석 방식

1. **효과 있었던 것** — val/public score 올린 변경
2. **효과 없었던 것** — reflection에서 "버려야 할 것"
3. **아직 안 해본 것** — 체크리스트 기준

### 제안 형식

```
현재 상황:
- best: X.XXXX (trial_NNN)
- 효과 있었던 것: [목록]
- 효과 없었던 것: [목록]

다음 시도 추천 (우선순위 순):
1. trial_{T+1}_{name}: [가설] — 근거: [왜 이게 다음이어야 하는지]
2. trial_{T+2}_{name}: [가설] — 근거: ...
3. trial_{T+3}_{name}: [가설] — 근거: ...
```

---

## 모드 3: 새 Trial 준비

**언제**: 전략 결정 후 "trial 만들어줘", "sub 준비하자"

`submissions/sub_{N+1}/trial_{T+1}_{name}/meta.json` 생성:

```json
{
  "id": "{T+1}",
  "name": "{name}",
  "base_trial": "{base}",
  "created_at": "YYYY-MM-DD",
  "hypothesis": "구체적 가설 한 문장",
  "changes": ["변경사항 1", "변경사항 2"],
  "rationale": "이전 trial 결과 기반 근거",
  "expected_impact": "low/medium/high"
}
```

---

## 점수 없이 실패한 경우

Notebook Timeout, Exception, OOM 등도 동일하게 처리. 점수가 없다고 기록을 안 남기면 같은 실수를 반복한다.

---

## 대회 자동 감지

`<competition_root>`는 현재 작업 디렉토리에서 `SUBMISSIONS.md`가 있는 가장 가까운 상위 폴더. 대회 slug는 `# Submissions — {slug}`에서 추출.
