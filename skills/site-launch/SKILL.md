---
name: site-launch
description: 새 웹사이트를 GA4·구글 서치콘솔·네이버 서치어드바이저·IndexNow에 사용자 손 안 대고 등록한다(서비스 계정 + 실제 Chrome 조작 + 보안문자만 텔레그램). "GA 붙여", "GA 속성 만들어", "서치콘솔 등록", "네이버 서치어드바이저", "검색 등록", "SEO 등록", "사이트맵 제출", "색인 요청" 등에 반드시 사용. 사용자에게 gcloud 로그인이나 직접 등록을 시키지 않는다.
---

# site-launch

등록이 끝나면 `seo-geo-audit` 스킬로 점검한다(FAIL 0까지).

사용자에게 시키지 말고 끝까지 직접 한다. 사람이 하는 건 네이버 보안문자 답장(텔레그램) 하나뿐.

스크립트: `~/.config/claude-accounts/personal/skills/site-launch/scripts/`

## 1. GA4 속성 + 측정 ID
```
python3 ga_property.py "<속성 이름>" https://site [--dry-run]
```
- 마지막 줄 `MEASUREMENT_ID G-XXXX`. 같은 이름 속성이 있으면 ID만 출력.
- GA 웹 화면을 Chrome 'Profile 1'(remin1994, 계정 Kangraemin 관리자)로 조작한다. 국가 대한민국·원화·업종(`GA_INDUSTRY` env, 기본 '도서 및 문학')·목표 2개·웹 스트림.
- 다른 경로는 막혀 있다: 서비스 계정은 GA 뷰어라 속성 생성 403, `gcloud auth application-default login --scopes=analytics.edit`는 구글 '차단된 앱', GA 사용자 권한 편집 패널은 서비스 계정 행에서 로딩만 돈다.
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
python3 naver_register.py verify  https://site   # 소유확인 → 보안문자 그림을 텔레그램 전송 → 답장 대기(15분) → 입력
python3 naver_register.py sitemap https://site
python3 naver_register.py rss     https://site   # RSS 피드(feed.xml) 제출
```
- 사이트 단위만 받는다(경로 붙은 주소 불가). 확인 파일 내용은 `naver-site-verification: naverXXXX.html`.
- 보안문자는 직접 풀지 않는다. 텔레그램(`CONTEST_TG_TOKEN/CHAT_ID`, ~/.claude/.env)으로 그림을 보내고, 사용자 답장을 getUpdates로 읽는다. 채팅으로 답이 오면 그 값을 쓴다.
- 네이버 로그아웃이면 `chrome-direct/scenarios/naver_login.py --qr --notify`.
- 사이트맵 칸은 전체 URL을 넣어야 확인 버튼이 켜진다.

## 4. IndexNow (네이버·빙 즉시 알림)
```
python3 indexnow.py <host> <key> <sitemap 경로|URL>
```
- 키 파일 `https://<host>/<key>.txt`(내용 = 키)를 먼저 배포. 배포 직후 api.indexnow.org는 403 → 몇 분 뒤 200.
- 배포 스크립트 끝에 붙여 매 배포마다 보낸다(예: 글쓰기공모전 `ops/vercel-deploy.sh`).

## 한글 도메인(IDN)
- 스크립트·DNS·Vercel·GSC에는 punycode(`xn--…`)를 쓴다. 네이버 서치어드바이저는 목록에 한글(`https://글쓰기공모전.kr`)로 저장한다 → naver_register.py가 xn--를 한글로 바꿔 찾는다.
- 가비아 구매: 영문명·우편번호 검색(모달은 shadow DOM이라 탭을 앞에 띄워야 그려짐)·전화번호 칸도 필수·이메일 인증번호(Gmail MCP로 읽기).
- 가비아 결제창(KCP)은 cross-origin iframe → JS 클릭 불가, 실제 마우스 클릭(CGEvent) 필요. 반복 클릭하면 모달이 겹친다. 결제 본인인증은 사용자에게 맡긴다.
- 가비아 DNS(dns.gabia.com): Vercel이면 A @ 76.76.21.21, A www 76.76.21.21. 그 뒤 `vercel domains add`·`vercel certs issue`.

## Chrome 조작 함정
- 백그라운드 탭은 Vue/Angular 화면이 안 그려진다 → `c.shot(tab, png)`로 앞으로 띄운 뒤 읽는다.
- 누른 뒤 alert가 뜨는 버튼은 `run_js("setTimeout(()=>btn.click(),10)")`로 눌러 AppleScript가 막히지 않게.
- GA 생성 화면 주소는 `#/a<계정>p<아무 속성>/admin/property/create` (속성 ID 없으면 안 그려짐). mat-checkbox는 내부 `input.mdc-checkbox__native-control`을 click.

## 검증 상태 (2026-10-19, geulmagam.vercel.app)
- gsc_register verify / naver_register add / ga_property(기존 감지·--dry-run) / indexnow: 스크립트로 실행 확인.
- naver verify·sitemap: 스크립트로 성공(2026-10-19, 글쓰기공모전.kr). ga_property 실제 생성: 손으로만 성공, 스크립트 형태는 아직 실행 전.
