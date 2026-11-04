---
name: seo-geo-audit
description: 배포된 웹사이트의 SEO(구글·네이버)와 GEO(ChatGPT·Perplexity·Claude 등 생성형 AI 인용) 상태를 자동 점검하고 빠진 항목을 고친다. "SEO 점검", "GEO", "검색 최적화 검증", "AI 검색 노출", "AEO", "llms.txt", "구조화 데이터 확인", "og:image", "색인 안 됨", "검색에 안 나와" 등에 사용. 등록(GA·서치콘솔·서치어드바이저 제출)은 site-launch 스킬.
---

# seo-geo-audit

점검은 스크립트로, 수정은 사이트 코드에서, 등록·제출은 `site-launch` 스킬로 한다.

## 1. 자동 점검 (먼저 돌린다)
```
python3 ~/.claude/skills/seo-geo-audit/scripts/audit.py https://site [--max 300] [--seed N] [--json]
```
- 배포 주소를 자바스크립트 없이(크롤러 시점) 읽는다. sitemap이 `--max`보다 크면 무작위로 뽑아 본다(앞쪽만 보지 않는다).
- FAIL = 고쳐야 함(종료 코드 1). WARN = 권장. INFO = 참고. 같은 종류는 묶어서 `[N곳, 예: URL]`로 보여 준다.
- 고친 뒤 배포하고 다시 돌려 FAIL 0을 확인한다.
- 보는 것: robots, 검색·AI 봇 이름으로 실제 요청한 응답(맥 IP라 진짜 봇 IP 대우까지 증명하지는 못함), sitemap(색인 파일 펼침·lastmod), soft 404, www, canonical·title·description·og·lang·h1·구조화 데이터, hreflang(자기 참조·언어 코드·서로 가리킴·대상 상태·noindex 대상), 사이트 전체 noindex 경보, 구역별 본문 측정(전체·고유 글자·고유 문장), 본문 똑같은 페이지, 90% 이상 겹치는 페이지.
- 본문 측정값과 90%는 우리가 정한 참고 값이다. 구글 기준이 아니다.

## 1-1. 구글 색인 실제 상태
"검색에 안 나와"면 추측하지 말고 이 순서로 본다.
```
python3 ~/.claude/skills/seo-geo-audit/scripts/gsc_trend.py https://site/       # 날짜별 노출, 7일 대 7일, 빠진 구역·페이지, 순위 변화
python3 ~/.claude/skills/seo-geo-audit/scripts/index_sample.py https://site [--n 100]   # sitemap 무작위 표본의 색인 비율, 전체 추정 범위, 구역별 상태
python3 ~/.claude/skills/seo-geo-audit/scripts/inspect_index.py https://site/ [URL ...]  # 특정 주소 확인
```
- 노출이 줄었는데 평균 순위가 그대로면 순위 하락보다 페이지 탈락을 먼저 의심한다.
- `inspect_index.py`를 주소 없이 돌리면 sitemap 앞 5개만 본다. 사이트 전체 판단은 `index_sample.py`로 한다.
- URL 검사 한도는 사이트당 하루 2,000건, 분당 600건(공식).
- 서비스 계정이 소유자가 아니면 site-launch의 `gsc_register.py verify`로 먼저 등록한다.

### 상태별 대응
- `URL is unknown`: sitemap 제출과 내부 링크를 확인한다.
- `Discovered - currently not indexed`: 공식 설명은 구글이 사이트 부담을 우려해 크롤링을 미룬 경우다. 새 도메인은 며칠 뒤 다시 본다. 오래가면 응답 속도와 URL 수를 본다.
- `Crawled - currently not indexed`: 공식 설명은 흔한 상태이고 꼭 문제는 아니다. 구글은 원인과 기준을 공개하지 않는다.
  1. 먼저 비율을 잰다. 소수면 그대로 둔다.
  2. 많으면 구역별로 나누고, 색인된 쪽과 안 된 쪽의 본문을 비교한다(`index_sample.py`).
  3. 그 페이지만의 내용을 더하거나, 더할 내용이 없는 페이지는 noindex와 sitemap 제외로 뺀다.
  4. 내용이 안 바뀐 페이지를 다시 요청하지 않는다. 다시 요청은 크게 바뀌었는데 일주일 넘게 안 읽힌 페이지에만 쓴다.
