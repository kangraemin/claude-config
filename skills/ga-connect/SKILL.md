---
name: ga-connect
description: Google Analytics 4 Data API를 프로젝트에 연결. 서비스 계정 인증, API 활성화, 쿼리 스크립트 생성을 자동화한다. "GA 연결", "GA4 연결해", "애널리틱스 데이터 좀 봐봐", "GA 데이터 조회", "analytics 연결", "GA 써봐", "GA 열어봐" 등 사용자가 GA 데이터를 요청하거나 연결을 지시할 때 반드시 이 스킬을 사용.
---

# /ga-connect

GA4 Data API 연결을 프로젝트에 세팅하고 바로 쿼리 가능한 상태로 만든다.

📚 관련 라이브러리: `library/api/google-analytics-data/service-account-setup.md`

## 전제

- `gcloud` CLI가 설치되어 있고 로그인되어 있음
- Python 3 + `google-analytics-data` 라이브러리 (없으면 `pip install google-analytics-data`)

## 플로우

### 1. 기존 서비스 계정 JSON 키 탐색

```bash
find ~ -maxdepth 5 -name "*.json" 2>/dev/null | xargs grep -l "service_account" 2>/dev/null | head
```

발견되면 경로 + `client_email` 읽기:
```bash
python3 -c "import sys,json; d=json.load(open('<PATH>')); print(d['client_email']); print(d['project_id'])"
```

**재사용 우선**. 여러 프로젝트가 하나의 서비스 계정을 공유해도 됨 (GA4 속성별로 접근 권한만 추가해주면 됨).

없으면 새로 만드는 경로 안내:
- https://console.cloud.google.com/iam-admin/serviceaccounts
- Create service account → Create key (JSON) → 다운로드 → `~/.claude/<project>-sa.json`으로 이동

### 2. GA4 Data API 활성화

```bash
gcloud services enable analyticsdata.googleapis.com --project=<PROJECT_ID>
```

프로젝트 ID는 서비스 계정 JSON의 `project_id` 값 사용.

### 3. Property ID 확인

사용자에게 요청:
- "GA4 Admin(⚙️) → Property details → **Property ID** (9자리 숫자) 알려주세요"
- ❌ `G-XXXXXXXX`는 Measurement ID. Data API는 숫자 Property ID 필요.

### 4. 서비스 계정에 Property 접근 권한 부여 (사용자 수동 단계)

**이건 API로 불가. 사용자가 직접 해야 한다.**

안내문구:
> GA4 Admin(⚙️) → **Property access management** → `+` → **Add users**
> 이메일: `<service-account>@<project>.iam.gserviceaccount.com`
> 권한: **Viewer**

추가했다고 답 받으면 5번 진행.

### 5. 쿼리 스크립트 생성

