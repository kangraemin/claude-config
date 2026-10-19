---
name: seo-geo-audit
description: 배포된 웹사이트의 SEO(구글·네이버)와 GEO(ChatGPT·Perplexity·Claude 등 생성형 AI 인용) 상태를 자동 점검하고 빠진 항목을 고친다. "SEO 점검", "GEO", "검색 최적화 검증", "AI 검색 노출", "AEO", "llms.txt", "구조화 데이터 확인", "og:image", "색인 안 됨", "검색에 안 나와" 등에 사용. 등록(GA·서치콘솔·서치어드바이저 제출)은 site-launch 스킬.
---

# seo-geo-audit

점검은 스크립트로, 수정은 사이트 코드에서, 등록·제출은 `site-launch` 스킬로 한다.

## 1. 자동 점검 (먼저 돌린다)
```
python3 ~/.claude/skills/seo-geo-audit/scripts/audit.py https://site [--max 300] [--json]
```
- 배포 주소를 자바스크립트 없이(크롤러 시점) 읽는다. sitemap의 URL을 `--max`개까지 전부 본다.
- FAIL = 고쳐야 함(종료 코드 1). WARN = 권장. 같은 종류는 묶어서 `[N곳, 예: URL]`로 보여 준다.
- 고친 뒤 배포하고 다시 돌려 FAIL 0을 확인한다.

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
- [ ] URL 검사 API로 색인 상태 확인: 서비스 계정 `searchconsole.googleapis.com/v1/urlInspection/index:inspect` — "Discovered - currently not indexed"는 새 도메인 초기에 정상, 며칠 뒤 다시 본다

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

### GEO (생성형 AI 인용) — Princeton GEO 논문(KDD'24) + geo-lint 규칙 요약
- [ ] `/llms.txt`: 사이트 한 줄 소개, 기준 시각, 주요 목록 링크, 데이터 파일 링크
- [ ] 질문형 소제목(`~은?`) + 바로 아래 첫 문장에 직답(40~80단어) — AI가 이 문장을 그대로 인용
- [ ] 수치·통계·출처를 넣는다(인용·통계·출처 추가가 노출을 최대 30~40% 올림). 키워드 반복은 효과 없음
- [ ] 엔티티(사이트명·브랜드·지역)를 본문에 명시, 한 문단만 떼어 읽어도 뜻이 통하게(대명사로 시작 금지)
- [ ] 비교 내용은 표, 절차는 번호 목록, 긴 글은 요약(TL;DR)·FAQ
- [ ] 신선도: "YYYY년 M월 D일 기준"·dateModified·RSS, 1년 넘은 연도 표기 정리
- [ ] 요약을 AI가 만들었으면 "원문 확인" 안내와 원문 링크(신뢰 신호)

## 3. 참고한 오픈소스·자료
- geo-lint (IJONIS, MIT, GEO 36개 규칙): https://github.com/IJONIS/geo-lint — 마크다운 콘텐츠용 린터. 규칙 목록 `docs/rules.md`
- Awesome Open GEO (라이선스 확인된 무료 GEO 도구 목록): https://github.com/cloudapp-dev/awesome-open-geo
- GEO 논문 arXiv:2311.09735 (인용·인용구·통계 추가가 가장 효과적, 키워드 스터핑은 효과 없음)
- SEOnaut(Go, 자체 호스팅 크롤러), Lighthouse SEO 감사 — 대규모 사이트 정밀 점검용
- 구글 기본 검색 노출 체크리스트: https://developers.google.com/search/docs/basics/basic-search-visibility-checklist.pdf

## 적용 사례
- 글쓰기공모전.kr (2026-10-19): FAIL 0. og:image·파비콘·RSS(+네이버 RSS 제출)·홈/장르 FAQ+FAQPage 추가. 코드: `글쓰기공모전/web/scripts/prerender.mjs`
