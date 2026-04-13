---
name: linkedin-post
description: 오늘 커밋 내역 기반으로 LinkedIn 포스트 초안 생성. '링크드인 써줘', 'linkedin', '링크드인', '링크드인에 올릴 글', 'LinkedIn 포스트' 등으로 호출. 개발 작업 후 LinkedIn 글쓰기 요청 시에도 반드시 이 스킬을 사용할 것.
---

# /linkedin-post

오늘의 git 커밋 내역을 보고 LinkedIn build in public 포스트 초안을 생성한다.

LinkedIn은 Twitter와 다르다. Twitter는 짧고 날것인 반면, LinkedIn은 **"이걸 만들면서 이런 걸 깨달았다"** 프레임이 핵심이다. 완성품 자랑이 아니라 과정에서 배운 인사이트를 공유하는 톤.

---

## 플로우

1. **현재 프로젝트의** 오늘 커밋만 확인 (다른 프로젝트 탐색 금지):
   ```bash
   git log --since="6am" --oneline
   ```
2. **repo URL 가져오기** (포스트 하단에 포함):
   ```bash
   git remote get-url origin
   ```
3. 커밋들을 분석해서 **오늘 작업의 전체 흐름**을 파악. 단순 나열이 아니라, 하나의 스토리나 인사이트로 묶는다.
4. **영어 버전 + 한국어 버전 두 개를 항상 모두 작성한다.** 하나만 쓰는 건 절대 금지. 사용자가 "하나만 써줘"라고 하지 않는 한 무조건 둘 다.
5. 출력 형식 (반드시 이 구조로):

   ```
   ---
   🇺🇸 English
   ---
   (영어 포스트 전문)

   ---
   🇰🇷 한국어
   ---
   (한국어 포스트 전문)
   ```

   - 영어 버전과 한국어 버전은 단순 번역이 아니라, 각 언어 독자에게 자연스러운 별도 포스트로 작성한다.
   - 두 버전 모두 코드 블록에 넣어 복붙 가능하게 제공한다.
6. 스크린샷 제안 (아래 섹션 참고)

---

## 핵심: LinkedIn 톤 잡기

LinkedIn에서 잘 먹히는 건 **"나 이거 만들었다"가 아니라 "이걸 만들면서 이걸 알게 됐다"**다. 독자가 가져갈 인사이트가 있어야 좋아요/댓글이 달린다.

### 톤 가이드

- **1인칭 스토리텔링.** "I tested...", "I spent the weekend...", "Here's what I found..."
- **의외성/반전.** "I expected X. Turns out Y." — 이 구조가 LinkedIn에서 가장 강력
- **구체적 숫자 하나.** "45 million parameter combinations", "391,650 test cases" — 숫자가 스크롤을 멈추게 함
- **겸손한 실패담.** 완벽한 성공 스토리보다 "이게 안 돼서 이렇게 바꿨다"가 더 진짜처럼 느껴짐
- **교훈으로 마무리.** "What I learned:", "Takeaway:" — 독자가 가져갈 것을 명시

### 구조

LinkedIn은 **첫 2줄이 생명**이다. "...더 보기"를 클릭하게 만드는 hook이 필요함.

```
[Hook — 숫자나 의외한 사실 1-2줄]

[배경 — 왜 이걸 하게 됐는지 2-3줄]

[과정 — 뭘 했는지, 뭘 발견했는지 3-5줄]

[인사이트/교훈 — 독자가 가져갈 것 2-3줄]

[GitHub 링크]

[해시태그]
```

줄바꿈을 많이 쓴다. LinkedIn에서는 짧은 문단(1-2줄) + 빈 줄이 가독성을 높인다. 한 문단에 3줄 이상 쓰지 않는다.

### 포맷

