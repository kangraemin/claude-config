# 참고한 오픈소스 스킬 (2026-11-07 조사, 별 수는 그날 기준)

| 저장소 | 별 | 라이선스 | 가져온 것 |
|---|---|---|---|
| coreyhaines31/marketingskills (analytics, conversion-tracking) | 58.8k | MIT | 이벤트 이름 object_action·snake_case, 기록표(tracking plan), GA 추천 이벤트 우선 |
| getsentry/skills | 1.1k | - | 오류 기록에 화면·버전·사용자 맥락 붙이기 |
| firebase/agent-skills (firebase-analytics, firebase-crashlytics) | 505 | Apache-2.0 | 설정 파일 먼저, Firebase↔GA 연결, DebugView 확인, custom key·로그·non-fatal, 심볼 업로드, 테스트 크래시 |
| getsentry/sentry-for-ai | 275 | MIT | 키 없어도 빌드 성공, 디버그는 크게·출시는 조용히 |
| PostHog/skills (instrument-error-tracking) | 78 | MIT | 기존 호출 grep 먼저, 중앙 파일 하나 |
| amplitude/mcp-marketplace (add-analytics-instrumentation) | 46 | - | 코드 위치까지 적은 기록표 |
| Accoil/product-tracking-skills | 45 | - | 화면 문구를 이름에 넣지 않기, 종류는 파라미터로, 끝말 규칙(_id·_count·is_·has_) |
| mixpanel/skills | 18 | - | 개인정보 금지·동의 |
| rudderlabs | 19 | - | 중복 전송 금지 |

## 어느 것에도 없어서 직접 넣은 것
- app_platform(토스·웹·안드로이드·iOS) 파라미터 + 사용자 속성 + 맞춤 측정기준.
- build(release/test) 구분.
- 서비스 계정 뷰어 권한 → 아침 리포트 자동 편입.
- 스토어 심사 중 빌드는 건드리지 않기.
- `scripts/ga_check.py`(속성 하나의 로깅 상태를 숫자로).
