# 스토어 제출 이슈 모음 (App Store Connect / Google Play)

수집 범위
- 대상 앱: 먹맵, 어디먹, 어디썼, 스레드 언팔 확인, 운빨로 살아남기(forge-survivor), 골골냥, 오늘의 눈썰미, 나사톡톡, 뚝카이로클리닉. 보류 앱(과학기록·AI-Tycoon·러너스하이·한개국어)은 제출 경험이 있는 것만.
- 출처: ~/claude-library decisions·library, 각 레포 git log·docs, ~/.claude/skills 스크립트, 세션 로그.
- 원문을 못 찾은 곳은 "원문 미확보"로 적었다.
- 경로 약기: LIB = ~/claude-library, VC = ~/programming/vibecoding, SC = ~/.claude/skills/chrome-direct/scenarios

---

## A. 심사 거절 (Apple)

### A1. Apple 5.6 — 심사 때 숨겨진 기능(스토어 빌드 정책)
- 플랫폼: iOS
- 단계: 심사 거절(11/10)
- 증상 원문: "We've identified a pattern of unusual behavior with the app that is commonly associated with fraudulent activity. Specifically, the app contains features that appear to have been intentionally hidden during the review process. Manipulative and misleading behavior is not consistent with guideline 5.6."
- 원인: 3번째 분석부터 뜨는 전면광고가 심사 중엔 안 보였다. 토스 문구도 스토어 빌드에 남아 있었다.
- 적용한 해결: 스토어 빌드에서 전면광고와 토스 문구 제거(`INTERSTITIAL = IS_NATIVE ? '' : ...`). 원격 설정·로그인·숨은 모드가 없다고 영어로 답신. 가짜 계정 테스트 ZIP 첨부, 심사 메모 갱신.
- 재발 방지 자동화: `VC/defense-game/tools/store_precheck.mjs`(토스 문구 검사 포함). 규칙 결정 `LIB/decisions/_global/scope/store-builds-must-have-no-toss-mentions.md`.
- 영향 앱: 스레드 언팔 확인(원 사례). 같은 유형이 운빨(설정의 약관·개인정보 링크), 어디먹(개인정보 페이지 "토스에서 열기" 띠), 나사톡톡(트로피 버튼은 토스 안에서만)에서 재발.
- 증거: threads-unfollow df71a7d, 1ba8c13 / eodimeok c332e87 / screw-puzzle 6b56732, 772b379 / 세션 88d507a8 / 제출 ID 97b10c21-03cf-4cd1-a850-95c5a342aef3

### A2. Apple 2.1 Information Needed (신규 계정, 심사 이력 부족)
- 플랫폼: iOS
- 단계: 첫 제출 후 심사 중
- 증상 원문: "This app has been submitted by a developer account that has a limited App Review history. We need additional information to better understand the app and complete the review."
- 요구 항목: 실기기 화면 녹화, 용도·대상, 설정 방법, 외부 서비스, 지역 차이, 규제 산업 서류, IAP 개요.
- 원인: 개발자 계정의 심사 이력이 적음.
- 적용한 해결: 실기기 녹화와 항목별 답신(영어). 심사용 데모 모드 `-reviewDemo` 실행 인자 추가(iOS는 env/NSUserDefaults도 읽음). 답신 후 Apple이 "additional time needed" 또는 "continue the review"로 응답.
- 재발 방지 자동화: `SC/asc_review_reply.sh`(답신·첨부), 답신 초안 템플릿 spot-difference `docs/store-submission/07`.
- 영향 앱: 운빨(11/3 답신), 눈썰미(10/29·11/2), 스레드 언팔 확인(11/2 요청, 11/8 답신), 뚝카이로(2.1 Performance: App Completeness, 10/29 거절·11/6 답신)
- 증거: spot-difference 5e3500b, a614c07, 367c1c8 / 세션 609cc2a4, affedaf3

