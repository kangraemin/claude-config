# 읽은 글·스킬 (2026-10-21)

## 글 (WebFetch로 실제로 읽음)
- https://claude.com/resources/articles/improving-frontend-design-through-skills — Anthropic. '분포 수렴'으로 Inter·보라 그라디언트·밋밋한 배경에 몰린다. 굵기 100/200 대 800/900, 크기 차이 3배 이상, 주 색 하나에 날카로운 강조 하나, 동작은 한 순간에 몰기.
- https://www.thefountaininstitute.com/blog/signs-vibe-coded-ui — 바이브코딩 UI 신호 7가지: 우선순위 없는 네온 색, 장식용 빛번짐, 이모지 아이콘, 보라 그라디언트, 카드 안 카드, 블록마다 다른 색 옆탭, 의미 없는 상태 점. 처방: 색은 페이지 공용 자원, 강조 쓸 곳을 정해 두고 거기만.
- https://prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-Website — Tailwind indigo-500 기본값이 원인. 가운데 히어로+아이콘 박스 3개, 모든 곳에 둥근 모서리·옅은 그림자. 레퍼런스 2~3개 모아 무엇이 좋은지 말로 적고 시작.
- https://www.superdesign.dev/blog/why-ai-design-looks-generic — 취향·탐색·구현 명세를 한 프롬프트에 섞지 말 것. 방향을 먼저 고정하고 DESIGN.md 토큰으로 묶는다. "더 깔끔하게" 같은 형용사 피드백은 실패 신호.
- https://noqta.tn/en/blog/ai-design-slop-overused-ui-patterns-fix-2026 — 모든 요소에 같은 큰 radius, 의미 없는 그라디언트, 넓은 자간 eyebrow, 가짜 Live 배지, 한쪽 두꺼운 색 테두리. radius는 카드 6px 같은 절제된 토큰.
- https://ice-ice-bear.github.io/ko/posts/2026-04-15-vibe-coding-design/ — (한국어) AI 티 벗기기 3원칙: 먼저 전부 지우기(모노톤·아이콘 제거 후 필요한 것만), 같은 카테고리 실서비스 레퍼런스(쿠팡·무신사·Claude), 방문자 목적 하나에 맞춰 배치.
- https://forum.cursor.com/t/i-built-a-free-tool-that-scores-how-ai-generated-your-app-looks/154796 — 'Vibe Score' 도구. Inter, 보라 그라디언트, 대칭 히어로, 모든 곳 shadow-lg. 강조색은 한 번의 큰 순간에 몰기.
- https://www.justinwetch.com/blog/improvingclaudefrontend — frontend-design 스킬 비판: 한 번의 생성 안에서 실행 못 하는 규칙, 형용사뿐인 지시, '피하라'만 있고 '대신 이렇게'가 없음. 금지마다 대안을 짝지어 쓴다.
- https://github.com/Laith0003/ux-skill/wiki/How-to-detect-AI-slop-in-your-design — 12/14/16/18/24/30/36/48… Tailwind 기본 크기 사다리 자체가 신호. 본문 굵기 600 금지, 브랜드색은 1~2곳(로고·주 버튼), 3곳 넘으면 신호. 둥근 숫자 가짜 통계(10x, 99.9%) 금지. 터치 44px.
- https://github.com/Laith0003/ux-skill/wiki/How-to-design-a-dashboard-with-Claude-Code — 대시보드 실패 6가지: 숫자 하나마다 카드, 같은 크기 KPI 3개, 표 숫자 tabular-nums 안 씀, 상태색에 그라디언트, 빈·로딩·오류 상태 없음, 모든 곳 Live 표시(화면당 2개까지).
- https://askcodi.substack.com/p/the-ai-ui-problem-nobody-talks-about — 긴 프롬프트·시스템 프롬프트로는 안 고쳐짐. 무엇을 넣고 무엇을 넣지 말지 적은 '구속력 있는 UI 명세'가 효과.
- https://21st.dev/blog/website-not-look-ai-generated — 로고 가리기 테스트: 문구가 경쟁사에도 맞으면 AI 티. 실제 화면·실제 사진·실제 숫자·이름·날짜. 기능 설명은 고르지 않게(강한 것·약한 것).
- https://superdesign.dev/blog/fix-generic-ai-landing-page — 매드립 헤드라인, 가운데 히어로+그라디언트, 같은 카드 3개, 기본 팔레트, 판에 박힌 섹션 순서. 한 번에 한 섹션씩 고친다(다시 뽑기 금지).
- https://www.eleken.co/blog-posts/ai-dashboard-design — AI 대시보드는 지표·차트 과다. "바빠 보이면 하나 뺀다". 맥락(목표·이유) 없이 숫자만 두지 않는다.
- https://www.oppadu.com/tools/design-systems-site/brand/toss.html — (비공식 정리) 토스: 강조 Toss Blue 하나, 한 화면 Primary 액션 하나, 그림자 거의 없음, 4px 단위, 본문 Pretendard 500 이상, 크기 단계 정해진 8개 중 화면엔 소수만.
- https://toss.im/tossfeed/article/uxwriter-interview — 토스 UX 라이팅 '잡초 뽑기'(뜻에 영향 없는 단어 빼기), 바텀시트 제목 한 줄, Zero Jargon.

