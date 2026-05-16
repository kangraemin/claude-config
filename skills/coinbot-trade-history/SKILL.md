---
name: coinbot-trade-history
description: Coinbot 라이브 거래 현황 조회 — 사용자가 "신규 전략 PnL", "최근 거래", "얼마 잃었어/벌었어", "신규 전략 이후", "거래 결과", "봇 성과" 등 라이브 트레이딩 현황을 물으면 반드시 이 스킬을 사용한다. 서버 DB에서 직접 조회하여 KST 기준 / 계정별 분리 형태로 보고한다.
---

# Coinbot 거래 현황 조회

## 데이터 소스

- **서버**: `ssh ubuntu@158.179.166.232`
- **DB**: `/home/ubuntu/coinbot/data/trades.db`
- **config**: `/home/ubuntu/coinbot/config.py` — `NEW_STRATEGY_DATE` 읽기
- 로컬 DB는 비어있으므로 반드시 서버에서 조회한다.

## 실행 절차

### 1. NEW_STRATEGY_DATE 읽기

```bash
cat << 'PYEOF' | ssh ubuntu@158.179.166.232 'python3 -'
import re, pathlib
cfg = pathlib.Path('/home/ubuntu/coinbot/config.py').read_text()
m = re.search(r'NEW_STRATEGY_DATE.*?=.*?"([^"]+)"', cfg)
print(m.group(1) if m else "NOT_FOUND")
PYEOF
```

### 2. 거래 조회 + KST 변환 + 계정 분리

```bash
cat << 'PYEOF' | ssh ubuntu@158.179.166.232 'python3 -'
import sqlite3
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
CUTOFF = "<NEW_STRATEGY_DATE 값>"  # 위에서 읽은 값

conn = sqlite3.connect('/home/ubuntu/coinbot/data/trades.db')
c = conn.cursor()

for acct in ['main', 'user2']:
    c.execute("""
        SELECT id, entry_time, exit_time, entry_price, exit_price,
               round(pnl,2), close_reason
        FROM trades
        WHERE status='closed' AND account_id=? AND entry_time >= ?
        ORDER BY exit_time
    """, (acct, CUTOFF))
    rows = c.fetchall()

    print(f"\n=== {acct} ===")
    total = 0
    for r in rows:
        eid, et, xt, ep, xp, pnl, reason = r
        et_kst = datetime.fromisoformat(et).astimezone(KST).strftime('%m/%d %H:%M') if et else "?"
        xt_kst = datetime.fromisoformat(xt).astimezone(KST).strftime('%m/%d %H:%M') if xt else "?"
        total += pnl or 0
        flag = " ←손실" if (pnl or 0) < 0 else ""
        print(f"  #{eid} {et_kst}→{xt_kst} 진입{ep:.2f} 청산{xp:.2f} PnL={pnl}{flag}")
    print(f"  합계: {round(total,2)} USDT ({len(rows)}거래)")
PYEOF
```

## 보고 형식

결과를 아래 형식으로 사용자에게 정리해서 전달한다.

```
**Iter4 이후 PnL** (KST 기준, NEW_STRATEGY_DATE~)

📌 **main 계정**
| 진입 | 청산 | 진입가 | 청산가 | PnL |
|------|------|--------|--------|-----|
| MM/DD HH:MM | MM/DD HH:MM | 0000 | 0000 | +X.XX |
...
합계: **+X.XX USDT** (N거래)

📌 **user2 계정**
(동일 형식)

📊 **전체 합산**: main X.XX + user2 X.XX = **합계 USDT**
```

- 손실 거래는 PnL에 ← 표시
- 연속 손실 구간이 있으면 하이라이트
- 모든 시각은 KST (UTC+9)

## 주의사항

- entry_time이 NULL인 거래는 구버전 데이터 — cutoff 이전으로 자동 제외됨
- close_reason이 'sl'이어도 수익 가능 (트레일 SL)
- 계정명은 `main` / `user2` (account_1 아님)