### A3. Apple 4.3 Spam
- 플랫폼: iOS
- 단계: 심사 거절(11/10)
- 증상: 질문 9개가 달린 4.3(스팸) 거절. 원문 미확보(답신 초안만 있음).
- 원인: 틀린그림찾기 장르의 유사 앱 판단으로 추정되나 확인된 근거는 없음.
- 적용한 해결: 9개 질문에 답하는 답신 작성.
- 재발 방지 자동화: 없음
- 영향 앱: 눈썰미
- 증거: spot-difference 8557e84, `docs/store-submission/08_appstore_4_3_reply.txt`, 세션 609cc2a4

### A4. 심사 중 빌드 교체 금지
- 플랫폼: iOS, Android
- 단계: 심사 대기·심사 중
- 증상: 수정하려고 빌드를 바꾸면 심사가 처음부터 다시 시작.
- 적용한 해결: 심사 중인 빌드는 건드리지 않고, 수정은 첫 업데이트에 싣는다.
- 재발 방지 자동화: 결정 문서뿐(스크립트 없음)
- 영향 앱: 눈썰미, 운빨
- 증거: `LIB/decisions/spot-difference/process/store-builds-under-review-untouched-fixes-ship-in-first-update-toss-web-now.md`, `LIB/decisions/_global/process/store-submit-needs-automated-policy-precheck-icon-name-policy-no-toss-and-no-swap-during-review.md`

### A5. 리뷰어용 로그인·탈퇴 문구가 서버 동작과 어긋남
- 플랫폼: iOS, Android
- 단계: 심사 메모, 데이터 보안
- 증상: 심사 계정이 없어 로그인 불가. 탈퇴 안내 문구가 서버 동작과 다름.
- 적용한 해결: 심사용 숨김 코드 로그인, 탈퇴 문구를 서버와 일치시킴, 데이터 보안의 계정 삭제 URL 입력.
- 재발 방지 자동화: 없음(결정 문서)
- 영향 앱: 러너스하이(보류)
- 증거: `LIB/decisions/runnershi/process/store-review-login-and-withdraw-copy-must-match-server.md`, RunnersHi 2228b0c, 206f02f

---

## B. 심사 거절 (Google Play)

### B1. 혼동을 야기하는 주장 정책 위반 (런처 이름·아이콘이 스토어와 다름)
- 플랫폼: Android
- 단계: 정책 상태, 앱 거부됨(11/9~11/10)
- 증상: "혼동을 야기하는 주장 정책 위반(설명·스크린샷 문구)". Console 정책 상태 문구 그대로의 원문은 미확보(세션 전달 메시지 요약만 있음).
- 원인: 기기 런처 이름·아이콘이 스토어 등록 이름·아이콘과 다름(Capacitor 기본 런처 아이콘 등).
- 적용한 해결: 런처 이름·아이콘을 스토어와 같게 맞춤. 뚝카이로는 스토어 아이콘, adaptive 배경 #17302B, iOS AppIcon 1024 적용 후 versionCode 2 / versionName 1.0.1로 재제출.
- 재발 방지 자동화: `VC/defense-game/tools/store_precheck.mjs`(런처 이름·아이콘 = 스토어 이름·아이콘 검사)
- 영향 앱: 운빨, 뚝카이로
- 증거: defense-game 9206cd2, 1e14b89, b81f6c0 / ttuk-chiro-clinic fc189fa / 세션 affedaf3

### B2. 사용자 데이터 정책 — 개인정보처리방침 오류
- 플랫폼: Android
- 단계: 정책 상태, 앱 거부됨(11/9~11/10)
- 증상: "사용자 데이터 정책 — 개인정보처리방침이 잘못됨(URL 접속·앱 이름/개발자 명시·수집 항목 확인)". 원문 전체는 미확보.
- 원인: 개인정보처리방침에 앱 이름·패키지·개발자가 없거나 URL이 열리지 않음.
- 적용한 해결: 방침 본문에 앱 이름·패키지·개발자 명시. 스토어 전용 방침 페이지 분리(먹맵 `/privacy/app`, 토스 문구 제거). 방침 URL은 `play_privacy_url.py`로 입력.
- 재발 방지 자동화: `store_precheck.mjs`(방침에 앱 이름·패키지·개발자 포함 검사), `SC/play_privacy_url.py`
- 영향 앱: 운빨, 먹맵, 어디먹
- 증거: defense-game-web b87ee24, 6741c18, 8c39612 / mukmap 3a0e6ae / eodimeok c332e87 / 세션 affedaf3, 5513ea85

