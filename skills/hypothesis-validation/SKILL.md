---
name: hypothesis-validation
description: |
  투자 가설 검증 커맨드. '가설 검증해봐', '이거 효과있을까', '테스트해봐', '백테스트 돌려봐',
  '/가설검증' 등으로 호출. 가설 제안 시 백테스트 없이 결론 내리는 패턴을 막기 위해
  hypothesis.md → backtest → results.csv → conclusion.md 순서를 강제한다.
  "백테스트 해볼까요?" 라고 묻지 말고 이 스킬을 즉시 실행할 것.
  stock-bot, coinbot 등 퀀트/투자 전략 프로젝트 전체에 적용.
---

# /가설검증

가설 검증은 4단계 파이프라인을 순서대로 실행한다. **단계 스킵 금지.**

---

## Step 1: hypothesis.md 작성 (백테스트 전 필수)

`hypothesis/<가설이름>/hypothesis.md` 생성. 프로젝트 루트 기준.
템플릿: `hypothesis/_template/hypothesis.md` 참고.

**합격 기준은 반드시 백테스트 전에 작성한다.**
결과를 보고 나서 기준을 조정하는 건 p-hacking이다.

---

## Step 2: backtest.py 작성 + 실행

`hypothesis/<가설이름>/backtest.py` 작성.
템플릿: `hypothesis/_template/backtest_template.py` 기반으로 작성.

**표준 백테스트 필수 포함 — 하나라도 빠지면 결론 불가:**

| 항목 | 내용 |
|------|------|
| IS/OOS 분리 | 전체 기간 앞 70% IS / 뒤 30% OOS |
| Walk-Forward | 최소 5 윈도우, expanding window |
| N/T ratio | 파라미터 수 / 총 거래 수 (과적합 지표) |
| Sharpe t-stat | p-value 포함 |
| vs B&H | 동일 종목 동일 기간 B&H 비교 |
| vs 현재 전략 | 프로젝트 기존 전략 대비 (stock-bot: alert.py, coinbot: 현재 전략) |
| 수수료 | 실제 비용 반영 (슬리피지 포함) |

---

## Step 3: results.csv 생성

`hypothesis/<가설이름>/results.csv` 저장.

**필수 컬럼 (hypothesis-gate가 없으면 conclusion.md BLOCK):**
```
symbol, period, trades, trades_per_yr,
sharpe_is, sharpe_oos, wf_win_rate, n_t_ratio,
cagr_is, cagr_oos, mdd_is, mdd_oos,
vs_bh, vs_alert
```

---

## Step 3.5: 검증 게이트 (자동, 스킵 금지)

results.csv 생성 후 **반드시** `validate_backtest.py`를 실행한다.

```bash
python3 hypothesis/_template/validate_backtest.py hypothesis/<가설이름>/results.csv
```

**검증 기준 (하드코딩, Claude 판단 개입 불가):**

| 기준 | 임계값 | 설명 |
|------|--------|------|
| OOS 폴드 수 | >= 3 | NaN 아닌 유효 폴드 |
| OOS Sharpe 최솟값 | > 0.0 | 모든 폴드에서 양수 |
| vs B&H 최악 폴드 | >= -50% | B&H 대비 과도한 언더퍼폼 금지 |
| OOS MDD 최대 | <= 40% | 최대 낙폭 제한 |
| 연간 거래 수 | >= 5 | 통계 유의성 확보 |
| 수수료 | <= 25% | 현실적 비용 |

**규칙:**
- exit code 0 = PASS → conclusion.md에 "검증됨" 기록 가능
- exit code 1 = FAIL → conclusion.md에 **"미검증 가설"** 강제 기록
- FAIL인데 "괜찮은데", "유망한데" 같은 긍정 표현 금지
- 검증 게이트 출력을 conclusion.md에 그대로 복사 (수정 금지)

---

## Step 4: conclusion.md 작성

`hypothesis/<가설이름>/conclusion.md` 작성.
results.csv + hypothesis.md 없으면 hypothesis-gate가 BLOCK한다.

**필수 포함:**

### 결과 테이블
| 종목 | 거래/년 | Sharpe IS | Sharpe OOS | WF승률 | N/T | vs B&H | vs 현재전략 |
|------|--------|-----------|------------|--------|-----|--------|------------|

### 합격기준 대비 판정
hypothesis.md에 사전 정의한 기준과 대조:
```
OOS Sharpe:  X.XX → 기준 Y.YY → ✅/❌
거래/년:     X.X  → 기준 Y    → ✅/❌
WF 승률:     XX%  → 기준 60%  → ✅/❌
N/T ratio:  X.X  → 0.5 이하  → ✅/❌
vs B&H:     X%   → 기준 Y%   → ✅/❌
vs 현재전략: X%   → 기준 Y%   → ✅/❌
```

### 검증 게이트 결과
validate_backtest.py 출력을 **그대로** 붙여넣기 (편집 금지).

### 최종 판정
- 검증 게이트 PASS + 합격기준 전 항목 ✅ → `PASS`
- 그 외 → `FAIL`
- **FAIL인 가설에 "유망", "방향은 맞다", "개선하면 될 듯" 같은 표현 금지. FAIL은 FAIL.**

### 다음 액션
채택 / 파라미터 조정 후 재검증 / 폐기

---

## 금지 행동

- **"백테스트 해볼까요?"** 금지 — 가설 검증 요청 = 즉시 실행
- **IS 결과만으로 "괜찮은데요"** 금지 — OOS + WF 없으면 결론 불가
- **hypothesis.md 없이 backtest 실행** 금지 — 합격기준 먼저, 결과 나중
- **results.csv 없이 conclusion.md 작성** 금지 — hypothesis-gate가 막음
