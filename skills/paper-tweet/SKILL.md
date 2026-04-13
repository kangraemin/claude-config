---
name: paper-tweet
description: 오늘 수집된 논문/HN/reddit 아티클 중 Gemini·Claude API를 쓰는 개발자에게 가장 흥미로운 것 하나를 골라 기깔나는 트윗 초안 생성. 'AI 논문 트윗', '오늘 논문 중에 트위터 올릴 거', '논문 하나 골라서 트윗 써줘', 'paper tweet', 'HN 글 트윗', '오늘 읽을만한 거 트윗으로' 등으로 호출. 이 스킬은 자기 작업이 아니라 외부 콘텐츠(논문/아티클)를 공유하는 트윗이다.
---

# /paper-tweet

오늘 수집된 논문·아티클 중 **Gemini / Claude API를 쓰는 개발자**에게 가장 실용적이거나 놀라운 것 하나를 골라 트윗 초안을 만든다.

## Step 1: 오늘 수집된 항목 가져오기

프로젝트에 `scripts/_today_for_tweet.ts`가 이미 있다. 이걸 사용한다:

```bash
TURSO_DATABASE_URL=$(grep TURSO_DATABASE_URL .env | cut -d= -f2) \
TURSO_AUTH_TOKEN=$(grep TURSO_AUTH_TOKEN .env | cut -d= -f2) \
npx tsx scripts/_today_for_tweet.ts
```

`one_liner`와 `how_to_apply` 필드도 포함돼 있어서 요약 없이도 픽 판단에 쓸 수 있다. `summarized_at IS NOT NULL` 조건이 있으므로 요약된 항목만 나온다.

## Step 2: 하나 고르기

**대상 독자**: Claude / Gemini API로 제품을 만들거나 LLM 앱을 개발하는 개발자.

이 사람들이 "오 이거 실제로 써먹겠다" 또는 "이런 게 되는구나" 하고 반응할 만한 항목을 고른다.

### 좋은 픽의 기준 (우선순위 순)

1. **바로 써먹을 수 있음** — 프롬프팅 기법, 컨텍스트 관리, 비용 절감, 속도 개선 등 구체적 기법
2. **놀라운 수치** — 기존 통념을 뒤집거나 명확한 before/after가 있는 벤치마크
3. **새 패턴/아키텍처** — RAG, 에이전트, tool use, multimodal 관련 실용 연구
4. **모델 동작의 의외성** — "이렇게 하면 안 될 줄 알았는데 됨" 류의 발견

### 피해야 할 픽

- 학계용 이론 논문 (NLP 태스크 SOTA 갱신, 수식 중심)
- 특정 도메인에만 해당하는 것 (의료영상 분류, 금융 시계열 예측 등)
- 뻔한 내용 ("LLM은 데이터가 많을수록 잘 됨")
- 제품 마케팅성 글

선택 후 **왜 이걸 골랐는지 한 줄**로 이유를 밝힌다.

## Step 3: 트윗 초안 작성

### 포맷

- **영어**로 작성, 바로 아래에 `> 한글 번역:` 블록 첨부
- 280자 제한 없음 (X Premium). 보통 5~15줄.
- 마지막 줄에 **paper-digest.app 페이지 URL** 포함: `https://paper-digest.app/en/papers/{id}` (DB의 id 필드 사용). 원본 arxiv/HN/reddit URL이 아닌 우리 서비스 링크를 건다.
- 해시태그: `#LLM` 필수 + 내용에 맞는 1개 (`#PromptEngineering`, `#AIEngineering`, `#RAG`, `#ClaudeAPI` 등) + `#BuildInPublic` 필수
- 이모지 0~1개. 없는 게 낫다.

### 톤 가이드

트윗의 화자는 **"이걸 읽고 흥미로워서 공유하는 개발자"**다. 논문 초록 번역이 아니라, 읽고 나서 슬랙에 링크 보내며 한마디 적는 느낌.

**직접 해보지 않은 내용은 체험담 어투를 쓰지 않는다:**
- ❌ "Tried this yesterday", "TIL:", "I found that", "got me", "알게 됐다"
- ✅ "according to this paper", "apparently", "~라고 한다", "~한 셈"
- 논문/아티클의 결과를 전달할 때는 출처를 자연스럽게 드러낸다: "this paper shows", "their benchmarks say"
- 단, 뉴스 앵커 톤은 여전히 금지: "study shows", "researchers found"

**허용하는 톤:**
- "Turns out... — at least according to this paper"
- "Okay so...", "Wait —"
- 핵심 수치 하나는 반드시 포함. 없으면 구체적 상황으로 대체.
- "kind of wild that", "worth looking into"
- "groundbreaking", "revolutionary", "state-of-the-art" 금지

### 구조 패턴

**발견형** (가장 많은 케이스):
```
[핵심 발견 or 반전 — 첫 줄에 결론]

[왜 이게 흥미로운지, API 개발자 입장에서]

[구체적 수치 or 기법]

[한 줄 테이크어웨이 or 한마디]

url
#LLM #태그 #BuildInPublic
```

**기법 공유형**:
```
[뭘 할 수 있게 됨]

[기존 방법 vs 이 방법]
[수치 or 구체적 차이]

[어디서 써먹을 수 있는지]

url
#LLM #태그 #BuildInPublic
```

### 좋은 예시

```
Turns out "think step by step" isn't the move anymore
— at least according to this paper.

Structured output schemas as CoT scaffolds outperform
freeform reasoning prompts by 12% on complex tasks.

Makes sense — you're giving the model *where* to put
each reasoning step, not just asking it to reason.

Worth trying in multi-hop QA pipelines.

https://...
#LLM #PromptEngineering #BuildInPublic
```

```
Okay so caching your system prompt isn't just a cost trick,
apparently.

With Claude, cached prompts get processed ~4x faster
on subsequent calls according to Anthropic's docs.

For long-context apps (legal, code review, docs) this
changes the architecture conversation.
Not "should I cache" but "what should I cache first."

https://...
#LLM #AIEngineering #BuildInPublic
```

```
Wait — RAG with no retrieval sometimes beats RAG with retrieval?

This paper says when the query is ambiguous, pulling top-k chunks
and stuffing them in context confuses the model more than helps.
They call it "context pollution."

Proposed fix: route queries first. Only retrieve when
retrieval actually helps. Sounds obvious in hindsight.

https://...
#RAG #LLM #BuildInPublic
```

### 나쁜 예시

```
New research shows that chain-of-thought prompting
significantly improves LLM performance across multiple
benchmarks, achieving state-of-the-art results.
#AI #MachineLearning #Research
```
→ 뉴스 앵커 톤. 구체성 없음. "significantly", "multiple benchmarks" — 의미없는 수식어.

## Step 4: 출력

트윗 초안 + 한글 번역 + 선택 이유를 함께 제시한다.

```
**선택**: [제목] (출처: arxiv/HN/reddit)
**이유**: [한 줄]

---

[트윗 초안]

---

> 한글 번역:
> [번역]
```

수정 요청 시 다듬는다.