---

## C. App Store Connect 설정·API

### C1. 앱 레코드는 API로 못 만든다
- 플랫폼: iOS
- 단계: 앱 등록
- 증상: Bundle ID는 API로 만들어지나 App 레코드 생성 API는 없음.
- 적용한 해결: 웹(Chrome)에서 앱 만들기.
- 재발 방지 자동화: `SC/apple_appid_asc_create.sh`(App ID 등록, 약관 동의, ASC 앱 생성), `VC/eodimeok/native/store/asc_setup.py`
- 영향 앱: 전부
- 증거: `LIB/library/api/app-store-connect-api-creates-bundle-ids-but-not-app-records-create-app-in-web.md`

### C2. Bundle ID가 다른 팀에 선점됨 (409)
- 플랫폼: iOS
- 단계: Bundle ID 등록
- 증상: 409, 같은 ID를 다른 팀이 사용.
- 적용한 해결: iOS용 ID를 분리(골골냥 `com.oguriworks.golgolnyang`). 판매자명 수정 시 이메일 재인증이 걸림.
- 재발 방지 자동화: 없음
- 영향 앱: 골골냥
- 증거: `LIB/library/game/app-store-bundle-id-taken-by-other-team-409-split-ios-id-and-apple-seller-edit-reverifies-email.md`

### C3. 제출 시 가격 미설정 — APP_PRICING_REQUIRED / "가격에서 가격 등급을 선택해야 합니다"
- 플랫폼: iOS
- 단계: 심사 제출(reviewSubmission)
- 원인: 무료 앱이라도 appPriceSchedule이 없음.
- 적용한 해결: 무료 가격 스케줄(appPriceSchedule) 생성.
- 재발 방지 자동화: `SC/asc_store_listing.py`, `SC/asc_submit_review.sh`
- 영향 앱: 운빨 외 신규 앱 전반
- 증거: `LIB/library/api/app-store-connect-review-submission-needs-app-price-schedule-else-app-pricing-required.md`

### C4. IAP 상품 ID 중복 ("already used")
- 플랫폼: iOS
- 단계: 인앱결제 생성
- 원인: 같은 팀의 다른 앱이 쓰는 상품 ID.
- 적용한 해결: 앱별 접두어 `forgesurvivor_` 사용(productPrefixIos).
- 재발 방지 자동화: 없음(앱 설정값)
- 영향 앱: 운빨
- 증거: 세션 affedaf3

### C5. 첫 소모성 IAP는 버전과 함께 제출해야 함 (FIRST_CONSUMABLE_MUST_BE_SUBMITTED_ON_VERSION)
- 플랫폼: iOS
- 단계: 심사 제출
- 증상: API로 제출 실패, 상품 46개를 수동으로 "심사에 추가".
- 적용한 해결: 웹에서 상품별 추가 클릭 자동화.
- 재발 방지 자동화: `SC/asc_store_listing.py`
- 영향 앱: 운빨, 눈썰미
- 증거: 세션 affedaf3, 609cc2a4

### C6. iPad 13인치 스크린샷 필수
- 플랫폼: iOS
- 단계: 메타데이터
- 원인: TARGETED_DEVICE_FAMILY=1,2(iPad 지원).
- 적용한 해결: 13" 스크린샷 추가, 또는 iPhone 전용으로 설정.
- 재발 방지 자동화: `VC/spot-difference/tools/store_images.py`, `~/.claude/skills/apps-in-toss-release-kit/scripts/store_images.py`
- 영향 앱: 운빨
- 증거: `LIB/library/api/app-store-connect-ipad-13inch-screenshots-required-when-app-targets-ipad.md`

### C7. 스크린샷이 아직 처리 중이면 제출 실패
- 플랫폼: iOS
- 단계: 제출
- 적용한 해결: 처리 완료를 기다린 뒤 제출.
- 재발 방지 자동화: `SC/asc_submit_review.sh`
- 증거: 같은 문서(C6)

