---
name: library-lint
description: Library 건강 체크. 오래된 항목, 관련 태그 양방향 깨짐, index 미등록, 카운트 불일치, 크로스레퍼런스 제안, 고아 파일을 점검한다. 'library 점검', 'library lint', '라이브러리 정리', 'library 건강 체크' 요청 시 트리거.
---

# Library Lint

## 실행 전 체크

아래 명령을 실행한다:
```bash
LOCK=~/.claude/.claude-library/.lint-lock
if [ -f "$LOCK" ]; then
  age=$(( $(date +%s) - $(date -r "$LOCK" +%s) ))
  if [ $age -lt 86400 ]; then
    echo "24시간 이내 실행됨 ($(date -r "$LOCK")). 스킵."
    exit 0
  fi
fi
date > "$LOCK"
```
- 24시간 이내면 → 즉시 종료
- 아니면 현재 시각 기록 후 진행
- 완료 후: `rm -f "$LOCK"`

---

`~/.claude/.claude-library/library/` 의 건강 상태를 점검하고 문제를 수정한다.

**6개 체크 항목을 반드시 전부 수행한다. 하나라도 건너뛰면 안 된다.**

---

## Step 1 — 관련 태그 양방향 검증 ✅

모든 `index.md`에서 `관련:` 태그를 파싱한다.
A→B가 있으면 B→A도 있어야 한다. 깨진 것은 확인 없이 바로 수정한다.

완료 기준: 양방향 깨진 태그 0개

---

## Step 2 — index.md 파일 목록 검증 ✅

각 주제 폴더 내 `.md` 파일(index.md 제외)을 `index.md`의 `지식 목록`과 비교한다.
미등록 파일이 있으면 index.md 지식 목록에 추가한다.

**포맷 규칙**: 반드시 아래 형식으로 추가한다.
```
- [filename.md](filename.md) — 한 줄 설명
```
- ✅ `- [hook-input-stdin.md](hook-input-stdin.md) — Claude Code hook input은 stdin JSON`
- ❌ `- [Claude Code hook은 stdin으로 입력받는다](hook-input-stdin.md) — ...` (링크 텍스트에 파일명이 아닌 제목 금지)

완료 기준: 미등록 파일 0개

---

## Step 2.5 — index.md 포맷 오류 수정 ✅

모든 `index.md`의 `지식 목록` 항목을 스캔한다.
링크 텍스트가 파일명(`.md` 포함)이 아닌 human-readable 제목인 항목을 찾아 수정한다.

패턴: `- [제목이 들어간 텍스트](filename.md) — 설명`  
→ `- [filename.md](filename.md) — 설명` 으로 교체

MCP 서버가 `[filename.md](path) — description` 포맷만 파싱하므로, 링크 텍스트가 파일명이 아니면 `library_search`에서 description이 빠져 검색이 안 된다.

완료 기준: 잘못된 포맷 항목 0개

---

## Step 3 — LIBRARY.md 정리 및 누락 항목 추가 ✅

두 가지를 한 번에 처리한다.

### 3-1. 잘못된 항목 제거
LIBRARY.md에서 아래 두 종류를 찾아 삭제한다:
- `— —` (설명 없는 항목) — 카테고리 index.md가 잘못 추가된 것
- `index.md`를 가리키는 항목 — 카테고리 디렉토리 index는 LIBRARY.md에 올라오면 안 됨

### 3-2. 누락 항목 추가
LIBRARY.md에 아직 없는 **개별 지식 파일**(non-index `.md`)을 찾아 추가한다.
포맷:
```
- [제목](library/카테고리/.../filename.md) — 한 줄 요약
```
여기서 `제목`은 파일 내 `# 제목` 헤더에서 가져온다. 없으면 파일명에서 추출한다.

완료 기준: `— —` 항목 0개, index.md 링크 0개, 누락 파일 0개

---

## Step 4 — 고아 파일 ✅