- 글자 수로 자르지 않는다. 구글 기준이 없고, 2,353자 페이지도 빠졌다(먹맵, 11/4).

### 쓰면 안 되는 것
- 구글 Indexing API를 일반 페이지에 쓰지 않는다. 공식 허용은 JobPosting과 BroadcastEvent뿐이다(google-indexing-script 방식 금지).
- 오픈소스 점수표의 수치(글자 수 하한, 키워드 밀도, 인용 134~167단어, `+527%`)를 기준으로 삼지 않는다. 출처가 없다.

## 보고 규칙
- 보고서의 모든 수치·주장은 raw 출력(스크립트·curl 결과)에 남은 것만 쓴다. `site:` 검색 결과처럼 기록이 없는 건 "확인 안 됨"으로 적는다.
- 확인 못 한 것(서치콘솔 오류 리포트, Bing 색인 상태(등록 여부는 audit.py가 봄), 실제 AI 인용 여부, Core Web Vitals)은 따로 "확인 못 함" 칸에 모은다.
- 우선순위: FAIL → 색인·신선도 → 메타·구조화 데이터 → GEO 콘텐츠.

## 2. 체크리스트 (스크립트가 못 보는 것 포함)

### 크롤링·색인
- [ ] robots.txt 200, `Sitemap:` 줄, 검색봇·AI봇(GPTBot·OAI-SearchBot·ChatGPT-User·ClaudeBot·Claude-SearchBot·PerplexityBot·Google-Extended·Yeti(네이버)·Bingbot) 차단 없음
- [ ] sitemap.xml: 대표 호스트 URL만, 200·리다이렉트 없는 최종 주소만, lastmod
- [ ] 모든 페이지 canonical = 자기 주소, noindex 없음
- [ ] 옛 주소·www → 대표 주소 301/308 (앱 등이 읽는 데이터 파일은 예외로 둘 수 있음)
- [ ] 없는 주소는 404 또는 대표 페이지로 canonical (soft 404 방지)
- [ ] 구글 서치콘솔·네이버 서치어드바이저 소유확인 + sitemap 제출 (site-launch)
- [ ] IndexNow 키 파일 + 배포마다 전송 (네이버·빙)
- [ ] 네이버 RSS 제출 (`naver_register.py rss`)
- [ ] **Bing Webmaster Tools 등록**(ChatGPT 검색·Copilot이 Bing 색인을 쓴다) — audit.py가 Bing API로 자동 확인(미등록·미확인 = FAIL). 등록은 site-launch `bing_register.py`
- [ ] 오래된 분석 코드(UA-로 시작하는 Universal Analytics) → GA4
- [ ] 색인 상태는 1-1 순서로 확인

### 페이지 메타
- [ ] title 10~70자, 페이지마다 다름, 핵심 검색어 앞쪽 (예: "소설 공모전 2026 마감순 모음")
- [ ] meta description 40~170자, 페이지마다 다름
- [ ] og:title·og:description·og:url·og:image(1200×630 PNG, 절대 URL)·og:locale, twitter:card=summary_large_image — 네이버 점검·카톡 공유 미리보기
- [ ] 파비콘 실파일 `/favicon.ico` + apple-touch-icon (data: URI만 있으면 검색결과 파비콘 안 나옴)
- [ ] `<html lang>`, h1 1개

### 렌더링
- [ ] 자바스크립트 없이도 본문이 HTML에 있다(SSR/프리렌더). AI 크롤러 대부분은 JS를 안 돌린다
- [ ] 목록 페이지는 항목 링크가 `<a href>`로 HTML에 있다(내부 링크 2개 이상)
- [ ] 이미지 alt

### 구조화 데이터 (JSON-LD)
- [ ] WebSite(+Organization, 있으면 sameAs 2개 이상) 1곳에 `@id`로 정의하고 다른 페이지가 참조
- [ ] 목록 = CollectionPage + ItemList, 상세 = WebPage/Article/Product/Event 등 맞는 타입, BreadcrumbList
- [ ] FAQPage (구글 리치결과는 정부·의료만 노출되지만 AI 검색이 읽는다), dateModified
- [ ] 리치 결과 테스트로 한 번 눈으로 확인: https://search.google.com/test/rich-results