### C8. 앱 개인정보(영양 표시) 라벨은 API가 없다
- 플랫폼: iOS
- 단계: 메타데이터
- 적용한 해결: Chrome 자동화로 입력·게시.
- 재발 방지 자동화: `SC/asc_privacy.sh`
- 영향 앱: 전부
- 증거: C6 문서, 세션 affedaf3

### C9. 수출 규정 준수 질문 매번 뜸
- 플랫폼: iOS
- 단계: TestFlight·제출
- 적용한 해결: Info.plist에 `ITSAppUsesNonExemptEncryption=false`.
- 재발 방지 자동화: 없음(템플릿에 포함)
- 증거: C6 문서

### C10. 개인정보처리방침 URL은 심사 대기 중에도 PATCH 가능
- 플랫폼: iOS
- 단계: 심사 대기(WAITING_FOR_REVIEW)
- 적용한 해결: API로 privacyPolicyUrl만 수정, 빌드 교체 없음.
- 재발 방지 자동화: `VC/threads-unfollow/scripts/asc_meta.py`
- 영향 앱: 먹맵
- 증거: `LIB/library/api/app-store-connect-privacy-policy-url-patch-works-while-waiting-for-review.md`

### C11. 재제출 API가 409 "Version is not ready to be submitted yet"
- 플랫폼: iOS
- 단계: 거절 후 재제출
- 원인: 웹에서 "심사 업데이트"를 눌러야 버전이 제출 가능 상태가 됨. API 단독으로는 안 됨. 심사 답변 대기 중이면 409 STATE_ERROR.
- 적용한 해결: 버전 페이지에서 "심사 업데이트" 클릭, 이어서 "앱 심사에 다시 제출".
- 재발 방지 자동화: `SC/asc_resubmit.sh`
- 영향 앱: 스레드 언팔 확인
- 증거: `LIB/library/tooling/asc-api-script-needs-asc-key-file-env-and-automatic-signing-export-hangs.md`, threads-unfollow 세션 88d507a8

### C12. 거절·정보요청 상태 제출에는 IAP를 추가할 수 없음
- 플랫폼: iOS
- 단계: 거절 후 재제출
- 적용한 해결: UI에서 기존 제출을 취소한 뒤 `asc_submit_review.sh` 재실행.
- 재발 방지 자동화: `SC/asc_submit_review.sh`
- 영향 앱: 눈썰미, 뚝카이로
- 증거: spot-difference 세션 609cc2a4

### C13. EU DSA 트레이더 선언
- 플랫폼: iOS
- 단계: 메타데이터
- 적용한 해결: 웹에서 트레이더 정보 입력.
- 재발 방지 자동화: `SC/asc_dsa_trader.sh`
- 증거: 세션 affedaf3

### C14. API 403 REQUIRED_AGREEMENTS_MISSING_OR_EXPIRED
- 플랫폼: iOS
- 단계: ASC API 호출 전반
- 원인: 갱신된 약관 미동의.
- 적용한 해결: 웹에서 약관 동의 후 재시도.
- 재발 방지 자동화: `SC/apple_appid_asc_create.sh`(약관 동의 포함)
- 증거: `LIB/library/infra/cicd/testflight-asc-api-agreement-403-and-xcode-runner.md`

### C15. 유료앱 약관 처리 중엔 StoreKit 상품이 빈 배열
- 플랫폼: iOS
- 단계: IAP 테스트
- 적용한 해결: 약관 처리 완료까지 대기.
- 재발 방지 자동화: 없음
- 증거: `LIB/library/mobile/ios/storekit2-products-empty-while-paid-apps-agreement-processing.md`

### C16. IAP 가격이 전 스토어프론트로 자동 환산됨
- 플랫폼: iOS, Android
- 단계: 인앱결제 가격
- 적용한 해결: 수동 지정한 국가는 환율 자동 조정이 안 되므로 확인.
- 재발 방지 자동화: 없음
- 증거: `LIB/library/product/monetization/store-iap-auto-converts-base-price-to-all-storefronts-manual-countries-not-adjusted.md`