- 길이: 보통 8~20줄. Twitter보다 길어도 괜찮지만 에세이는 금지.
- **줄바꿈 많이.** 한 문단 1-2줄 + 빈 줄. LinkedIn 모바일에서 긴 문단은 벽처럼 보임.
- 해시태그: 포스트 맨 아래에 3-5개. `#BuildInPublic` 필수 + 관련 태그 (`#Python`, `#QuantTrading`, `#DevTools`, `#ClaudeCode` 등)
- **GitHub 링크**: remote URL이 있으면 해시태그 바로 위에 포함. `git remote get-url origin`으로 가져온다. 추측 금지.
- **복붙 가능한 포맷**: LinkedIn에 그대로 붙여넣을 수 있어야 한다. 코드 블록 안에서 작성.

### 하지 말 것 (LinkedIn 클리셰)

- "I'm excited to announce..." / "Thrilled to share..." — 가장 흔한 LinkedIn 클리셰
- "Here are 5 lessons I learned:" — 뻔한 리스트 도입
- "Agree? 👇" / "Repost if you..." — engagement bait
- 이모지 줄머리 (🔥 First... 💡 Second... 🚀 Third...) — "LinkedIn bro" 톤
- "Let me tell you a story." — 불필요한 서두
- 모든 줄이 한 단어인 시 형식 (So. I. Did. This.)
- "revolutionary", "game-changer", "paradigm shift" — 마케팅 단어

---

## AI가 쓴 것처럼 보이지 않게

AI가 쓴 글의 특징은 **완벽한 균형**이다. 모든 문단이 비슷한 길이, 모든 요점이 깔끔하게 정렬, 항상 3가지 교훈. 실제 사람이 쓴 글에는 들쭉날쭉함이 있다.

### 영어 포스트에서

- **문장 길이를 불규칙하게.** AI는 비슷한 길이의 문장을 반복한다. 아주 짧은 문장과 조금 긴 문장을 섞어라.
- **"Lesson:" / "Takeaway:" 레이블 금지.** 교훈은 그냥 마지막에 자연스럽게 흘러가게 두면 된다. 이름표 붙이지 않아도 독자는 안다.
- **완벽한 3단 구조 금지.** Hook → Background → Process → Insight 공식이 너무 뻔하면 AI 티가 난다. 배경을 아예 생략하거나, 인사이트 없이 과정만으로 끝내기도 해라.
- **불완전한 생각을 남겨라.** "I'm still not sure if this was the right call." 같은 열린 결말이 진짜처럼 느껴진다.
- **지나치게 구체적인 세부 사항.** "the 4th bug I fixed that day", "around 11pm when I almost gave up" — AI는 이런 걸 잘 안 쓴다. 너무 작은 디테일이 오히려 진짜 냄새를 낸다.
- **동사 선택.** "implemented", "utilized", "leveraged" → "wrote", "tried", "broke", "shipped". 단순하고 강한 동사.

### 한국어 포스트에서

한국어 LinkedIn은 영어 버전의 번역이 아니라, **한국 개발자가 실제로 쓰는 말투**여야 한다.

- **구어체 어미.** "~했어요", "~더라고요", "~거든요", "~더니" — 글이 아닌 말처럼 읽혀야 함.
- **AI 번역 냄새 어휘 금지**: "해당 기능", "이를 통해", "활용하여", "구현하였습니다", "적용함으로써" — 공문서 투.
- **솔직한 감정 묘사.** "솔직히 좀 허탈했어요", "뭔가 이상하다 싶었는데", "거의 포기하려다가" — AI는 이런 감정 묘사를 잘 안 한다.
- **불완전한 문장도 OK.** "근데 막상 해보니까...", "어, 이거 되네?" — 글쓰기보다 생각이 먼저 나오는 것처럼.
- **결론을 명시하지 않아도 된다.** "그래서 배운 건 ~입니다" 대신 그냥 사실 나열로 끝내도 독자가 스스로 느낀다.

### 자기검열 기준

초안을 쓰고 나서 스스로 물어봐라:
- 문단 길이가 너무 균일하지 않은가?
- "Lesson:", "Takeaway:", "Key insight:" 같은 레이블이 없는가?
- 구체적인 실패나 당혹스러운 순간이 담겨 있는가?
- 마지막 문장이 "always remember to..." 식의 교훈 요약이 아닌가?

