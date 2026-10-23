---
name: site-launch
description: 새 웹사이트를 GA4·구글 서치콘솔·네이버 서치어드바이저·빙 웹마스터·다음 웹마스터도구·IndexNow·애드센스에 사용자 손 안 대고 등록한다(서비스 계정 + 실제 Chrome 조작 + 보안문자는 Claude가 그림을 읽어 직접 입력). "GA 붙여", "GA 속성 만들어", "서치콘솔 등록", "네이버 서치어드바이저", "빙 등록", "Bing Webmaster", "다음 검색 등록", "Daum 웹마스터", "검색 등록", "SEO 등록", "사이트맵 제출", "색인 요청", "광고 붙여", "애드센스", "광고 달아", "ads.txt", "애드센스 심사" 등에 반드시 사용. 사용자에게 gcloud 로그인이나 직접 등록을 시키지 않는다.
---

# site-launch

등록이 끝나면 `seo-geo-audit` 스킬로 점검한다(FAIL 0까지).

사용자에게 시키지 말고 끝까지 직접 한다. 보안문자도 Claude가 직접 푼다(사용자 10/23 "너가 풀 수 있잖아, 왜 내가 풀어줘야 해").

스크립트: `~/.config/claude-accounts/personal/skills/site-launch/scripts/`

## 1. GA4 속성 + 측정 ID
```
python3 ga_property.py "<속성 이름>" https://site [--dry-run]
```
- 마지막 줄 `MEASUREMENT_ID G-XXXX`. 같은 이름 속성이 있으면 ID만 출력.
- GA 웹 화면을 Chrome 'Profile 1'(remin1994, 계정 Kangraemin 관리자)로 조작한다. 국가 대한민국·원화·업종(`GA_INDUSTRY` env, 기본 '도서 및 문학')·목표 2개·웹 스트림.
- 다른 경로는 막혀 있다: 서비스 계정은 GA 뷰어라 속성 생성 403, `gcloud auth application-default login --scopes=analytics.edit`는 구글 '차단된 앱', GA 사용자 권한 편집 패널은 서비스 계정 행에서 로딩만 돈다.
- 업종 값은 화면 이름 그대로(앞부분 일치): 음식 사이트는 `GA_INDUSTRY=식음료`('음식'은 NF). 목표 체크박스는 aria-label이 비어 있어 부모 글자(트래픽 파악·참여 발생)로 찾는다(2026-10-19 mukmap 성공).
- 다른 프로젝트 측정 ID 재사용 금지(데이터 섞임). 사이트 전용 속성을 만든다.
- 맞춤 측정기준·이벤트 설정은 서비스 계정 API로 가능(기존 속성에 edit 허용된 범위).

## 2. 구글 서치콘솔 (로그인 불필요)
```
python3 gsc_register.py token  https://site/     # meta 출력 → <head>에 넣고 배포
python3 gsc_register.py verify https://site/ [sitemap.xml]
```
- 서비스 계정이 소유자로 인증하고 remin1994·kangaiai1994를 소유자로 추가 → 사람 콘솔에도 보인다. 사이트 추가·사이트맵 제출까지.
- 처음 한 번 `gcloud services enable siteverification.googleapis.com searchconsole.googleapis.com --project ai-paper-analytics` (이미 켜짐).

## 3. 네이버 서치어드바이저
```
python3 naver_register.py add     https://site   # FILE/FILE_CONTENT/META 출력 → 둘 다 사이트에 넣고 배포
python3 naver_register.py verify  https://site   # 소유확인 → 보안문자 cap.png 저장 → Claude가 Read로 읽고 answer.txt에 씀 → 입력
python3 naver_register.py sitemap https://site
python3 naver_register.py rss     https://site   # RSS 피드(feed.xml) 제출
python3 naver_register.py crawl   https://site URL [URL ...]   # '웹 페이지 수집' 요청. 보안문자 없음(2026-10-22 kangraemin.github.io 39건 연속 성공). 목록 파일은 `xargs`로 넘긴다(zsh는 $var 줄바꿈을 안 쪼갬)
# 하위 경로 사이트(github.io/<repo>/)는 세 번째 인자로 경로를 꼭 준다: rss https://kangraemin.github.io oneul-kkum/feed.xml (안 주면 루트 feed.xml=다른 사이트 피드가 제출됨)
# 네이버 RSS는 RSS 2.0만 받는다(Jekyll atom.xml은 "형식이 올바르지 않습니다"). 제출마다 보안문자를 사용자에게 물으니 재시도 루프 금지, 한 번에 몰아서.
```
- 사이트 단위만 받는다(경로 붙은 주소 불가). 확인 파일 내용은 `naver-site-verification: naverXXXX.html`.
- 보안문자는 Claude가 푼다: verify를 백그라운드로 돌리고 `/tmp/site-launch/cap.png`가 새로 바뀌면 Read로 보고 글자를 `/tmp/site-launch/answer.txt`에 쓴다. 한 번만 제출(재시도 루프 금지). 틀려서 실패하면 한 번 더 돌릴 수 있고, 그래도 안 되면 그때만 사용자에게 그림을 보낸다. 텔레그램 전송은 하지 않는다(NAVER_CAPTCHA_TG=1일 때만). 사용자에게 보안문자를 묻지 않는다(2026-10-23 사용자 지시).
- 네이버 로그아웃이면 `chrome-direct/scenarios/naver_login.py --qr --notify`.
- 사이트맵 칸은 전체 URL을 넣어야 확인 버튼이 켜진다.
- 검색어·페이지별 노출 리포트: `https://searchadvisor.naver.com/console/site/report/expose?site=<urlencoded 사이트>`(요약 화면 '콘텐츠 노출/클릭 → 자세히 보기'와 같음). 검색 키워드·웹문서 TOP 30. 하루 늦게 갱신.