### C17. ASC 웹 로그인 비밀번호가 틀린다고 나옴
- 플랫폼: iOS
- 단계: 웹 자동화 로그인
- 적용한 해결: Chrome 패스키 드롭다운으로 로그인.
- 재발 방지 자동화: chrome-direct 시나리오
- 증거: `LIB/library/tooling/macos-system/asc-web-login-use-chrome-passkey-dropdown-when-saved-password-wrong.md`

---

### C18. 판매 국가(availability)가 비어 있는데 제출됨 — 승인돼도 어느 나라에도 안 나옴
- 증상: `asc validate`가 `availability.missing`(appAvailabilityV2). `asc pricing availability view`가 "no availability configured yet". 가격(무료)은 있어서 제출은 됐다.
- 11/10 실측: 배포 앱 8개 중 7개가 이 상태였다(골골냥만 175개국).
- 해결: `scripts/asc.sh pricing availability create --app <ID> --all-territories --available true --available-in-new-territories true` → `territory-availabilities --app <ID> --paginate`로 175 확인. 심사 대기 중에도 된다(앱 단위 설정).

### C19. `asc validate`의 socialMediaAgeRestricted 오류는 오탐
- `age_rating.missing_field`(socialMediaAgeRestricted)가 떠도 socialMedia=false면 비어 있는 게 맞다. `asc age-rating audit --app ...`가 Ready=true면 무시한다(validate_all.sh가 걸러 냄).
- 2026-09부터 신규 제출·업데이트마다 소셜미디어 문항 답이 필수다. audit에서 Missing이 나오면 그때 `asc age-rating edit`.

## D. 빌드·서명·업로드 (iOS)

### D1. 업로드·export 중 키체인 비밀번호 창에서 멈춤
- 플랫폼: iOS
- 단계: 아카이브/export/업로드
- 증상 원문: "codesign이(가) 키체인에서 '9J3VFUS745' 키 접근을 허용하고자 합니다". 자동 서명 export가 이 창에서 무한 대기.
- 적용한 해결: 키체인 목록을 비운 클라우드 서명, 또는 ASC API로 만든 인증서를 임시 전용 키체인에 넣어 서명.
- 재발 방지 자동화: `~/.config/forge-survivor/ios_upload.sh`(전용 키체인, BUNDLE/APP_ID 환경변수), `asc_api.py`
- 영향 앱: 스레드 언팔 확인, 운빨, 어디먹
- 증거: `LIB/library/infra/cicd/xcode-export-keychain-prompt-avoid-with-empty-keychain-list-cloud-signing.md`, 세션 88d507a8, affedaf3

### D2. 키체인 검색 목록에서 login.keychain 누락 → errSecInternalComponent / WWDR G3
- 플랫폼: iOS
- 단계: 서명, git push
- 적용한 해결: 검색 목록에 login.keychain 복구, WWDR G3 중간 인증서 설치.
- 재발 방지 자동화: `ios_upload.sh`에 기록(2026-11-10)
- 영향 앱: 어디먹
- 증거: `LIB/library/infra/cicd/user-keychain-search-list-missing-login-keychain-breaks-git-push-and-codesign.md`

### D3. 배포 인증서 개수 한도 (409)
- 플랫폼: iOS
- 단계: 인증서 생성
- 적용한 해결: 불필요한 인증서 정리 후 재생성. CI에서는 개발 인증서 정리 단계를 추가.
- 재발 방지 자동화: hankuk 00dd33f (CI 정리)
- 영향 앱: 한개국어(보류)
- 증거: hankuk dc6a3f9, 00dd33f

### D4. Unity iOS export에 1024 마케팅 아이콘 누락 (rc=70)
- 플랫폼: iOS
- 단계: 아카이브
- 증상: "Missing app icon ... 1024 by 1024".
- 적용한 해결: 1024 아이콘을 export 결과에 주입한 뒤 빌드.
- 재발 방지 자동화: 없음(문서)
- 증거: `LIB/library/game/unity-ios-export-lacks-1024-marketing-icon-and-keychain-prompt-avoid-with-api-cert-temp-keychain.md`