하나라도 걸리면 다듬어라.

### 좋은 예시

Before/Problem/Fix형 (여러 개선 항목이 있을 때 기본):
```
Been building a knowledge library for AI coding agents. Had about 98 entries. Read Karpathy's LLM Wiki gist today, looked at mine again.

Before
- every entry had the same "what happened + lesson" format.

Problem
- when logging a debugging gotcha, "how to prevent it next time" was missing. When logging an experiment, "what conditions I ran it under" was missing. One template meant something important always got left out.

Fix
- 4 templates by situation. Debugging gets what-broke/why/how-fixed/prevention. Experiments get conditions/results/conclusion. Just fill in the blanks.

Before
- all entries aged the same way.

Problem
- "this flag was removed in Python 3.12" becomes wrong when the version changes, but "GPU doesn't support bf16" is true forever. Couldn't tell them apart, so cleanup meant manually checking everything.

Fix
- permanent/temporal tags. Planning to run a lint command periodically that only checks temporal entries — "is this still valid?" Permanent ones get skipped.

https://github.com/kangraemin/ai-knowledge

#BuildInPublic #ClaudeCode
```

이 포맷의 핵심:
- 뭘 바꿨는지(Fix)만 쓰면 changelog. **왜 바꿨는지(Problem)와 이전 상태(Before)를 같이 써야** 읽는 사람이 맥락을 잡음.
- Before → Problem → Fix 순서로 반복하면 여러 항목도 자연스럽게 이어짐.
- **Before/Problem/Fix 각각 줄바꿈 후 `- ` bullet으로 내용 작성.** 한 줄에 "Before: 내용" 붙이지 말 것.

인사이트형:
```
I tested 45 million parameter combinations for a trading strategy.

Not a single one consistently beat buy-and-hold.

I built a backtesting engine in Python — grid search across 10 parameters, walk-forward validation, out-of-sample testing. The works.

After weeks of running experiments, here's what the data showed: the simplest approach (just holding) wins.

It's not the answer I wanted. But it's the honest one.

Sometimes the most valuable thing you can build is proof that the complex solution isn't worth it.

https://github.com/kangraemin/stock-bot

#BuildInPublic #Python #QuantTrading #DataScience
```

과정 공유형:
```
Built a Telegram bot that sends me trading signals every morning at 6am.

11 leveraged ETFs. RSI + Bollinger Bands + EMA. Backtested across 5 years of data.

The surprising part? Writing 177 tests taught me more about the strategy than the backtest results did. Every edge case I tested exposed an assumption I hadn't questioned.

Current setup:
- Python + yfinance for data
- Oracle Cloud for hosting
- Telegram for alerts

It's not fancy. But it runs every day without me touching it.

https://github.com/kangraemin/stock-bot

#BuildInPublic #Python #TradingBot #Automation
```

실패/반전형:
```
Spent a weekend optimizing my DCA strategy with RSI-based multipliers.

3x when RSI is oversold. 2x when it's low. 1x otherwise. Sounds smart, right?

17,600 combinations. 303 walk-forward windows. Full grid search.

Result: 51% win rate. Literally a coin flip.

The fancy multiplier added zero edge over just buying the same amount every time.

Lesson: complexity doesn't equal alpha. Sometimes the boring approach is the optimal one.

#BuildInPublic #QuantFinance #Python #DataDriven
```

### 한국어 포스트 좋은 예시

```
AI 가드레일이 너무 쉽게 뚫리고 있었어요.

에러도 아니고, 경고도 아니에요. 그냥 통과시키면 안 되는 작업들을 조용히 넘기고 있었던 거예요.

ai-bouncer라는 걸 만들고 있는데요 — Claude Code가 코드 짜기 전에 반드시 계획 단계를 밟게 하는 게이트 시스템이에요.

문제는 "이 작업이 단순한가?" 판단 기준이 너무 막연했던 거더라고요.

"짧은 범위", "최소 변경" — 전부 주관적인 말이잖아요. Claude는 거의 모든 걸 단순 작업으로 보고 게이트를 그냥 건너뜀.

그래서 숫자로 다 바꿨어요. 최대 몇 파일, 최대 몇 줄, 복잡도 점수 몇 점 이하.

바꾸자마자 오탐이 뚝 줄었고요.

모호한 규칙은 규칙이 아니더라고요. AI는 "빠르게 가도 되는 해석"을 귀신같이 찾아냄.

https://github.com/kangraemin/ai-bouncer

#BuildInPublic #ClaudeCode #AIAgents #개발
```

