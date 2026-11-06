---
name: app-logging
description: 앱·게임·토스 미니앱·웹에 GA4 이벤트 로깅과 크래시 기록(Firebase Crashlytics)을 넣고, 제대로 들어갔는지 숫자로 확인한다. "로깅 넣어", "로깅 최대한 많이", "GA 넣어/붙여", "이벤트 추가", "이벤트 설계", "트래킹", "크래시", "크래쉬리틱스", "Crashlytics", "Firebase", "앱 플랫폼 구분", "안드인지 iOS인지 토스인지", "로깅 잘 돼있나", "출시 전 점검", 스토어(플레이스토어·앱스토어) 업데이트 준비 같은 말이 나오면 코드를 열기 전에 반드시 이 스킬부터 쓴다. GA 데이터를 읽고 분석만 할 땐 ga-analyze, GA 속성 새로 만들기는 site-launch.
---

# 앱 로깅 · 크래시 기록

## 왜 이 스킬이 있나
- 2026-11-06~07 점검에서 앱마다 로깅 수준이 제각각이었다.
  - 나사톡톡·러너스하이는 분석이 없었다.
  - 대부분 웹 스트림 하나라 토스·웹·안드로이드·iOS를 주소(hostName)로만 겨우 갈랐다.
  - 크래시 기록(Crashlytics)은 디펜스 게임 하나뿐이었다.
- 사용자 지시(11/6~7): "로깅 최대한 많이 남기라그래", "안드인지 iOS인지 토스인지 웹인지 다 되어있나".
- GA를 직접 쓴다. GTM은 태그를 대신 붙여 주는 관리 도구일 뿐이고 앱에선 한 단계만 늘어난다(사용자 11/7 질문에 이렇게 답함).

## 순서
1. **지금 상태부터 잰다.**
   - `python3 ~/.claude/skills/app-logging/scripts/ga_check.py` → 속성 목록.
   - `python3 ~/.claude/skills/app-logging/scripts/ga_check.py <속성ID|이름>` → 스트림·맞춤 측정기준·이벤트 종류·플랫폼별 사용자·실시간.
   - 코드에서 기존 호출을 찾는다: `grep -rnE "gtag|logEvent|Analytics\.log|track\(|/g/collect|Crashlytics" src app lib Assets --include=*.{ts,tsx,js,cs,kt,swift}`.
   - 문서(`docs/EVENTS.md` 등)에 적힌 것과 GA 실제 값이 다르면 GA를 믿는다. 11/7 스레드언팔은 문서엔 app_platform 측정기준이 있다고 했지만 GA엔 없었다.
2. **이벤트 기록표를 쓴다.** `docs/EVENTS.md`에 이름·언제·파라미터·코드 위치. 아래 '무엇을 남기나'를 빠짐없이 채운다.
3. **한 파일로 보낸다.** `src/analytics.ts`(또는 `Analytics.cs`)의 `track(name, params)` 하나만 쓴다. 화면 코드에서 gtag·logEvent를 직접 부르지 않는다.
4. **플랫폼을 붙인다(필수).** 아래 'app_platform'.
5. **크래시 기록을 넣는다(스토어 빌드).** 아래 'Crashlytics'.
6. **확인한다.** 테스트 빌드를 열어 `ga_check.py <속성> ` 실시간 칸에 이벤트가 뜨는지 본다. 웹은 GA DebugView, 앱은 `adb shell setprop debug.firebase.analytics.app <패키지>`.
7. **보고한다.** 속성 ID, 이벤트 종류 수(전→후), 실시간 확인 결과, 크래시 테스트 결과.

## 무엇을 남기나 (최대한 많이)
- 앱 열기: `app_open`(첫 실행 여부, 방문 횟수, 유입 referrer·utm, 첫 화면 그리는 데 걸린 ms).
- 화면: `screen_view`(screen, prev_screen, 앞 화면 머문 ms). 앱 가려짐·돌아옴 `app_hide`·`app_resume`(머문 ms).
- 버튼: 누를 수 있는 건 다 `*_click`(button, placement). 뒤로가기도(via: system/toss_back/android_back).
- 단계와 걸린 시간: 시작·성공·실패를 짝으로 (`upload_start`/`analysis_success`/`analysis_fail`, `level_start`/`level_complete`/`level_fail`), duration_ms 포함.
- 실패는 이유와 함께: `*_fail`(reason, code, message 앞 100자). 잡힌 오류 `js_error`·`handled_error`.
- 광고: `ad_request`·`ad_loaded`·`ad_show`·`ad_reward`·`ad_fail`(placement, reason). 요청 대비 실패가 같으면(11/7 눈썰미 7/7) 광고 ID·그룹부터 의심.
- 결제: `iap_view`·`iap_start`·`purchase`(GA 추천 이름)·`iap_fail`·`iap_restore`·`iap_recover_fail`.
- 설정 바꾸기, 공유(`share`), 가입(`sign_up`), 로그인(`login`), 튜토리얼(`tutorial_begin`/`tutorial_complete`), 레벨(`level_up`), 재화(`earn_virtual_currency`/`spend_virtual_currency`).
- GA 추천 이름이 있으면 그 이름을 쓴다. 보고서가 알아서 묶어 준다.

