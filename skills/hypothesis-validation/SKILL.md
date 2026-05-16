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

## Step 5: 확장 검증 (Extended Validation)

conclusion.md 작성 후 **반드시** 아래 3가지 추가 검증을 실행한다.
`backtest/extended_validation.py`의 `run_extended_validation()`을 호출하거나,
각 함수를 backtest.py 말미에 직접 삽입한다.

### 5-1. WF Embargo 체크
- IS 끝 ~ OOS 시작 간격이 **21일 미만**이면 `⚠️ WARN` 출력
- WARN이어도 진행 가능하나 결과 신뢰도 낮음으로 표기

### 5-2. Monte Carlo Permutation Test
- OOS 거래의 **진입 날짜를 랜덤화**해서 1000회 반복 → Sharpe 분포 생성
- `p_value < 0.05` → PASS (전략이 운이 아님)
- `p_value >= 0.05` → FAIL (운으로 통과한 것)
- ⚠️ 수익률 셔플 금지 — 진입 날짜 랜덤화만 유효

### 5-3. Out-of-Universe Test
- 훈련에 **사용하지 않은** 유사 종목에 동일 신호 로직 적용 → OOS Sharpe 계산
- 기본 대체 종목: SPY→IVV, QQQ→VGT, IWM→VTWO, GLD→IAU, TLT→IEF
- **평균 OOU Sharpe > 0** → PASS
- **평균 OOU Sharpe ≤ 0** → FAIL (특정 종목 과적합)

### 5-4. 라이브 적용 기준 (AND 조건)
기존 8-check PASS **+** 아래 전부:
- MC `p_value < 0.05`
- OOU avg Sharpe `> 0`
- (Embargo >= 21일 권장)

**어느 하나라도 FAIL이면 라이브 적용 금지.**

---

## Step 6: 검증 결과 로그 저장 (필수)

확장 검증 완료 후 **반드시** 아래 두 곳에 기록한다. 누락 금지.

### 6-1. hypothesis validation_log.md
`hypothesis/<가설이름>/validation_log.md` 저장:

```
# Validation Log — <가설이름>
- 날짜: YYYY-MM-DD HH:MM
- 전략: <전략명>
- 8-Check: N/8 (PASS/FAIL)
- MC p-value: 0.xxx (PASS/FAIL)
- OOU Sharpe: 평균 X.XX (PASS/FAIL)
  - IVV: X.XX, VGT: X.XX, VTWO: X.XX, IAU: X.XX, IEF: X.XX
- Embargo: XX일 (OK/WARN)
- **최종 판정: PASS ✅ / FAIL ❌**
```

`backtest/extended_validation.py`의 `save_validation_log()`를 사용하면 자동 생성된다.

### 6-2. ralph-x log.md append (ralph 루프 실행 중일 때)
`ralph-x-runs/*/log.md`가 존재하면 한 줄 append:
```
| <iter> | <전략명> | <PASS/FAIL> | Sharpe=X.XX | MC_p=X.XX | OOU=X.XX | <비고> |
```
`save_validation_log(ralph_log_path=..., iter_num=...)`에 경로를 넘기면 자동 처리된다.

---

## 금지 행동

- **"백테스트 해볼까요?"** 금지 — 가설 검증 요청 = 즉시 실행
- **IS 결과만으로 "괜찮은데요"** 금지 — OOS + WF 없으면 결론 불가
- **hypothesis.md 없이 backtest 실행** 금지 — 합격기준 먼저, 결과 나중
- **results.csv 없이 conclusion.md 작성** 금지 — hypothesis-gate가 막음
- **Step 5~6 스킵** 금지 — MC + OOU + 로그 저장은 결론 작성과 동급 필수 단계
- **8-check PASS라도 MC/OOU 미통과시 "라이브 가능"** 표현 금지
