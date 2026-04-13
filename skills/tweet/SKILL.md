---
name: tweet
description: 오늘 커밋 내역 기반으로 build in public 트윗 초안 생성. '트윗 써줘', 'tweet', '트윗', '오늘 뭐 올리지', 'X에 올릴거' 등으로 호출. 개발 작업 후 트윗 요청 시에도 사용.
---

# /tweet

오늘의 git 커밋 내역을 보고 build in public 스타일 트윗 초안을 생성한다.

## 플로우

1. **현재 프로젝트의** 오늘 커밋만 확인 (다른 프로젝트 탐색 금지):
   ```bash
   git log --since="6am" --oneline
   ```
2. **repo URL 가져오기** (트윗 하단에 포함):
   ```bash
   git remote get-url origin
   ```
3. 커밋들을 분석해서 **오늘 작업의 전체 흐름**을 파악. 하나만 골라 요약하지 말고, 의미 있는 작업 단위들을 묶어서 스토리로 구성한다. 단, changelog처럼 전부 나열하는 건 금지.
4. 스크린샷 제안 (아래 섹션 참고)
5. 사용자에게 트윗 초안 + **한글 번역** + 스크린샷 제안을 함께 제시 — 수정 요청 시 다듬기
   - 트윗 본문은 영어로 작성하되, 바로 아래에 `> 한글 번역:` 블록으로 전체 번역을 붙인다. 사용자가 내용을 빠르게 파악할 수 있도록.

## 핵심: 사람처럼 쓰기

AI가 쓴 글은 티가 남 — 너무 깔끔하고, 구조적이고, 감정이 없다.
사람이 트위터에 쓰는 건 생각의 흐름 그대로, 약간 거칠고, 개인적이다.

### 톤 가이드

- **내용에 맞는 길이.** 할 말이 없으면 2줄, 스토리가 있으면 15줄도 OK. 억지로 줄이지 말 것. 불완전 문장도 OK.
- **구어체 자연스럽게.** "Turns out...", "TIL:", "Okay so...", "Fun fact:", "Ngl,", "Wait —"
- **삽질/놀란 점 포함.** 완벽한 척 하면 AI 냄새남. "took me way too long to figure out", "should've done this weeks ago"
- **숫자 하나면 충분.** "67 tests" or "5.5 → 8.3" — 구체적 숫자 하나가 임팩트.
- **이모지 0~1개.** 없는 게 낫고, 쓰더라도 하나만.

### 포맷

- 영어
- 280자 제한 없음 (X Premium). 보통 2~15줄. 내용이 풍부하면 길게 써도 된다 — 스토리가 있는 긴 트윗이 억지로 압축한 짧은 트윗보다 낫다.
- **구조**: 여러 항목이 있으면 "제목 + bullet" 포맷 사용:
  ```
  제목
  - 내용
  - 내용

  제목
  - 내용
  - 내용
  ```
  항목이 하나면 자유 형식 OK.
- 마지막 줄에 해시태그: `#BuildInPublic` 필수 + 관련 1개 (`#ClaudeCode`, `#DevTools` 등)
- **GitHub 링크**: remote URL이 있으면 트윗 마지막 (해시태그 바로 위)에 항상 포함. `git remote get-url origin`으로 가져온다. 추측 금지. remote가 없으면 생략.
- **복붙 가능한 포맷**: 트윗 초안은 사용자가 그대로 복사해서 X에 붙여넣을 수 있어야 한다. 코드 블록 안에서 한 문장을 여러 줄로 쪼개지 말 것 — 문단 구분(빈 줄)만 실제 줄바꿈이고, 한 문장/문단 안에서는 자연스러운 한 줄로 쓴다. X가 알아서 줄을 감싸므로, 보기 좋게 쪼갤 필요 없다.

### 하지 말 것

- "I'm excited to announce..." / "Thrilled to share..." — 공식 발표 톤
- "Here's what I learned today:" — 뻔한 도입
- 커밋 전체 나열하는 changelog 스타일
- "🚀🔥💡🎉" 이모지 도배
- "Thread 🧵" — 단일 트윗임
- 모든 문장이 같은 길이로 정렬된 깔끔한 구조
- "implemented", "leveraged", "utilized" — 이력서 단어

### 좋은 예시

Before/Problem/Fix 포맷 (여러 항목일 때 기본):
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

제목 + bullet 포맷 (짧은 항목 여러 개):
```
Write e2e tests
- found 6 real bugs just by writing them
- 50 → 67 total

Delete unused agents
- 3 planner agents doing literally nothing
- Claude handles planning directly

Auto-cleanup installer
- stale files were silently breaking hooks
- source is truth now

#BuildInPublic #ClaudeCode
```

