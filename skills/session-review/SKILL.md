---
name: session-review
description: 세션에서 배울게있는지 정리하고 library에 저장. '배운 거 정리해줘', '이번 세션 정리', '세션 리뷰', 'session review', '오늘 배운 거', '이번 대화에서 건진 거' 같은 요청 시 반드시 이 스킬을 사용. 기술적 발견, 삽질 해결, API 동작, 설계 결정 등 다음에 또 쓸 만한 게 있는지 확인할 때도 트리거.
---

# Session Review

이번 세션 대화를 돌아보고 library에 저장할 가치가 있는 지식을 추출한다.

## 판단 기준

저장할 가치가 있는 것:
- 삽질로 알게 된 API/라이브러리 동작 (에러로 발견한 것, 문서에 없는 것)
- 설계 결정과 그 이유 (왜 A 대신 B를 선택했는지)
- 시도했다가 실패한 접근법과 이유
- 앞으로 같은 상황에서 다시 쓸 수 있는 패턴/인사이트

저장하지 않는 것:
- 이번 작업에만 해당하는 일회성 정보
- 코드 파일에 이미 반영된 내용
- git history에서 확인 가능한 것
- 오타/포맷 수정

**아무것도 없으면 "이번 세션에서 저장할 내용 없음"으로 끝낸다. 억지로 만들지 않는다.**

## 플로우

1. **스캔**: 이번 세션 대화 전체를 돌아보며 위 기준에 맞는 것 목록화
2. **저장**: 바로 library에 파일로 작성 (확인 없이)
3. **커밋**: git commit & push
4. **보고**: 저장한 내용 한 줄 요약으로 알림

확인 단계 없이 바로 저장한다. 사용자가 "정리해줘"라고 했으면 저장까지가 요청의 범위다.

## 저장 방법

Library 경로: `~/.claude/.claude-library/library/`

### 분류
**`~/.claude/TAXONOMY.md`를 먼저 확인한다.**

- 매칭되는 카테고리/서브카테고리가 있으면 그곳에 저장
- 없으면 TAXONOMY.md에 먼저 추가 후 저장
- ❌ 대회명, 프로젝트명, 도구명을 카테고리/서브카테고리로 사용 금지
- ✅ 기법/주제/도메인 기준으로 분류

### 파일명
- **"뭘 배웠는지"**가 파일명에 드러나야 한다
- ❌ `discovery.md`, `lessons.md` (뭔지 모름)
- ✅ `ar1-lag-is-dominant-signal.md` (교훈이 드러남)

### 파일 작성 순서
1. TAXONOMY.md 확인 — 매칭 분류 찾기, 없으면 추가
2. `~/.claude/.claude-library/library/[카테고리]/[서브카테고리]/[주제]/[파일명].md` 생성 (`source_session` 포함)
3. 주제 `index.md` 생성 또는 업데이트 + `관련:` 태그
3.5. **자동 크로스레퍼런스**: `library_search()`로 핵심 키워드 검색 → 관련 주제 발견 시 양방향 `관련:` 태그 추가
4. `~/.claude/.claude-library/LIBRARY.md` 업데이트
5. `~/.claude/CLAUDE.md` 목차에 새 주제 추가 (없으면)
5.5. **Synthesis 체크**: 같은 서브카테고리 파일 3개 이상이면 종합 문서 필요성 자문 → 필요하면 `library/synthesis/`에 작성

### 지식 파일 형식
```markdown
# [제목]

- 날짜: YYYY-MM-DD
- 출처: [세션 설명 / 경험]
- source_session: [워크로그 날짜/시간 or 세션 컨텍스트]

## 내용
핵심 내용. 구체적으로.

## 시사점
다음에 이 지식을 어떻게 쓸 수 있는지.
```

## 커밋
```bash
git -C ~/.claude/.claude-library add -A
git -C ~/.claude/.claude-library commit -m "feat: [주제] 추가"
git -C ~/.claude/.claude-library push
```

저장 후: `📚 library에 추가: [경로]` 한 줄로 알린다.
