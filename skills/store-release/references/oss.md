# 스토어 배포·심사 오픈소스 비교 (2026-11-10)

별·최근 커밋은 gh api 실측. 받은 곳은 ~/programming/oss/ (--depth 1 --filter=blob:none).

| 이름 | 별 | 최근 커밋 | 받은 경로 | 판정 | 이유 |
|---|---|---|---|---|---|
| fastlane/fastlane | 42374 | 11/09 | oss/fastlane-src (이미 brew로 설치됨) | 부분 채택 | 서명(match)·빌드·TestFlight·Play AAB 업로드(supply)엔 좋다. 이미 game, developerTycoon에 Fastfile 있음. 메타데이터·심사 회신은 asc가 더 가볍다. 버전이 낡아 `fastlane update_fastlane` 경고 |
| rorkai/App-Store-Connect-CLI (asc) | 8312 | 11/10 | oss/App-Store-Connect-CLI | **채택** | 단일 Go 바이너리, ASC API 키로 바로 동작. 앱·빌드·심사 상태·validate·메타데이터·스크린샷·연령등급·심사 제출·고객 리뷰 회신까지 있음. 우리 asc_*.sh는 Chrome 조작이라 이걸로 대체 가능 |
| rorkai/app-store-connect-cli-skills | 1131 | 11/07 | oss/app-store-connect-cli-skills | 부분 채택 | asc 쓰는 법 스킬 26개(release-flow, submission-health, metadata-sync, localize-metadata 등). `asc install-skills`로 설치 가능. 참고용으로 둠 |
| devsemih/appstore-review-skill | 105 | 07/13 | oss/appstore-review-skill | 부분 채택 | 애플 가이드라인·Play 정책 요약(2.3.10 다른 플랫폼 이름 금지 = 우리 5.6/토스 반려와 같은 계열)과 코드 점검 스킬. 규칙 참고 자료로만 씀. 별 적음 |
| ParthJadhav/app-store-screenshots | 7887 | 11/07 | oss/app-store-screenshots | 안 씀(참고) | 스크린샷 생성기 스킬. 우리는 store_images.py·Figma로 이미 만듦. 문구·프레임 아이디어 참고만 |
| keremerkan/ascelerate | 244 | 11/09 | oss/ascelerate | 안 씀 | asc와 기능이 겹치고 별·범위 작음 |
| Triple-T/gradle-play-publisher | 4322 | 10/14 | oss/gradle-play-publisher | 안 씀 | 안드로이드 네이티브 Gradle 전용. 우리는 RN/Expo·Unity라 fastlane supply나 Play API가 맞음 |
| XcodesOrg/xcodes | 4890 | 09/14 | oss/xcodes | 안 씀 | Xcode 버전 설치기. 지금 문제와 무관 |
| codemagic-ci-cd/cli-tools | 499 | 10/30 | oss/codemagic-cli-tools | 안 씀 | app-store-connect/google-play CLI가 있으나 asc·fastlane과 겹치고 별 적음 |
| expo/eas-cli | 1383 | 11/10 | (안 받음, npm) | 해당 앱만 | Expo 앱의 build/submit에만. 레포가 커서(42MB+) 받지 않음 |
| Play Console API 클라이언트 (googleapis/google-api-python-client 8971) | 8971 | 11/10 | (안 받음, 653MB) | 안 받음 | 용량 초과. 필요하면 pip install로 |

## 검증 (asc 6.6.0, `brew install asc`, 읽기 전용만)
키: ~/.claude/.env의 ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_FILE(→ASC_PRIVATE_KEY_PATH로 넘김). 값은 출력하지 않음.
- `asc apps list --output table`: 앱 12개 조회 성공(스레드 언팔 확인, 먹맵, 나사톡톡, 어디먹, 운빨로 살아남기 등)
- `asc builds list --app 6829148689`: 빌드 2개(1, 2) VALID 조회 성공
- `asc review status --app 6829148689`: 버전 1.0 WAITING_FOR_REVIEW, 제출 정보 조회 성공
- `asc validate --app 6829148689`: 제출 준비 점검 성공. error 3건(availability.missing, age_rating.missing_field socialMediaAgeRestricted 등), warning 1건(키워드가 앱 이름과 겹침). 사람이 놓치기 쉬운 항목을 API로 잡아 준다
- 쓰기(제출·업로드·회신)는 하지 않음.

## 우리 자체 스크립트와 대응
- 자체: ~/.claude/skills/chrome-direct/scenarios/asc_submit_review.sh, asc_resubmit.sh, asc_review_reply.sh, asc_store_listing.{sh,py}, asc_privacy.sh, asc_dsa_trader.sh (모두 Chrome 화면 조작, 깨지기 쉽고 로그인 필요)
- 대체: `asc review submit/doctor`, `asc validate`, `asc review details-update`, `asc localizations`/`metadata`, `asc screenshots`, `asc age-rating`, `asc reviews respond`
- 안 대체됨(웹 필요할 가능성): asc_privacy.sh(앱 개인정보 영양표 답변), asc_dsa_trader.sh(DSA 트레이더 선언). `asc` 안에 privacy/agreements 관련이 있는지 해당 작업 때 `asc search "privacy"`로 먼저 확인
- Resolution Center 반려 메시지 회신(2.1 회신): asc_review_reply.sh는 Resolution Center 메시지 스레드 회신인데 ASC API엔 공개 엔드포인트가 없어 asc `web` 세션 명령 쪽인지 확인 필요(미검증)
- Play: 서비스 계정 JSON은 ~/.claude/ai-paper-analytics-sa.json 하나만 찾았고 이건 analytics용(ai-paper-analytics 프로젝트)이라 Play 업로드용이 아님. 자체 play_*.py도 Chrome 조작. Play 쪽은 asc 같은 대체재가 없어서 fastlane supply(서비스 계정 키 필요) 또는 Play 콘솔 조작을 유지

## 계속 자체로 만들어야 하는 것 (오픈소스에 없음)
- 스토어판 토스 문구·타 플랫폼 이름 검사: defense-game tools/store_precheck.mjs 방식(BANNED 정규식, 런처 이름·아이콘 일치, 방침에 앱 이름 포함). 리뷰 스킬은 가이드라인 2.3.10을 설명만 하고 우리 소스 문구를 검사해 주진 않음
- Play 비공개 테스트 요건(12명·14일) 추적, Play 심사 중 새 버전 불가 대기
- 개인정보처리방침 URL 일괄 교체(Play 콘솔), 스크린샷 문구 검수
- codesign 키체인 암호 창 회피(맥 환경 문제, 도구 무관)

## 적용 권고
1. 앞으로 App Store 조회·검증·심사 제출은 `asc`를 먼저 쓴다(`asc validate`를 제출 전 필수 점검으로).
2. Chrome 기반 asc_*.sh는 asc로 대체되는 것부터 순서대로 걷어낸다(제출·메타데이터·리뷰 회신).
3. 서명·빌드·Play 업로드는 기존 fastlane Fastfile 유지.