### 나쁜 예시 (이렇게 절대 쓰지 말 것)

```
🚀 Exciting news! I'm thrilled to share that I've been working on
an incredible trading bot that leverages cutting-edge AI technology
to analyze market patterns!

Here are 5 things I learned:
🔥 1. Data is everything
💡 2. Testing matters
🎯 3. Automation saves time
💪 4. Python is powerful
🌟 5. Never give up

What do you think? Drop your thoughts below! 👇

#AI #Trading #Python #Innovation #Tech #Startup #Growth #Mindset
```
→ 왜 나쁜가: 이모지 도배, "thrilled to share", 구체적 내용 제로, 해시태그 8개, engagement bait. 전형적인 "LinkedIn bro" 포스트.

```
Today I implemented a sophisticated backtesting framework utilizing
advanced statistical methods for quantitative trading analysis.
The system leverages walk-forward optimization to validate
strategy parameters across multiple asset classes.

#QuantitativeFinance #MachineLearning #FinTech
```
→ 왜 나쁜가: 이력서 톤. "implemented", "sophisticated", "utilizing", "leverages". 사람이 아니라 보도자료 같음. 개인적 이야기 제로.

---

## 변경 동기와 개선점

트윗과 마찬가지로 "뭘 했다"만 쓰면 changelog다. LinkedIn에서는 특히 **why**가 중요:

- **before → after**: "매일 수동으로 차트 확인 → 아침 6시에 알림 자동 수신"
- **의외의 발견**: "이게 될 줄 알았는데 데이터가 정반대를 보여줬다"
- **숫자로 표현**: "391,650 combinations", "177 tests", "51% win rate"

커밋 메시지에서 "what"을 뽑고, 대화 컨텍스트에서 "why"와 "so what"을 찾아서 포스트에 녹인다.

---

## 스크린샷 제안

LinkedIn 포스트에 이미지가 있으면 engagement가 확연히 올라간다. 포스트 초안과 함께 구체적으로 제안.

### 좋은 이미지

- **결과 그래프/차트**: 백테스트 수익률 곡선, 비교 차트
- **터미널 출력**: 실행 결과가 인상적일 때
- **before/after**: 변경 전후 비교
- **아키텍처 다이어그램**: 시스템 구조가 핵심일 때

### 제안 형식

포스트 초안 아래에:
```
📸 이미지 제안:
- [차트] 45M 조합 그리드 서치 결과 히트맵 — 최적 조합이 B&H와 차이 없음을 시각적으로 보여주는 컷
- [터미널] 백테스트 실행 결과 요약 출력 화면
```

---

## 범위

`/linkedin-post`를 호출한 프로젝트(현재 작업 디렉토리)의 커밋만 본다. 다른 프로젝트 디렉토리를 탐색하지 않는다.

## 커밋 없는 날 / 소개 포스트

커밋이 없거나, 사용자가 대화 내용 기반으로 쓰고 싶다고 하면:
- 최근 작업 기반 회고/인사이트
- 프로젝트 전체를 소개하는 "I've been building..." 포스트
- 개발 중 발견한 교훈
- **첫 포스트 / 인사 글**: "앞으로 이런 글 올릴게" 스타일 — 뭘 만들고 있는지, 어떤 시행착오를 겪고 있는지, 왜 공유하려는지를 자연스럽게. "저는 앞으로 ~를 올릴 예정입니다" 같은 공식 발표 톤 금지.

커밋 없는 날도 마찬가지로 **영어 + 한국어 둘 다 작성.**