`scripts/ga-query.py` 생성 (아래 [템플릿](#템플릿-scriptsga-querypy) 참조). 상수 치환:
- `PROPERTY_ID`
- `SA_PATH` (서비스 계정 JSON 절대 경로)

### 6. 테스트

```bash
python3 scripts/ga-query.py overview --days 30
```

- 성공: JSON 출력 → 사용자에게 요약 설명
- 403 `PERMISSION_DENIED`: 4번 단계(Property access 추가) 재확인
- 403 `SERVICE_DISABLED`: 2번 단계(API 활성화) 재확인

### 7. 커밋 제안

스크립트 + 관련 변경사항을 `feat: GA4 Data API 연결 스크립트` 같은 메시지로 커밋 제안.

## 템플릿 (`scripts/ga-query.py`)

```python
#!/usr/bin/env python3
"""GA4 Data API query tool.

Usage:
  python scripts/ga-query.py overview [--days 30]
  python scripts/ga-query.py events [--days 7]
  python scripts/ga-query.py countries [--days 30]
  python scripts/ga-query.py retention [--days 30]
  python scripts/ga-query.py raw --metrics activeUsers,sessions --dimensions country --days 7
"""
import argparse
import json
import os
import sys

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account

PROPERTY_ID = "<PROPERTY_ID>"   # 9자리 숫자
SA_PATH = os.path.expanduser("<SA_JSON_PATH>")


def client():
    creds = service_account.Credentials.from_service_account_file(SA_PATH)
    return BetaAnalyticsDataClient(credentials=creds)


def run(c, metrics, dimensions, days):
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        metrics=[Metric(name=m) for m in metrics],
        dimensions=[Dimension(name=d) for d in dimensions],
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        limit=100,
    )
    return c.run_report(req)


def fmt(resp):
    dims = [h.name for h in resp.dimension_headers]
    mets = [h.name for h in resp.metric_headers]
    rows = []
    for r in resp.rows:
        row = {}
        for i, d in enumerate(dims):
            row[d] = r.dimension_values[i].value
        for i, m in enumerate(mets):
            row[m] = r.metric_values[i].value
        rows.append(row)
    return {"dimensions": dims, "metrics": mets, "rows": rows}


def cmd_overview(args):
    resp = run(
        client(),
        ["activeUsers", "newUsers", "sessions", "averageSessionDuration", "screenPageViews"],
        [],
        args.days,
    )
    print(json.dumps(fmt(resp), indent=2, ensure_ascii=False))


def cmd_events(args):
    resp = run(client(), ["eventCount"], ["eventName"], args.days)
    print(json.dumps(fmt(resp), indent=2, ensure_ascii=False))


def cmd_countries(args):
    resp = run(client(), ["activeUsers", "sessions"], ["country"], args.days)
    print(json.dumps(fmt(resp), indent=2, ensure_ascii=False))


def cmd_retention(args):
    resp = run(client(), ["activeUsers"], ["cohort", "cohortNthDay"], args.days)
    print(json.dumps(fmt(resp), indent=2, ensure_ascii=False))


def cmd_raw(args):
    metrics = [m.strip() for m in args.metrics.split(",") if m.strip()]
    dimensions = [d.strip() for d in args.dimensions.split(",") if d.strip()] if args.dimensions else []
    resp = run(client(), metrics, dimensions, args.days)
    print(json.dumps(fmt(resp), indent=2, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in [
        ("overview", cmd_overview),
        ("events", cmd_events),
        ("countries", cmd_countries),
        ("retention", cmd_retention),
    ]:
        sp = sub.add_parser(name)
        sp.add_argument("--days", type=int, default=30)
        sp.set_defaults(func=fn)
    sp = sub.add_parser("raw")
    sp.add_argument("--metrics", required=True)
    sp.add_argument("--dimensions", default="")
    sp.add_argument("--days", type=int, default=30)
    sp.set_defaults(func=cmd_raw)

    args = p.parse_args()
    try:
        args.func(args)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        if "PERMISSION_DENIED" in str(e) or "403" in str(e):
            print(
                f"\n→ GA4 Admin → Property access management에서 서비스 계정을 Viewer로 추가했는지 확인하세요.",
                file=sys.stderr,
            )
        sys.exit(1)


if __name__ == "__main__":
    main()
```

## 자주 쓰는 쿼리 예시

| 목적 | 커맨드 |
|---|---|
| 요약 | `overview --days 30` |
| 이벤트 분포 | `events --days 30` |
| 국가 분포 | `countries --days 30` |
| 리텐션 | `retention --days 30` |
| 커스텀 파라미터 | `raw --metrics eventCount --dimensions eventName,customEvent:step_number --days 30` |
| 소스/미디엄 | `raw --metrics sessions --dimensions sessionSource,sessionMedium --days 7` |
| 기기 분포 | `raw --metrics activeUsers --dimensions deviceCategory --days 30` |

## 이미 연결된 프로젝트에서

`scripts/ga-query.py`가 있으면 그냥 바로 실행. 재세팅 불필요.

## 주의

- 서비스 계정 JSON은 절대 리포에 커밋 금지. `.gitignore`에 `*-sa.json` 또는 `~/.claude/` 바깥 경로에 보관.
- Measurement ID(`G-XXX`)는 **Data API에 못 씀**. Property ID(9자리 숫자)만 유효.
- Property access는 **API로 추가 불가** (사용자 수동 단계). 자동화하려면 Admin API + OAuth 필요, 단순 세팅엔 오버킬.