어떤 `index.md`에도 등록되지 않은 `.md` 파일을 찾아 해당 index.md에 추가한다.

완료 기준: 고아 파일 0개

---

## Step 5 — durability 태그 자동 추가 ✅

`durability` 태그가 없는 파일을 모두 찾는다. **각 파일의 내용을 직접 읽고** 파일별로 판단해서 태그를 붙인다. 키워드 카운팅으로 처리하지 않는다.

판단 기준 (파일 내용을 읽고 종합적으로 판단):
- `durability: temporal` — 특정 라이브러리 버전/API 동작에 의존, 버그 우회법, 설치 방법, OAuth/토큰 발급 방식 등 라이브러리 업데이트나 정책 변경으로 무효화될 가능성이 높은 것
- `durability: permanent` — 설계 원칙, 아키텍처 패턴, 데이터 구조나 알고리즘의 근본 동작, 언어/플랫폼 레벨 특성, 반복 가능한 함정처럼 시간이 지나도 유효할 가능성이 높은 것
- 애매한 경우 `permanent`로 판단한다

파일 frontmatter의 `- 날짜:` 줄 바로 다음에 `- durability: temporal` 또는 `- durability: permanent` 를 추가한다.
`durability: temporal`이면서 날짜가 3개월+ 된 것은 별도로 보고한다 (삭제는 하지 않음).

완료 기준: durability 태그 없는 파일 0개

---

## Step 6 — 크로스레퍼런스 자동 적용 ✅

모든 주제의 index.md를 읽는다. 태그가 없는 주제뿐 아니라 **전체 주제를 대상**으로 연결 가능한 쌍을 찾는다. **index.md 내용을 직접 읽고** 판단한다.

판단 기준:
- 같은 기술 스택이나 도메인에서 함께 참조할 만한 주제
- 한쪽의 함정/패턴이 다른 쪽에서도 적용되는 경우
- 이미 한쪽에 관련: 태그가 있어도 반대쪽에 없으면 추가한다 (양방향 보장)
- 연결이 억지스럽거나 단지 같은 카테고리라는 이유만이면 추가하지 않는다

양방향으로 index.md에 `관련:` 태그를 추가한다. 사용자에게 묻지 않는다.

완료 기준: 연결 가능한 주제 쌍에 양방향 태그 추가됨, 추가한 연결 목록 보고

---

## 실행 순서

Step 1 → 2 → 2.5 → 3 → 4 → 5 → 6 순서로 진행한다.
각 Step이 완료된 후 다음 Step으로 넘어간다. **Step 5, 6을 생략하면 안 된다.**

자동 수정(1~4) 완료 후:
- `CHANGELOG.md`에 수정 사항 append
- `git commit & push`

그 다음 Step 5, 6 결과를 사용자에게 보고한다.

---

## 최종 출력 형식

보고 전에 아래 체크리스트를 반드시 완성한다. N 자리에 실제 숫자를 채워야 한다. 0이어도 괜찮지만 비워두면 안 된다.

```
## 실행 체크리스트
- [x] Step 1 — 양방향 태그 깨진 것: N개 수정
- [x] Step 2 — index.md 미등록 파일: N개 추가
- [x] Step 2.5 — index.md 포맷 오류(human-readable 제목): N개 수정
- [x] Step 3 — LIBRARY.md `— —` 제거: N개 / index.md 링크 제거: N개 / 누락 파일 추가: N개
- [x] Step 4 — 고아 파일: N개 처리
- [x] Step 5 — 오래된 항목(temporal, 3개월+): N개 / durability 태그 없는 파일: N개
- [x] Step 6 — 크로스레퍼런스 제안: N쌍

🔧 자동 수정 (Step 1~4):
- [항목] 설명

⚠️ 수동 확인 필요 (Step 5~6):
- [오래된 항목] ...
- [크로스레퍼런스 제안] ...

📊 통계:
- 전체 주제: N개
- 전체 지식 파일: N개
```