## 이름 규칙 (오픈소스 스킬 공통)
- 소문자 snake_case, `대상_동작`(object_action), 지난 일은 과거형(`level_completed`보다 GA 추천 이름이 있으면 그쪽).
- 화면 글자(버튼 문구)를 이름에 넣지 않는다. 종류는 파라미터로(`home_click` + button=start).
- 파라미터 끝말: `_id`, `_count`, `_ms`, `is_`, `has_`.
- GA 한도: 이벤트 이름 500종, 이벤트당 파라미터 25개, 사용자 속성 25개, 이름 40자, 값 100자.
- 개인정보(이름·전화·이메일·파일 내용·아이디) 금지. 사람 수, ms, 화면·버튼 이름만.
- 같은 이벤트를 두 번 보내지 않는다(SDK 자동 수집 `screen_view`·`first_open`과 겹치는지 확인).

## app_platform (토스·웹·안드로이드·iOS 구분)
- 값: `toss` / `web` / `android` / `ios`. 판정은 실행 환경으로 한다(토스 SDK 존재, Capacitor `getPlatform()`, Unity `Application.platform`).
- 모든 이벤트의 **이벤트 파라미터**와 **사용자 속성**에 둘 다 붙인다.
- GA 맞춤 측정기준으로 등록한다: '앱 플랫폼'(이벤트 범위, app_platform)과 '앱 플랫폼 사용자'(사용자 범위). 등록 안 하면 보고서에서 못 쓴다.
  - `python3 ~/.claude/skills/site-launch/scripts/ga_custom_dims.py <속성ID> [이름:매개변수:event|user ...]` (GA 화면 조작, 멱등, tmux -L gh 에서).
  - 표시 이름에 괄호를 쓰면 저장이 안 된다.
- 확인용 Playwright 는 모바일 user_agent 를 준다. HeadlessChrome UA 는 GA가 봇으로 걸러 실시간에 안 뜬다.
- `build`(release/test)도 붙여 테스트 배포 기록을 걸러 낸다.
- 개발 서버·localhost에서는 보내지 않는다. 단 스토어 앱 웹뷰 주소도 localhost라 앱은 주소로 거르지 않는다.

## 속성과 아침 리포트
- 앱마다 GA 속성을 따로 만든다(다른 앱 측정 ID 재사용 금지). 만들기는 `site-launch` 스킬 `ga_property.py`.
- 스토어 앱은 Firebase 프로젝트를 GA 속성에 연결하고 안드로이드·iOS 스트림을 둔다. `google-services.json`·`GoogleService-Info.plist`를 먼저 넣고 코드를 쓴다.
- 서비스 계정 `ai-paper-analytics-sa.json`에 그 속성 뷰어 권한을 준다. 그러면 아침 리포트(`~/.claude/scripts/ga_daily_report.py`)가 속성을 알아서 읽는다(최근 30일 포함). `ga_check.py` 목록에 안 나오면 권한이 없는 것이다.
- 분석 키가 없어도 빌드·실행은 돼야 한다. 디버그 빌드는 크게 알리고, 출시 빌드는 조용히 넘어간다.

## Crashlytics (스토어 빌드)
- 안드로이드·iOS 스토어 빌드엔 넣는다. 토스 미니앱·웹은 Crashlytics가 없으니 `js_error`(message, stack 앞부분, screen) 이벤트와 `window.onerror`·`unhandledrejection`으로 대신한다.
- 넣을 것: 사용자 id(익명 키), custom key(screen, app_platform, build, 앱 버전), 로그(직전 화면·버튼), 잡힌 오류는 non-fatal로 기록.
- 기호 파일을 올린다: 안드로이드 mapping(R8/ProGuard), Unity 네이티브 심볼(`FirebaseCrashlytics.UploadSymbols` / Gradle `uploadCrashlyticsSymbolFile`), iOS dSYM. 안 올리면 크래시 위치가 안 읽힌다.
- 확인: 테스트 빌드에서 일부러 크래시(`FirebaseCrashlytics.getInstance()` 테스트 크래시)를 내고 콘솔에 뜨는지 본다.
- 예: Capacitor는 `@capacitor-firebase/crashlytics`(디펜스 게임에 들어 있음), Unity는 Firebase Unity SDK.

## 스토어 심사 중이면
- 심사 중인 빌드는 바꾸지 않는다. 로깅은 승인 뒤 첫 업데이트에 넣는다(사용자 11/7, 나사톡톡 세션).
- 토스·웹 빌드는 지금 넣고 테스트 배포한다.

## 다른 세션에 시킬 때
- 그 앱 세션에 이 스킬 경로(`~/.claude/skills/app-logging/SKILL.md`)를 주고 "이 순서대로, 결과로 속성 ID·이벤트 종류 수·실시간 확인을 보내라"고 한다.
- 꺼져 있으면 `python3 ~/.claude/skills/reboot-reconnect/scripts/open_session.py <앱>`으로 켠다.

## 참고
- 오픈소스 출처와 가져온 규칙: `references/sources.md`.
