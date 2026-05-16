---
name: ga-analyze
description: GA4 데이터 스냅샷을 저장하고 이전 스냅샷 대비 증감을 계산해 개선 액션 아이템을 뽑는 스킬. 시계열로 데이터를 축적해서 "2주 전보다 리텐션이 좋아졌나?" 같은 질문에 답할 수 있게 한다. "GA 분석", "GA 분석해봐", "데이터 분석", "지표 어때", "KPI 뽑아", "리텐션 어때", "유입 어때", "스냅샷 찍어", "analytics 보고서", "GA 리포트" 등 사용자가 GA 데이터를 분석하거나 개선점을 찾으려 할 때 반드시 이 스킬을 사용. 단순 "GA 열어봐" 같은 접근은 ga-connect 스킬로, 분석·비교·리포트가 필요하면 이 스킬로 라우팅.
---

# /ga-analyze

프로젝트의 GA4 Property에서 핵심 지표 스냅샷을 뜨고, 이전 스냅샷과 비교해 **"뭐가 나아졌고 뭐가 나빠졌고 뭘 먼저 고쳐야 하는지"**를 답하는 스킬.

📚 관련:
- `library/api/google-analytics-data/` — GA4 Data API 세팅 노하우
- `ga-connect` 스킬 — 최초 연결 (없으면 먼저 해야 함)

## 철학

- **스냅샷은 영구 보관한다.** 매 실행마다 `analytics/snapshots/*.json` 에 쌓아둔다. 몇 달 후 "출시 직후와 비교" 같은 질문에 답하려면 지금 데이터를 정확히 남겨야 한다.
- **요약만 보고 원본을 잃지 않는다.** 리포트는 markdown으로 쓰지만 raw JSON은 항상 보존. 나중에 새 관점으로 재분석할 수 있어야 한다.
- **델타 없는 분석은 분석이 아니다.** 숫자 하나는 의미 없다. 이전 값과의 증감을 같이 보여야 한다.
- **액션은 우선순위로.** 문제를 나열만 하면 무력감만 남는다. P0/P1/P2/P3로 분류해 "지금 뭘 먼저 해야 하나"를 명확히 한다.

## 전제

- 프로젝트에 `scripts/ga-query.py`가 있어야 한다 (없으면 `ga-connect` 스킬 먼저 호출)
- Python `google-analytics-data`, `google-oauth2` 설치됨

## 플로우

### 1. 스킬 스크립트를 프로젝트에 복사

```bash
cp ~/.claude/skills/ga-analyze/scripts/ga-snapshot.py scripts/ga-snapshot.py
```

매번 복사할 필요는 없음 — 이미 있으면 스킵.

### 2. 스냅샷 + 리포트 생성

```bash
python3 scripts/ga-snapshot.py --days 30
```

**동작**:
1. `scripts/ga-query.py`에서 `PROPERTY_ID`, `SA_PATH` 파싱
2. 20+ 개의 표준 쿼리 배치 실행 (overview, sources, devices, countries, events, pages, first-session cohort, purchases, ads)
3. `analytics/snapshots/YYYY-MM-DDTHHMM.json` 으로 저장
4. 직전 스냅샷과 비교 (있으면)
5. `analytics/reports/YYYY-MM-DD.md` 생성

### 3. 리포트 사용자에게 요약 전달

리포트 파일 읽어서 주요 수치 + 액션 아이템을 대화에서 요약. 리포트 파일 경로도 함께 알려줘서 나중에 재참조 가능하게.

### 4. 데이터 축적

`analytics/` 폴더는 **git에 커밋**. 리포지토리에 남겨두면 시계열 비교가 쉬워진다 (6개월 뒤 "출시 직후와 지금" 비교 등).

첫 실행 후:
```bash
git add analytics/ scripts/ga-snapshot.py
git commit -m "feat: GA4 snapshot tooling + baseline"
```

## 저장되는 데이터

`analytics/snapshots/<timestamp>.json`:

```json
{
  "taken_at": "2026-04-18T09:00",
  "period_days": 30,
  "property_id": "528427024",
  "sections": {
    "overview": [{"activeUsers": "45", ...}],
    "sources": [...],
    "new_users_by_day": [...],
    "devices": [...],
    "countries": [...],
    "events": [...],
    "pages": [...],
    "first_session_engagement": [...],
    "purchases": [...],
    "ads": [...]
  }
}
```

이 구조는 **절대 바꾸지 말 것**. 미래의 비교가 깨진다. 필드를 추가하는 건 OK, 이름 변경/삭제는 ❌.

## 리포트 구조

- **Headline**: 활성유저, 신규, 세션, 평균세션, engagement rate — vs prev
- **Key events**: 주요 이벤트별 count + 유저당 빈도 + vs prev
- **Funnel ratios**: 튜토리얼 스텝/유저, challenge 완주율, upgrade 구매율
- **Acquisition**: source/medium 별 세션·유저·engagement/user
- **Countries**: 국가별 유저 + engagement/user
- **Devices**: desktop/mobile/tablet
- **Action items (ranked)**: P0/P1/P2/P3 별 구체적 액션

## 액션 아이템 우선순위 기준

휴리스틱이며, 필요시 `scripts/ga-snapshot.py`의 `prioritize_actions()` 에서 튜닝:

| 심각도 | 트리거 조건 | 예시 |
|---|---|---|
| **P0** | 리텐션 붕괴, 핵심 루프 이탈 | 튜토 step/user < 3, 신규/활성 비율 > 90% |
| **P1** | 측정 불가 / 단일 의존 | Custom dimension 미등록, 유입 한 채널 > 65% |
| **P2** | 수익화 계측 안 됨, 디바이스 편향 | transactions=0 with 10+ users |
| **P3** | 감지된 문제 없음 — 수동 확인 권장 | 헬스 체크 위주 |

## 자주 쓰는 추가 쿼리

스냅샷엔 기본 지표만 들어간다. 특정 가설이 있으면 `scripts/ga-query.py raw`로 파고들 것:

```bash
# 시간대별 세션
python3 scripts/ga-query.py raw --metrics sessions --dimensions hour --days 7

# 랜딩 페이지 성능
python3 scripts/ga-query.py raw --metrics sessions,engagementRate --dimensions landingPage --days 30

# Custom dimension (등록 이후)
python3 scripts/ga-query.py raw --metrics eventCount --dimensions "customEvent:step" --days 7
```

## 주의

- **Custom dimension**: GA4는 이벤트 파라미터를 기본 제공하지 않는다. `step`, `action`, `challenge_type` 등 파라미터로 쿼리하려면 GA4 Admin → Data display → Custom definitions에서 **미리 등록**해야 한다. 등록 이후 들어온 데이터부터만 조회 가능 (소급 불가).
- **샘플링**: GA4 표준 리포트는 상위 플랜에서 샘플링되지 않지만, 무료 속성에서 대량 쿼리 시 주의. 현재 스냅샷 쿼리량은 안전한 수준.
- **타임존**: `today`, `NdaysAgo`는 Property의 타임존 기준. GA4 설정 타임존 확인.
- **비용**: GA4 Data API는 무료 쿼터 있음 (Core Reporting: 25,000 tokens/day, 250,000 tokens/hour). 하루 10번 스냅샷 정도는 문제 없음.

## 실행 주기 제안

- **일간**: 출시 직후 2주간은 매일 (급변 모니터링)
- **주간**: 안정화 이후 매주 월요일 (retro 자료로 활용)
- **수시**: 새 기능 출시 / 마케팅 캠페인 전후

`/loop` 스킬과 결합하면 자동 주기 실행 가능.
