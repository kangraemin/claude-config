---
name: hn-post
description: "Hacker News 'Show HN' 포스트 초안 작성. 프로젝트를 분석해서 HN 커뮤니티 톤에 맞는 포스트를 생성한다. 'HN 글 써줘', 'Show HN', '해커뉴스 포스트', 'HN에 올릴 글', '해커뉴스에 올리자', 'hn post' 요청 시 반드시 이 스킬을 사용할 것."
---

# HN Post Generator

프로젝트를 Hacker News에 소개하는 "Show HN" 포스트 초안을 작성한다.
HN은 기술적 깊이와 솔직함을 좋아하고, 마케팅 냄새를 극도로 싫어한다.

---

## 실행 흐름

### Step 1: 프로젝트 분석

포스트를 쓰기 전에 프로젝트를 철저히 파악한다:

1. **README.md** 읽기
2. **핵심 소스 코드** 읽기 — 실제로 뭘 하는지 코드 수준에서 이해
3. **git log** — 개발 히스토리, 어떤 순서로 만들었는지
4. **기술 스택** — 언어, 프레임워크, 외부 의존성
5. **GitHub remote URL** — `git remote get-url origin`으로 실제 repo URL 추출
6. **차별점** — 비슷한 도구가 있다면 뭐가 다른지

사용자에게 물어볼 것:
- 만든 동기 (있으면 포스트가 훨씬 좋아짐)
- 특별히 강조하고 싶은 기술적 결정
- 타겟 독자 (모바일 개발자? 인프라? AI?)

### Step 2: 포스트 작성

#### 제목 규칙

HN 제목은 `Show HN:` 프리픽스 + 짧은 설명.

- 80자 이내
- 프로젝트가 뭔지 한 문장으로. 모호하면 클릭 안 함.
- 기술 키워드 포함 (검색/필터용)

좋은 예:
```
Show HN: Code Inspector MCP – Kotlin/Android code quality scoring for Claude Code
```

나쁜 예:
```
Show HN: I built an amazing tool that revolutionizes code quality checking!!!
```

#### 본문 구조

HN 본문은 plain text. 마크다운 안 먹힌다 (링크만 자동 변환).
짧고 밀도 높게. 문단 사이 빈 줄로 구분.

```
[1문단: 이게 뭔지 + 왜 만들었는지 — 2-3줄]
개인적 동기에서 시작. "I wanted X but Y didn't exist" 패턴.

[2문단: 어떻게 동작하는지 — 3-5줄]
기술적 디테일. 구체적일수록 좋다.
구현에서 흥미로운 결정이나 트레이드오프.

[3문단: 결과/현재 상태 — 1-2줄]
실제로 쓰고 있는지, 한계점은 뭔지. 솔직하게.

GitHub: [실제 repo URL]
```

#### 톤 가이드라인

`~/.claude/rules/writing-style.md`의 영어 문체를 따른다:

HN에서 먹히는 톤:
- **기술적 정밀함** — 구체적인 구현 디테일, 숫자, 트레이드오프
- **솔직함** — 한계점, 아직 안 된 것, 이상했던 것을 먼저 말하면 신뢰가 올라감
- **담담함** — 흥분하지 않음. 사실 나열.
- **"이상했다 → 알고 보니"** 구조가 자연스러움

HN에서 까이는 톤:
- "revolutionary", "game-changer", "amazing", "excited" — AI slop 냄새
- 이모지 사용
- "Please star the repo"
- 마케팅 용어, 과장
- 리스트/불릿 포인트 남용 (산문체가 HN 톤)

동사: `wrote`, `tried`, `broke`, `shipped` — `implemented`, `leveraged`, `utilized` 금지

### Step 3: 한국어 브리핑

사용자에게 전달할 때 반드시 한국어로 설명한다:

```
**포스트 전략**: [왜 이 각도로 썼는지, 어떤 점을 강조했는지]
**예상 반응**: [HN 독자들이 어떤 질문/반응을 할 수 있는지]
**주의점**: [올릴 때 조심할 것]
```

### Step 4: 최종 출력

아래 순서로 출력:

#### 4-1. 한국어 브리핑

포스트 전략, 각도 설명.

#### 4-2. Show HN 포스트 (영어)

제목과 본문을 인용 블록으로. 바로 복붙 가능하게.

#### 4-3. 포스트 번역 (한국어)

영어 포스트의 자연스러운 한국어 번역. 직역 금지.
사용자가 "내가 뭘 올리는 건지" 바로 파악할 수 있게.

---

## 자기검열

초안 생성 후 반드시 확인:

- [ ] "thrilled", "excited", "amazing", "revolutionary" 없는가?
- [ ] "implemented", "leveraged", "utilized" 없는가?
- [ ] 모든 문단 길이가 균일하지 않은가? (AI 냄새)
- [ ] GitHub URL이 실제 repo URL인가? (placeholder 금지)
- [ ] 한 번이라도 "이상했다" / "몰랐다" / "틀렸다" / 한계점이 나오는가?
- [ ] 본문이 plain text인가? (마크다운 문법 사용 안 했는가?)
- [ ] 3-4문단 이내인가?

---

## 주의사항

- HN은 제목 + URL 또는 제목 + text 포스트. 둘 다 가능하지만 Show HN은 보통 text + GitHub 링크.
- 올린 직후 첫 댓글로 추가 맥락을 다는 게 관례. 포스트 본문에 다 넣지 못한 기술적 디테일이나 로드맵.
- 올리는 시간: 미국 동부 오전 (한국 밤 10시-자정)이 트래픽 피크.
- 자기 글에 다른 계정으로 upvote하면 즉시 ban. 절대 금지.
- Show HN 가이드라인: https://news.ycombinator.com/showhn.html