### D5. ATT 프레임워크 링크 오류 / 서명 없는 기기 빌드
- 플랫폼: iOS
- 적용한 해결: ATT weak-link, 서명 없는 기기 빌드 옵션.
- 재발 방지 자동화: 없음
- 영향 앱: 나사톡톡
- 증거: screw-puzzle 06c9715, `LIB/library/tooling/unity/2021-3-android-gradle-aab-needs-templates-jetifier-blacklist-compilesdk33-and-ios-needs-att-framework.md`

### D6. 디스크 부족 ("No space left")
- 플랫폼: iOS, Android
- 단계: 아카이브·빌드
- 원인: 빌드에 5GB 이상 필요, 한때 124MB만 남음.
- 적용한 해결: 캐시·빌드 산출물 정리 후 재시도.
- 재발 방지 자동화: `disk-cleanup` 스킬
- 영향 앱: 운빨
- 증거: 세션 affedaf3

### D7. Xcode가 계정을 거부해 개발 빌드 서명 불가
- 플랫폼: iOS
- 적용한 해결: ASC API로 프로파일 생성해 서명. 실기기 캡처에는 카메라 권한 필요.
- 재발 방지 자동화: 없음(문서)
- 증거: `LIB/library/mobile/ios/xcode-account-rejected-sign-dev-build-via-asc-api-profile-and-wired-iphone-capture-needs-camera-permission.md`

---

## E. TestFlight

### E1. 외부 테스터 초대에 베타 심사 필드 필요
- 증상: 외부 그룹 초대 실패.
- 적용한 해결: 베타 앱 설명·피드백 이메일·심사 연락처를 먼저 입력.
- 재발 방지 자동화: hankuk 76ade58, 891c3b3, 5641096 (연락처 자동 입력)
- 영향 앱: 한개국어(보류)
- 증거: `LIB/library/infra/cicd/testflight-external-invite-needs-beta-review-fields.md`

### E2. 내부 테스터가 INVITED 상태로 앱이 안 보임 / 멤버 아니면 409
- 적용한 해결: 이메일 수락 뒤에만 앱이 보임. 내부 테스터는 팀 멤버여야 함.
- 재발 방지 자동화: 없음(규칙: 업로드 때 yamyam1575 테스터 포함)
- 증거: `LIB/library/infra/cicd/testflight-internal-tester-invited-state-app-hidden-until-email-accepted.md`, `LIB/decisions/runnershi/process/testflight-uploads-include-yamyam1575-tester.md`

### E3. 빌드 번호 충돌
- 적용한 해결: 빌드 번호 = ASC 최신 + 1로 자동 산출.
- 재발 방지 자동화: hankuk dc6a3f9, RunnersHi-iOS 858c2b9
- 증거: 위 커밋

---

## F. Google Play Console

### F1. 닫힌 테스트 12명×14일 요건
- 적용한 해결: 조직 계정(D-U-N-S)으로 요건 면제, 프로덕션 직행.
- 재발 방지 자동화: 없음(결정 문서)
- 영향 앱: 골골냥 외 전부
- 증거: `LIB/decisions/_global/process/play-release-via-org-account-no-closed-test.md`, cat-petting f99efd1

### F2. 한국 개발자 추가 정보(사업자번호·통신판매업 신고번호·신고기관) 미입력
- 증상: 제출·IAP 활성화·계정 전체가 막힘.
- 적용한 해결: 개발자 프로필에 입력.
- 재발 방지 자동화: `SC/play_dev_status.py`(상태 확인), `SC/play_iap_bulk.py`(korea-info)
- 증거: `LIB/library/business/google-play-korea-paid-app-requires-business-reg-mail-order-no-and-agency.md`

### F3. 앱 생성
- 적용한 해결: 임시 이름으로 만든 뒤 개명(운빨은 'No Way, It Works'로 생성). 이름이 자주 바뀌면 일관성이 깨진다.
- 재발 방지 자동화: `SC/play_app_create.py`
- 증거: 세션 affedaf3

