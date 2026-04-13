---
name: today-papers
description: ai-paper 프로젝트에서 오늘 수집된 논문/아티클 타이틀을 source별로 한글로 출력하는 스킬. '오늘 수집된거 보여줘', '오늘 뭐 들어왔어', '타이틀 가져와', '오늘 수집된 것들' 등의 요청 시 반드시 이 스킬을 사용. ai-paper 프로젝트 디렉토리에서만 동작.
---

## 동작 방식

1. DB에서 오늘 수집된 papers 조회
2. 타이틀을 한글로 번역해서 source별로 출력

## 날짜 계산

- DB의 `collectedAt`은 UTC로 저장됨
- **항상 KST(UTC+9) 기준**으로 오늘 날짜를 구한다
- SQL에서 `DATE(datetime(collectedAt, '+9 hours'))` 로 KST 날짜 비교

## 실행 절차

### Step 1: 스크립트 실행

프로젝트 루트에서 아래 스크립트를 `/tmp/fetch_today_papers.ts`로 생성 후 실행:

```typescript
import * as dotenv from 'dotenv';
dotenv.config();
import { db } from './src/lib/db';
import { papers } from './src/lib/db/schema';
import { sql, desc } from 'drizzle-orm';

async function main() {
  // KST 기준 오늘 날짜
  const kstNow = new Date(Date.now() + 9 * 60 * 60 * 1000);
  const dateStr = kstNow.toISOString().slice(0, 10);

  const rows = await db.select({
    source: papers.source,
    title: papers.title,
  })
  .from(papers)
  .where(sql`DATE(datetime(${papers.collectedAt}, '+9 hours')) = ${dateStr}`)
  .orderBy(papers.source, desc(papers.collectedAt));

  console.log(JSON.stringify({ date: dateStr, rows }));
}

main().catch(console.error);
```

실행: `npx tsx /tmp/fetch_today_papers.ts` (프로젝트 루트에서)

### Step 2: 타이틀 한글 번역 후 출력

가져온 타이틀을 source별로 그룹화하고, 각 타이틀을 자연스러운 한국어로 번역해서 출력.

번역 시 원문의 기술 용어(LLM, RAG, K8s 등)는 그대로 유지하고, 문장은 자연스러운 한국어로.

## 출력 형식

```
**arxiv (N)**
- 한글 타이틀 1
- 한글 타이틀 2

**hacker_news (N)**
- 한글 타이틀 1

**reddit (N)**
- 한글 타이틀 1
```

총 건수도 마지막에 한 줄로.