## 검색 요약으로만 본 것
- 토스 'One Thing per Screen'(한 화면 한 판단) — 2차 기사 기준, 공식 원문 미확인.
- 당근 SEED: 주황 브랜드색 유지 + 라임 포인트(https://designcompass.org/2026/07/27/daangn-seed-design-system-rebranding/). 색 사용량 규칙은 공식 확인 안 됨.

## 오픈소스 스킬 (원문 읽음, 사본은 oss/)
| 스킬 | URL | 라이선스 | 가져온 규칙 |
|---|---|---|---|
| anthropics/skills frontend-design | https://github.com/anthropics/skills/tree/main/skills/frontend-design | Apache-2.0 | 제목 속 한 단어만 색·기울임 강조 금지, 대문자 라벨·eyebrow 금지, 01/02/03 번호는 순서가 정보일 때만, 2026 AI 군집(크림+테라코타 #D97757, 검정+형광 강조, 신문풍 헤어라인, SaaS 카드 키트, 'A · B · C' 가운뎃점 메타). 로컬 ~/.claude/skills/frontend-design 과 본문 동일이라 사본 안 둠 |
| Leonxlnx/taste-skill (tasteskill v2) | https://github.com/Leonxlnx/taste-skill | MIT | 크기 5개가 천장·눈에 보이는 일은 2~3개, 그라디언트·쉬는 그림자·이모지·eyebrow·작은 대문자 라벨 금지, 강조색은 주 행동 + 하나, 본문은 진한 잉크(회색 본문 금지), 카드 행 금지, 데이터는 합이 맞게·비교 기준 명시. 247개 사이트 통계(아이콘 카드 상위 1% vs 하위 28% 등) |
| pbakaus/impeccable | https://github.com/pbakaus/impeccable | Apache-2.0 | craft-floor 금지 목록(같은 크기 아이콘 카드, 히어로 지표 템플릿, 2px 넘는 한쪽 색 테두리, 스파크라인·진행 링이 내용 대신), distill(색 1~2+중립, 크기 3~4개, 굵기 2~3개, 문장 반으로 두 번), quieter(채도 70~85%, 900→600) |
| gabelul/pixelslop | https://cdn.jsdelivr.net/npm/pixelslop@0.3.8/dist/skill/resources/ai-slop-patterns.md | Apache-2.0 | 패턴 26개 측정 규칙(히어로 지표 24px+ 숫자 2개, 같은 카드 그리드, 카드 6개 넘게 감싸기, 같은 간격만 쓰기) — 검사 스크립트 기준값 참고 |
| Laith0003/ux-skill | https://github.com/Laith0003/ux-skill | MIT | 152개 규칙 린터. 위 wiki 2편의 수치 규칙(브랜드색 3곳 초과, Tailwind 크기 사다리, 가짜 둥근 숫자) |
| 로컬 gstack design-review | ~/.claude/skills/design-review/SKILL.md | — | AI Slop 블랙리스트 11개(아이콘 원형 3열, 다 가운데 정렬, 장식 블롭, 왼쪽 색 테두리…). 이 스킬은 그쪽과 겹치지 않게 '숫자 검사 + 한국 모바일 + 덜어내기 순서 + 사용자 전후 비교'에 집중 |