### F4. targetSdk 36, 16KB 페이지 크기, minSdk
- 증상: minSdk 23은 Play 자동 보호에서 거절됨. Unity 2021.3은 targetSdk 36은 되나 미리 빌드된 libunity 때문에 16KB가 막힘.
- 적용한 해결: minSdk 24, Unity 6(6000.0.84f1) + GMA 10.7 사용.
- 재발 방지 자동화: 없음(결정 `unity-games-must-use-unity6`)
- 영향 앱: 먹맵(6801b4e), 나사톡톡(1be833d)
- 증거: `LIB/library/tooling/unity/unity-2021-3-target-api-36-ok-but-16kb-blocked-by-prebuilt-libunity.md`

### F5. Unity 6 + GMA Gradle 9 빌드 실패
- 적용한 해결: GMA 9.6 대신 10.7, androidlib package 속성 패치, 템플릿은 기본값에서 복사.
- 재발 방지 자동화: 없음(문서)
- 증거: `LIB/library/tooling/unity/unity6-gradle9-breaks-gma-9-6-android-build.md`, `unity6-gma-10-7-only-needs-androidlib-package-attr-patch-and-templates-from-defaults.md`

### F6. Unity 2021.3 AAB 빌드 (Gradle 템플릿·Jetifier·compileSdk 33)
- 영향 앱: 나사톡톡
- 증거: screw-puzzle 5b9, `LIB/library/tooling/unity/2021-3-android-gradle-aab-needs-templates-jetifier-blacklist-compilesdk33-and-ios-needs-att-framework.md`

### F7. AD_ID 권한 병합 불일치
- 증상: 광고 ID 선언과 매니페스트 병합 결과가 다름(Firebase가 권한을 끌어옴).
- 적용한 해결: 명시적으로 `tools:node="remove"` 등으로 비활성화.
- 재발 방지 자동화: 없음
- 증거: `LIB/library/mobile/android/firebase-ad-id-permission-merging-needs-explicit-disable.md`

### F8. 첫 프로덕션 출시에 국가/지역 0개
- 증상: 출시 시작이 막힘.
- 적용한 해결: 177~178개 국가/지역 선택.
- 재발 방지 자동화: `SC/play_release.py`
- 영향 앱: 운빨, 뚝카이로
- 증거: 세션 affedaf3, f814539f

### F9. 관리형 게시 / 수동 공개
- 적용한 해결: Play는 관리형 게시 켜기, iOS는 releaseType MANUAL. 날짜 예약 대신 공개 직전까지 대기.
- 재발 방지 자동화: `SC/play_release.py managed`
- 증거: `LIB/decisions/_global/process/ship-until-just-before-public-use-manual-release-and-managed-publishing-not-date-schedule.md`

### F10. 스크린샷 비율·크기 제한
- 증상: 16:9 또는 9:16만 허용.
- 적용한 해결: 변환해서 업로드.
- 재발 방지 자동화: `VC/cat-petting/art/store/build_store.py`, `validate_store.py`
- 증거: `LIB/library/api/app-store-connect-review-submission-needs-app-price-schedule-else-app-pricing-required.md`(Play 메모 포함)

### F11. Play 인앱상품 자동화 함정
- 증상: Material 라디오는 한 번만 클릭, 입력은 execCommand, 원화 반올림, 설명 50자 미만.
- 적용한 해결: 스크립트로 처리.
- 재발 방지 자동화: `SC/play_iap_create.py`(골골냥 10개, 11/6), `SC/play_iap_bulk.py`
- 증거: 위 문서, cat-petting `docs/PLAY_CONSOLE_FORMS.md`

### F12. 스토어 앱 목록이 비어 있음 (웹뷰 origin 거부)
- 증상: 스토어 빌드에서만 목록이 빈 화면.
- 원인: 웹뷰 origin(localhost)이 읽기 API의 CORS 허용 목록에 없음.
- 적용한 해결: origin 허용 추가.
- 재발 방지 자동화: 없음
- 영향 앱: 먹맵
- 증거: mukmap 8ad4aa1

### F13. Unity WebGL을 Play에 올리는 방법
- 적용한 해결: Android WebView + WebViewAssetLoader 래퍼.
- 증거: `LIB/library/game/unity-webgl-to-google-play-via-webview-asset-loader-wrapper.md`

### F14. 업로드 서명 키·버전 코드
- 적용한 해결: 키스토어는 레포 밖 보관, 제출마다 versionCode 증가.
- 영향 앱: 한개국어(c2af086), 운빨, 뚝카이로, 나사톡톡(2d5586c)
- 증거: 위 커밋