### GEO (생성형 AI 인용)
- 구글 공식: AI 기능에 나오려고 새 파일이나 표시를 만들 필요가 없다. 색인되고 스니펫 자격이 있어야 한다. 그래서 색인이 먼저다.
- 아래 항목은 근거 수준이 다르다. 논문 실험 결과나 경험칙이고, 구글·AI 회사의 보장이 아니다.
- 측정은 질문 묶음을 정해 같은 조건으로 반복한다. 한 번 물어본 결과로 판단하지 않는다.
- ChatGPT 검색 노출 봇은 OAI-SearchBot이고 GPTBot은 학습용이다. 둘을 따로 본다.
- [ ] `/llms.txt`(효과 근거 없음, 있으면 좋은 정도라 audit.py에서도 INFO): 사이트 한 줄 소개, 기준 시각, 주요 목록 링크, 데이터 파일 링크
- [ ] 질문형 소제목(`~은?`) + 바로 아래 첫 문장에 직답(40~80단어) — AI가 이 문장을 그대로 인용
- [ ] 수치·통계·출처를 넣는다(인용·통계·출처 추가가 노출을 최대 30~40% 올림). 키워드 반복은 효과 없음
- [ ] 엔티티(사이트명·브랜드·지역)를 본문에 명시, 한 문단만 떼어 읽어도 뜻이 통하게(대명사로 시작 금지)
- [ ] 브랜드명이 흔하면(다른 사이트가 선점) title·본문 앞쪽에 한국어 롱테일 설명을 붙인다
- [ ] 비교 내용은 표, 절차는 번호 목록, 긴 글은 요약(TL;DR)·FAQ
- [ ] 신선도: "YYYY년 M월 D일 기준"·dateModified·RSS, 1년 넘은 연도 표기 정리
- [ ] 요약을 AI가 만들었으면 "원문 확인" 안내와 원문 링크(신뢰 신호)

## 3. 참고한 오픈소스·자료
- geo-lint (IJONIS, MIT, GEO 36개 규칙): https://github.com/IJONIS/geo-lint — 마크다운 콘텐츠용 린터. 규칙 목록 `docs/rules.md`
- Awesome Open GEO (라이선스 확인된 무료 GEO 도구 목록): https://github.com/cloudapp-dev/awesome-open-geo
- GEO 논문 arXiv:2311.09735 (인용·인용구·통계 추가가 가장 효과적, 키워드 스터핑은 효과 없음)
- SEOnaut(Go, 자체 호스팅 크롤러), Lighthouse SEO 감사 — 대규모 사이트 정밀 점검용
- 구글 기본 검색 노출 체크리스트: https://developers.google.com/search/docs/basics/basic-search-visibility-checklist.pdf

## 3-1. 오픈소스 조사 (2026-11-04, 14개)
- 전체 정리: https://claude.ai/artifact/NjhnSKedCXgBT3JXe3mmja
- 큰 사이트 정밀 크롤링이 필요하면 siteone-crawler(Rust, MIT)가 가장 낫다. `--upload`는 외부로 보내니 쓰지 않는다.
- seonaut는 제목 길이를 바이트로 재서 한국어가 오탐한다. LibreCrawl은 300단어 기준이라 한국어가 얇다고 나온다.
- 쓰지 않는다: open-seo-mcp-skills(권한을 외부 업체 서버로 넘김), google-indexing-script의 publish(공식 허용 밖).

## 적용 사례
- 글쓰기공모전.kr (2026-10-19): FAIL 0. og:image·파비콘·RSS(+네이버 RSS 제출)·홈/장르 FAQ+FAQPage 추가. 코드: `글쓰기공모전/web/scripts/prerender.mjs`
- 오늘꿈해몽 kangraemin.github.io/oneul-kkum (2026-10-22): FAIL·WARN 0. og.png·favicon·apple-touch-icon(assets/web 복사), 구조화 데이터 없는 페이지에 WebPage 자동, sitemap lastmod를 날짜·데이터 커밋일로, RSS(날짜별 운세)·llms.txt·홈 질문형 FAQ. 코드: `next-product/scripts/build-web.mjs`
