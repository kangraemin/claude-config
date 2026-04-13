# /analyze — 백테스트 분석 파이프라인

백테스트 분석을 실행하고 결과를 `analysis/` 폴더에 자동 저장하는 스킬.

## 트리거

`/analyze` 또는 사용자가 분석/백테스트/가설검증을 요청할 때.

## 서브커맨드

### 1. `/analyze grid <옵션>`
그리드 서치 실행 + 결과 저장.

옵션:
- `--symbols`: 심볼 (기본: SYMBOLS_BASE + SYMBOLS_3X 전체)
- `--timeframe`: daily, weekly, hourly (기본: daily)
- `--periods`: 1y,3y,5y 등 (기본: 1y,3y,5y)
- `--top-n`: 상위 N개 (기본: 5)
- `--n-jobs`: 병렬 코어 수 (기본: 8)

실행 절차:
1. 데이터 로드 (`load_multi`, hourly면 `interval="1h"`)
2. `run_full_grid_search()` 실행 (progress=True)
3. 결과를 `analysis/backtest/YYYY-MM-DD-grid-<timeframe>.md`에 저장
4. 심볼별 top 파라미터, Sharpe, 수익률, 거래횟수 테이블 포함

```python
from backtest.data_loader import load_multi
from backtest.grid_search import run_full_grid_search
from config import SYMBOLS_BASE, SYMBOLS_3X, FeeModel

symbols = SYMBOLS_BASE + SYMBOLS_3X
data = load_multi(symbols)
hourly_data = load_multi(symbols, interval="1h") if timeframe == "hourly" else None

results = run_full_grid_search(
    data=data,
    top_n=top_n,
    periods=periods,
    timeframes=[timeframe],
    fee_rates=[float(FeeModel.STANDARD), float(FeeModel.EVENT)],
    n_jobs=n_jobs,
    progress=True,
    hourly_data=hourly_data,
)
```

### 2. `/analyze compare <A> <B>`
두 타임프레임/기간 비교 분석.

예: `/analyze compare daily hourly`

절차:
1. 두 결과셋 로드 (캐시 또는 재실행)
2. 심볼별 Sharpe/수익률/거래횟수 비교 테이블 생성
3. `analysis/backtest/YYYY-MM-DD-compare-<A>-vs-<B>.md`에 저장

### 3. `/analyze overlap`
포지션 오버랩 분석.

절차:
1. 그리드서치 best 파라미터로 각 심볼 백테스트 실행
2. 심볼별 거래 구간 추출 (진입~청산 시점)
3. 시간축 오버랩 매트릭스 생성
4. `analysis/insight/YYYY-MM-DD-overlap.md`에 저장

### 4. `/analyze signal <symbol>`
특정 심볼의 시그널 상세 분석.

절차:
1. best 파라미터로 백테스트 실행
2. 개별 거래 목록 (진입/청산 날짜, 수익률, 보유기간)
3. 승률, 평균 수익, 최대 손실 등 통계
4. `analysis/backtest/YYYY-MM-DD-signal-<symbol>.md`에 저장

### 5. `/analyze hypothesis "<가설>"`
가설 검증 파이프라인.

예: `/analyze hypothesis "시간봉 RSI 14가 21보다 유리하다"`

절차:
1. 가설 파싱 → 필요한 파라미터 변형 결정
2. A/B 그리드서치 실행 (변경 파라미터만 다르게)
3. 결과 비교 + 통계적 유의성 (t-test 등)
4. `analysis/hypothesis/YYYY-MM-DD-<slug>.md`에 저장
5. 결론: 지지/기각/불충분

### 6. `/save [제목]`
현재 대화 중 분석 결과를 파일로 저장 (실행 없이 메모만).

절차:
1. 제목 결정 (사용자 지정 또는 자동 추출)
2. 카테고리 자동 분류: `backtest/`, `hypothesis/`, `insight/`
3. `analysis/<category>/YYYY-MM-DD-<slug>.md`에 저장
4. INDEX.md 업데이트

---

## 파일 저장 공통 규칙

### 디렉토리 구조
```
analysis/
  INDEX.md              # 전체 분석 목록
  backtest/             # 그리드서치, 시그널 분석
  hypothesis/           # 가설 검증
  insight/              # 메모, 관찰, 인사이트
```

### 파일 포맷
```markdown
# <제목>

- **날짜**: YYYY-MM-DD HH:MM
- **카테고리**: <category>
- **커맨드**: <실행한 서브커맨드>
- **심볼**: <관련 심볼>
- **타임프레임**: <timeframe>
- **소요시간**: <실행 시간>

## 요약

<핵심 결과 2-3줄>

## 데이터

<테이블, 수치>

## 결론

<takeaway, 다음 액션>
```

### INDEX.md 포맷
```markdown
# Analysis Index

| 날짜 | 카테고리 | 제목 | 파일 | 핵심 결과 |
|------|---------|------|------|----------|
```

### 규칙
- `analysis/` 없으면 자동 생성
- 기존 파일 덮어쓰기 금지 — 같은 slug면 `-2`, `-3` 붙임
- git add/commit 하지 않음
- 그리드서치 캐시 (`backtest/.grid_cache/`) 활용 — 이미 돌린 건 재실행 안 함
- 긴 실행은 `run_in_background`로 돌리고 완료 시 알림