---

## G. 공통 원칙 (재발 방지)

### G1. 제출 전 정책 사전검사 스크립트를 통과시킨다
- 검사 항목: 런처 이름·아이콘 = 스토어 이름·아이콘, 방침에 앱 이름·패키지·개발자 포함, 스토어 빌드에 토스 문구 없음.
- 자동화: `VC/defense-game/tools/store_precheck.mjs`, `tools/ocr_vision.swift`
- 증거: `LIB/decisions/_global/process/store-submit-needs-automated-policy-precheck-icon-name-policy-no-toss-and-no-swap-during-review.md`, defense-game 21d1f30

### G2. 외부 승인 대기 중에 출시 체크리스트를 미리 채운다
- 증거: `LIB/decisions/_global/process/prepare-full-release-checklist-while-waiting-on-external-approval.md`

### G3. 토스 게임 등급은 Play·App Store 중 먼저 공개된 쪽에서 가져온다
- 증거: `LIB/decisions/_global/process/toss-game-rating-from-play-or-app-store-whichever-public-first-and-just-submit-dont-explain.md`
- 자동화: `SC/ait_game_rating.py`

---

# 이미 있는 제출 자동화 스크립트 목록

`SC` = ~/.claude/skills/chrome-direct/scenarios

- `SC/apple_appid_asc_create.sh` — App ID 등록, 갱신 약관 동의, ASC 앱 레코드 생성.
- `SC/apple_siwa_setup.py` — Sign in with Apple 설정.
- `SC/asc_store_listing.py` (`.sh`) — TestFlight, IAP, 스토어 등록정보, 스크린샷, 빌드 연결, 개인정보 라벨.
- `SC/asc_privacy.sh` — 앱 개인정보(영양 표시) 라벨 입력·게시.
- `SC/asc_submit_review.sh` — 심사 제출(가격 스케줄·IAP 포함).
- `SC/asc_resubmit.sh` — 거절 후 "심사 업데이트" 클릭 → 앱 심사에 다시 제출.
- `SC/asc_review_reply.sh` — 심사 답신·첨부.
- `SC/asc_dsa_trader.sh` — EU DSA 트레이더 선언.
- `SC/play_app_create.py` — Play 앱 생성.
- `SC/play_dev_status.py` — Play 개발자 계정 상태·한국 추가 정보 확인.
- `SC/play_iap_create.py` — Play 인앱상품 생성.
- `SC/play_iap_bulk.py` — Play 인앱상품 일괄 처리, korea-info.
- `SC/play_release.py` — status / sha1 / managed / submit / upload.
- `SC/play_listing_default_lang.py` — 기본 등록정보 언어 설정.
- `SC/play_listing_translations.py` — 등록정보 번역 입력.
- `SC/play_privacy_url.py` — 개인정보처리방침 URL 입력.
- `SC/ait_game_rating.py` 외 `ait_*` — 토스(앱인토스) 쪽 등급·등록(스토어 아님).
- `~/.config/forge-survivor/asc_api.py` — ASC API(JWT) 호출 헬퍼.
- `~/.config/forge-survivor/ios_upload.sh` — 전용 키체인으로 서명·업로드.
- `VC/defense-game/tools/store_precheck.mjs` — 스토어 정책 사전검사.
- `VC/defense-game/tools/ocr_vision.swift` — 스크린샷 OCR(문구 검사).
- `VC/threads-unfollow/scripts/asc_meta.py` — ASC 메타데이터·스크린샷·제출.
- `VC/eodimeok/native/store/asc_setup.py` — 어디먹 ASC 설정.
- `VC/spot-difference/tools/store_images.py`, `release.sh` — 스토어 이미지·릴리스.
- `~/.claude/skills/apps-in-toss-release-kit/scripts/store_images.py` — 스토어 이미지 생성.
- `VC/cat-petting/art/store/build_store.py`, `validate_store.py` — 스토어 이미지 생성·검증.
- 목록 표: `~/.claude/skills/chrome-direct/SKILL.md` 75~124행.