단일 항목 (자유 형식):
```
TIL Claude Code can bypass Write/Edit blocks
through Bash heredoc. Sneaky.

Had to add a 2nd defense layer with git diff.
#BuildInPublic
```

```
Removed 3 files today. Wrote 0 new ones.
Best kind of day.
#BuildInPublic
```

```
Okay so my hook wasn't checking for empty folder names.
Entire validation chain was getting skipped silently.

Fixed in 4 lines.
#BuildInPublic #DevTools
```

스토리텔링형 (긴 트윗):
```
Swore at my LLM out of frustration and somehow
got a noticeably better answer.

No way that's real. So I went and read every paper
I could find on this.

Turns out there's a 2025 study where rude prompts
hit 84.8% vs polite at 80.8%. Google's Sergey Brin
even said on stage "all models do better if you
threaten them with physical violence."

So Wharton ran a proper experiment. 9 prompts
including "I'll punch you" and "$1 trillion tip."
5 models. 25 runs per question.

Result: no consistent improvement.
The reason rude prompts sometimes work is boring —
they're just shorter and more direct.
Polite fluff actually distracts the model.

Don't swear at your AI. Just stop being wordy.

#BuildInPublic #LLM
```

### 나쁜 예시 (이렇게 절대 쓰지 말 것)

```
Today I implemented an automated cleanup mechanism
for the agent file management system, ensuring
stale files are properly removed during updates.
#BuildInPublic #AI #DevTools #Coding #SoftwareEngineering
```
→ 왜 나쁜가: "implemented", "mechanism", "ensuring" — 이력서/보도자료 톤. 해시태그 5개. 사람이 이렇게 안 씀.

```
🚀 Exciting update! Just shipped a major improvement
to my AI workflow enforcer. Quality scores improved
significantly. Check it out! 💪
#BuildInPublic #AI #DevTools
```
→ 왜 나쁜가: "Exciting update!", "Just shipped", "Check it out!" — LinkedIn 광고 톤. 이모지 2개. 구체적 숫자 없음.

## 변경 동기와 개선점

트윗에 "뭘 했다"만 쓰면 changelog랑 다를 바 없다. 사람들이 궁금한 건 **왜 바꿨는지**, **뭐가 나아졌는지**다.

- **before → after**: 이전에 뭐가 불편/불가능했고, 지금은 어떻게 됐는지
- **계기**: 버그 리포트, 직접 쓰다 짜증난 점, 유저 피드백 등
- **숫자로 개선 표현**: "3s → 0.2s", "5 steps → 1 command", "0 → 67 tests"

커밋 메시지만 보면 "what"만 보이지만, 대화 컨텍스트에서 "why"를 찾아서 넣어야 한다. 대화에서 사용자가 불만을 표현하거나, 문제를 설명하거나, 비교한 부분을 찾아 트윗에 녹인다.

## 스크린샷 제안

트윗에 이미지가 있으면 engagement가 확연히 다르다. 트윗 초안과 함께 어떤 스크린샷을 찍으면 좋을지 구체적으로 제안한다.

### 좋은 스크린샷

- **before/after 비교**: 변경 전후를 나란히 보여주는 게 가장 강력
- **실제 동작 화면**: 새 기능이 실행되는 모습 (UI 변경, 터미널 출력 등)
- **코드 diff**: 핵심 변경이 몇 줄인 경우, 짧은 diff가 임팩트 있음
- **에러 → 성공**: 고친 버그의 에러 메시지 + 수정 후 정상 동작

### 제안 형식

트윗 초안 아래에 이렇게 제시:

```
📸 스크린샷 제안:
- [앱 화면] Claude Inspector에서 토큰 팝오버 클릭한 모습 — 비용 계산이 한눈에 보이는 컷
- [비교] 이전 버전(숫자만) vs 새 버전(단가×수량 계산 표시)
```

구체적으로 **어디서 뭘 캡처하라**고 알려줘야 한다. "앱 스크린샷" 같은 모호한 제안은 쓸모없다.

## 범위

`/tweet`을 호출한 프로젝트(현재 작업 디렉토리)의 커밋만 본다. 다른 프로젝트 디렉토리를 탐색하지 않는다.

## 커밋 없는 날

커밋이 없으면 "오늘 커밋 없음" 알려주고, 그래도 올리고 싶으면:
- 최근 작업 기반 회고/인사이트
- 개발 중 발견한 것
- 쓰고 있는 도구에 대한 짧은 생각
