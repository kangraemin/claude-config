---
name: kaggle-init
description: Kaggle 대회 디렉토리 초기 세팅 스킬. 새 대회 폴더에 SUBMISSIONS.md, TRIALS.md, submissions/ 폴더, .gitignore를 자동 생성한다. '새 대회 세팅해줘', 'kaggle init', '폴더 구조 만들어줘', 'kaggle-init', '대회 디렉토리 초기화', '대회 시작할 건데 구조 잡아줘' 같은 요청 시 반드시 이 스킬을 사용할 것.
---

# Kaggle Init

새 Kaggle 대회 디렉토리를 TRIAL_GUIDE.md 기반 구조로 세팅한다.

## 수집해야 할 정보

스킬 실행 전 다음 정보를 파악한다. 대화 컨텍스트에 이미 있으면 그걸 쓰고, 없으면 한 번에 물어본다:

1. **competition_dir**: 세팅할 디렉토리 경로 (현재 작업 디렉토리 기준)
2. **competition_name**: 대회 이름 (예: `playground-series-s6e3`)
3. **task_type**: 분류(classification) / 회귀(regression) / 기타
4. **metric**: 평가 지표 (예: AUC-ROC, RMSE, MAE)

---

## 생성할 파일 목록

```
<competition_dir>/
  SUBMISSIONS.md
  TRIALS.md
  submissions/
    .gitkeep
  .gitignore
```

---

## 각 파일 내용

### SUBMISSIONS.md

```markdown
# Submissions — <competition_name>

| # | Date | Best Trial | Val | Public | Private | Gap | Status |
|---|------|------------|-----|--------|---------|-----|--------|

**Gap** = Public - Val. 양수면 val이 보수적, 음수면 overfitting 의심.
```

### TRIALS.md

```markdown
# Trials — <competition_name>

| # | Name | Val Score | Public Score | Key Changes | Status |
|---|------|-----------|--------------|-------------|--------|

## 메트릭
- Task: <task_type>
- Metric: <metric>
- Direction: <higher_is_better or lower_is_better>
```

### .gitignore

```gitignore
# 데이터
*.csv
*.parquet
*.feather
*.zip

# 모델
*.pkl
*.joblib
*.h5
*.pt
*.pth

# 로그
*.log

# 예외: 제출 파일이 아닌 스크립트는 추적
!submissions/**/*.py
!submissions/**/*.json
!submissions/**/*.md
```

### submissions/.gitkeep

빈 파일.

---

## 실행 순서

1. 정보 파악 (위 4가지)
2. `competition_dir` 존재 확인. 없으면 생성.
3. 파일 4개 생성 (이미 있는 파일은 덮어쓰기 전 확인)
4. 생성 완료 후 트리 출력으로 구조 확인
5. 완료 메시지: 어떤 파일이 생성됐는지 한 줄씩

## 완료 후 안내

세팅 완료 후 다음을 짧게 안내한다:
- 베이스라인 trial 바로 시작할 수 있다
- trial은 `submissions/sub_01/trial_001_<name>/` 형식으로 생성
- 자세한 규칙은 `TRIAL_GUIDE.md` 참조