## 2-1. 구글 색인 생성 요청 (서치콘솔 버튼, 하루 약 10건)
```
python3 gsc_request_index.py https://host/ URL [URL ...]   # URL마다 RESULT 요청됨/이미 등록됨/할당량 초과
```
- API에 색인 요청이 없어서 Chrome 'Profile 1'로 'URL 검사 → 색인 생성 요청'을 누른다. 새 사이트에서 sitemap이 며칠째 pending일 때 허브 페이지부터 넣는다.
- 하위 경로 속성(https://host/path/)은 inspect 화면이 404 → 루트 속성으로 연다. 8건쯤에서 응답이 느려지며 '시간 초과'가 나면 할당량으로 보고 다음 날 이어 한다(2026-10-22 검증, kangraemin.github.io).

## 4. IndexNow (네이버·빙 즉시 알림)
```
python3 indexnow.py <host> <key> <sitemap 경로|URL>
```
- 키 파일 `https://<host>/<key>.txt`(내용 = 키)를 먼저 배포. 배포 직후 api.indexnow.org는 403 → 몇 분 뒤 200.
- 배포 스크립트 끝에 붙여 매 배포마다 보낸다(예: 글쓰기공모전 `ops/vercel-deploy.sh`).
- 키 파일은 32자 hex 이름으로 골라라(`ls public | sed -nE 's/^([0-9a-f]{32})\.txt$/\1/p'`). `*.txt` 첫 파일을 집으면 `ads.txt`가 키로 잡혀 422가 난다.

## 4-1. 빙 웹마스터 (API 키, 화면 조작 없음)
```
python3 bing_register.py https://site --public web/public   # BingSiteAuth.xml 생성 → 배포 → 같은 명령 다시 → 확인·sitemap 제출
```
- 키 `BING_WEBMASTER_API_KEY`(~/.claude/.env). 이미 확인·제출된 사이트는 건너뛰고 상태만 출력.
- URL 직접 제출: `POST /webmaster/api.svc/json/SubmitUrlBatch?apikey=` `{siteUrl, urlList(≤500)}`. 할당량은 `GetUrlSubmissionQuota`(2026-10-22 kangraemin.github.io 하루 10,000). 새 사이트는 sitemap 전체를 500개씩 한 번에 낸다.
- 사이트맵 제출만으론 빙이 크롤링을 안 할 수 있다 → `python3 bing_register.py https://site/path/ --submit-urls`로 sitemap 주소를 전부 직접 제출(하루 10,000건, 2026-10-23 oneul-kkum 2,836건).
- sitemap은 `SubmitFeed`로 낸다. `SubmitSitemap`은 null만 주고 목록에 안 남는다.
- 새 사이트는 sitemap만 내면 빙이 몇 주씩 안 가져간다(mukmap.kr 10/23: 홈도 미수집). `bing_daily_submit.py https://site/ --first <홈>`을 매일 크론으로 돌려 하루 한도(100)씩 직접 넣는다. 낸 주소는 `~/.cache/bing-submit/<host>.json`.
- GSC에 URL-prefix로 등록된 사이트는 웹 'Import from GSC'로 한 번에 가져올 수 있다. "Site addition unsuccessful"이 떠도 실제론 들어간다. GSC 도메인 속성(sc-domain)은 목록에 안 나와 이 스크립트로 넣는다.

## 4-2. 다음(Daum) 웹마스터도구 (카카오 로그인 불필요)
```
python3 daum_register.py pin    https://site      # PIN 발급 → '#DaumWebMasterTool:…' 줄 출력 → robots.txt 하단에 넣고 배포
python3 daum_register.py verify https://site sitemap.xml [URL ...]   # 인증 → 사이트맵 Seed 등록 → 문서 수집 요청
```
- PIN은 `~/.claude/.env`의 `DAUM_PIN_<HOST>`에 저장(출력 안 함). 루트 robots.txt를 못 고치는 하위 경로 사이트(github.io/repo)는 불가.
- 이용동의 체크박스는 /agree로 이동했다 돌아오는 구조라 `label.choice_agree`에 checked 클래스를 직접 붙인다.
- 검증: 2026-10-23 oguriworks.com pin·verify·수집요청 성공, verify 재실행(이미 인증 세션) 멱등 확인.

## 5. 애드센스 (계정 pub-4785237655148075, remin1994)
- 코드: 모든 정적 페이지 head에 `<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4785237655148075" crossorigin="anonymous"></script>`(자동 광고). 앱인토스 등 다른 빌드엔 넣지 않는다. `ads.txt`: `google.com, pub-4785237655148075, DIRECT, f08c47fec0942fa0`.
- 코드·ads.txt를 배포한 뒤 실행(사이트 추가 → 소유권 확인 → 검토 요청, 이미 있으면 남은 단계만·상태 출력, IDN 자동 punycode):
```
python3 adsense_add.py https://site [--dry-run]    # 마지막 줄 RESULT: <host> / 준비 중 / … 이면 끝. 심사는 며칠~2주
```
- 내부 흐름: `새 사이트` → `input[aria-label="웹 사이트"]` → `저장` → "코드를 삽입했습니다" 체크 → `.verify-button` → `다음` → `검토 요청`.
- 로그아웃돼 있어도 스크립트가 `chromectl.google_relogin`으로 다시 로그인한다(패스키 시트 `계속` 클릭, 지문 불필요). 사용자에게 시키지 않는다.
- 공고 모음·짧은 글 사이트는 "가치가 별로 없는 콘텐츠"로 거절된 전례(티스토리 3개)가 있다.

- 수입 확인(읽기 전용): `python3 adsense_earnings.py` → 오늘·어제·7일·이번 달 예상 수입, 잔고, 지급 단계 경고(은행 세부정보 미등록 등), 사이트별 7일. 검증 2026-10-22.
- 한 도메인에 여러 사이트가 섞이면(예: kangraemin.github.io 개인 블로그 + /oneul-kkum/) 경로별 수입은 URL 채널로 나눈다: `python3 adsense_url_channel.py <host/경로> [--dry-run]`(이미 있으면 EXISTS). 만든 시점부터 집계되고 소급되지 않는다. 화면: 보고서 > 설정(톱니) > URL 채널 관리 = `reporting/?rt=d&ol=url_channels`. 검증 2026-10-23(kangraemin.github.io/oneul-kkum 생성·재실행 EXISTS).

## 한글 도메인(IDN)
- 스크립트·DNS·Vercel·GSC에는 punycode(`xn--…`)를 쓴다. 네이버 서치어드바이저는 목록에 한글(`https://글쓰기공모전.kr`)로 저장한다 → naver_register.py가 xn--를 한글로 바꿔 찾는다.
- 가비아 구매: 영문명·우편번호 검색(모달은 shadow DOM이라 탭을 앞에 띄워야 그려짐)·전화번호 칸도 필수·이메일 인증번호(Gmail MCP로 읽기).
- 가비아 결제창(KCP)은 cross-origin iframe → JS 클릭 불가, 실제 마우스 클릭(CGEvent) 필요. 반복 클릭하면 모달이 겹친다. 결제 본인인증은 사용자에게 맡긴다.
- 가비아 DNS(dns.gabia.com): Vercel이면 A @ 76.76.21.21, A www 76.76.21.21. 그 뒤 `vercel domains add`·`vercel certs issue`.

## Chrome 조작 함정
- 구글 계정이 '로그아웃됨'이면 `c.google_relogin(tab)` 한 줄로 해결(ga_property·adsense_add에 들어 있음).
- 백그라운드 탭은 Vue/Angular 화면이 안 그려진다 → `c.shot(tab, png)`로 앞으로 띄운 뒤 읽는다.
- 누른 뒤 alert가 뜨는 버튼은 `run_js("setTimeout(()=>btn.click(),10)")`로 눌러 AppleScript가 막히지 않게.
- GA 생성 화면 주소는 `#/a<계정>p<아무 속성>/admin/property/create` (속성 ID 없으면 안 그려짐). mat-checkbox는 내부 `input.mdc-checkbox__native-control`을 click.

## 검증 상태 (2026-10-19, geulmagam.vercel.app)
- gsc_register verify / naver_register add / ga_property(기존 감지·--dry-run) / indexnow: 스크립트로 실행 확인.
- bing_register: 글쓰기공모전.kr 추가·확인·제출 성공(API로 손으로 한 것과 같은 순서), 재실행 멱등 확인.
- naver verify·sitemap: 스크립트로 성공(2026-10-19, 글쓰기공모전.kr). ga_property 실제 생성: 손으로만 성공, 스크립트 형태는 아직 실행 전.
