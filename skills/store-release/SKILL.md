---
name: store-release
description: 앱스토어(App Store Connect)·플레이스토어(Google Play Console) 제출·심사·반려 대응·재제출·TestFlight·IARC 등급까지 스토어 배포 전 과정. "스토어 제출", "앱스토어 올려", "플레이 올려", "심사", "반려", "리젝", "재제출", "TestFlight", "IARC", "판매 국가", "연령 등급", "IAP 심사", "스토어 배포" 같은 말이 나오면 화면을 열거나 스크립트를 새로 짜기 전에 반드시 이 스킬부터 연다. 지금까지 겪은 이슈 50여 개와 해결책, 오픈소스 asc CLI 사용법이 들어 있다.
---

# 스토어 배포·심사

## 왜 이 스킬이 있나
- 10~11월 스토어 제출에서 같은 함정을 여러 세션이 따로 밟았다(토스 문구 5.6 반려, 가격·판매국 누락, 키체인 창, IAP 미첨부 등).
- 겪은 이슈와 해결책 전부: `references/issues.md`(증상별 A~G). 막히면 증상 단어로 먼저 grep한다.
- 오픈소스 비교와 채택 이유: `references/oss.md`. 결론은 아래 '도구'.

## 도구 (오픈소스 먼저, 없는 것만 자체)
- **App Store 조회·점검·메타데이터·제출: `asc`**(rorkai/App-Store-Connect-CLI, 별 8천+). `scripts/asc.sh <명령>`이 ~/.claude/.env의 ASC 키로 실행한다. 키 값은 출력하지 않는다.
  - `asc.sh apps list` · `builds list --app ID` · `review status --app ID` · `validate --app ID`
  - `pricing availability ...`(판매국) · `age-rating view|audit|edit` · `localizations` · `screenshots` · `review submit` · `reviews respond`
  - 처음 쓰는 명령은 `asc.sh <명령> --help`부터. 쓰기 명령은 `--dry-run`이 있으면 먼저 돌린다.
- **서명·빌드·TestFlight·Play AAB 업로드: fastlane**(이미 있는 Fastfile). iOS 업로드는 키체인 창 회피판(issues D1·D2).
- **Chrome 시나리오는 API가 없는 것만**: `~/.claude/skills/chrome-direct/scenarios/`
  - App Store: `asc_privacy.sh`(개인정보 라벨, API 없음), `asc_dsa_trader.sh`(EU DSA), `asc_review_reply.sh`(Resolution Center 회신, API 공개 안 됨).
  - Play 콘솔 전부: `play_release.py`, `play_privacy_url.py`, `play_listing_*.py`, `play_iap_*.py`, `play_app_create.py`, `play_dev_status.py`. Play는 asc 같은 대체재가 없다(서비스 계정 키도 없음).
  - `asc_submit_review.sh`·`asc_resubmit.sh`·`asc_store_listing.*`는 asc로 대체된다. 새로 쓰지 말고 asc를 쓴다.

## 순서
1. **스토어판 점검(우리 것)**: 빌드·스토어 문구에 토스·다른 플랫폼 이름이 없는지, 런처 이름·아이콘이 스토어와 같은지, 개인정보처리방침에 앱 이름이 있는지.
   - 기준 구현: `~/programming/vibecoding/defense-game/tools/store_precheck.mjs`(BANNED `/토스(?!트)|\bToss\b|itch\.io/`). 다른 앱은 이걸 복사해 STORE 값만 바꾼다.
   - 토스 전용 기능(토스에서 열기·토스 로그인·토스 광고)은 스토어 빌드에서 코드로 꺼진다(issues A1, 반려 5.6).
2. **빌드·업로드**: fastlane / ios_upload. 빌드 번호는 매번 올린다(E3). 디스크 15GB 아래면 `disk-cleanup` 먼저(D6).
3. **메타데이터**: 가격(무료) · **판매국 전체** · 연령 등급 · 스크린샷(iPad 13인치 포함) · 개인정보 라벨 · 첫 IAP는 버전에 붙여 함께.
4. **제출 전 점검(필수)**: `bash ~/.claude/skills/store-release/scripts/validate_all.sh [앱ID...]` → `RESULT: OK`여야 제출한다.
   - 보류 4개(과학기록·AI-Tycoon·러너스하이·한개국어)는 자동으로 뺀다.
   - 심사 대기 상태의 `version.state.editable`, socialMediaAgeRestricted 오탐(C19)은 스크립트가 걸러 낸다.
   - 경고 `iap.review_readiness`(IAP가 READY_TO_SUBMIT)는 반려·재제출 때 그 버전에 IAP를 붙여 같이 낸다(C5·C12).
5. **제출**: `asc.sh review submit` (안 되면 issues C11 409 참고).
6. **반려**: Resolution Center 원문을 먼저 읽고 issues A·B에서 같은 번호를 찾는다. 심사 중 빌드 교체 금지(A4).
7. **출시 뒤**: 스토어 공개 주소가 200이면 토스 게임은 그 주소로 앱인토스 자체 등급을 넣고 검토 요청(IARC 메일은 안내일 뿐, 할 일 없음).

## 11/10 실측
- 8개 앱 중 7개가 판매국 0이었다 → 전체 175개국으로 넣음(C18). 승인돼도 어디에도 안 나올 뻔했다.
- `validate_all.sh` 결과 오류 0, 경고: 키워드가 앱 이름·부제와 겹침, IAP 미제출(골골냥 10·눈썰미 3·뚝카이로 3), 골골냥 2.0.0 새 기능 문구 비어 있음.

## 하지 않는 것
- 키체인 암호 입력, .env·sns.env 값 출력.
- 심사 중 버전에 빌드 바꿔 끼우기.
- 보류 4개 앱 제출.
