---
name: design-ppt
description: "Use this skill to create a branded .pptx presentation from any content source (markdown doc, PDF, existing PPT) using a named design system from getdesign.md. Trigger whenever the user mentions making/creating a PPT or slides with a specific brand design (apple, claude, stripe, notion, etc.), or when they have a document they want turned into a polished slide deck. Keywords: '디자인 PPT', 'PPT 만들어', 'slides from', 'brand PPT', 'getdesign', 'apple design ppt', '공모전 PPT'. Always use this skill when the user wants a visually designed presentation, not just any pptx task — for editing/reading existing .pptx files use the pptx skill instead."
---

# Design PPT Skill

브랜드 디자인 시스템을 적용한 .pptx 파일을 콘텐츠 문서에서 자동 생성한다.

## 워크플로우 개요

1. **디자인 시스템 획득** — `npx getdesign@latest add [brand]`로 DESIGN.md 생성
2. **콘텐츠 분석** — 입력 문서(md/pdf/pptx)에서 핵심 내용 추출
3. **슬라이드 구성 계획** — 섹션·슬라이드 목록 초안 (사용자 확인)
4. **PPT 생성** — pptxgenjs 스크립트 작성 + 실행
5. **QA** — 이미지 변환 후 시각 검수, 문제 수정

---

## Step 1: 디자인 시스템 획득

사용자가 브랜드를 지정하지 않으면 물어본다. 기본값은 `apple`.

```bash
# 프로젝트 루트에서 실행
npx getdesign@latest add [brand]
# → DESIGN.md 생성됨
```

DESIGN.md를 읽어서 다음을 파악한다:
- **색상**: primary, background, text, accent, surface 계열
- **타이포그래피**: 제목/본문 폰트 패밀리, 크기
- **특성**: 전체적인 분위기와 레이아웃 원칙

**PPT용 색상 매핑** (DESIGN.md의 실제 hex 값으로 채운다):
```
TITLE_BG     = [브랜드의 어두운/강한 배경색]
CONTENT_BG   = [브랜드의 밝은 캔버스/배경색]
PRIMARY      = [브랜드 primary/accent 색]
TEXT_DARK    = [진한 텍스트 색]
TEXT_MUTED   = [흐린 텍스트 색]
CARD_BG      = [카드/서피스 색]
```

> 폰트는 시스템에 없을 수 있다. `Calibri`(sans) / `Georgia`(serif)를 fallback으로 쓴다.
> 브랜드가 serif 계열이면 제목에 Georgia, sans 계열이면 Calibri 사용.

---

## Step 2: 콘텐츠 분석

입력 파일 타입별 처리:

```bash
# Markdown / 텍스트
cat content.md

# PDF
python -m markitdown content.pdf

# 기존 PPTX
python -m markitdown content.pptx
```

분석 시 파악할 것:
- 전체 목적/주제 (한 줄 요약)
- 주요 섹션 및 계층 구조
- 핵심 데이터/숫자 (차트로 만들 후보)
- 표/리스트 구조

---

## Step 3: 슬라이드 구성 계획

분석 결과를 바탕으로 슬라이드 목록을 작성하고 **사용자에게 확인**받는다.

```
[슬라이드 계획 예시]
1. 표지     — 서비스명 + 한 줄 정의 + 대회명
2. 문제정의  — 핵심 통계 3개 (대형 숫자 callout)
3. 경쟁 현황 — 비교 테이블
4. 솔루션   — 3개 핵심 기능 (아이콘+텍스트 그리드)
5. 기술 구조 — 스택 다이어그램 또는 텍스트 카드
6. 데이터   — 공공데이터 출처 표
7. AI 설계  — 의도→tool 매핑 (테이블)
8. 성과/지표 — 백테스트 결과 (바 차트)
9. 로드맵   — 단기/중기/장기 타임라인
10. 마무리  — 핵심 메시지 + CTA
```

슬라이드가 너무 많으면 내용을 압축하고, 너무 적으면 중요 섹션을 분리한다.
일반적으로 **8~12슬라이드**가 적당하다.

---

## Step 4: PPT 생성

### 사전 준비

```bash
npm list -g pptxgenjs || npm install -g pptxgenjs
```

### 스크립트 작성 원칙

**pptx 스킬의 `pptxgenjs.md`를 반드시 읽고 따른다** (`~/.claude/skills/pptx/pptxgenjs.md`).
핵심 주의사항:
- hex 색상에 `#` 절대 금지 (`"CC785C"` ✓, `"#CC785C"` ✗)
- shadow 옵션 재사용 금지 → `makeShadow()` 팩토리 함수 사용
- bullet은 `bullet: true` 사용, unicode `•` 금지
- 8자리 hex 금지 (opacity는 별도 `opacity` 필드로)

### 슬라이드 레이아웃 패턴

**표지 슬라이드** (TITLE_BG 배경 + 밝은 텍스트):
```
[브랜드 PRIMARY 컬러 상단 바 또는 사이드 악센트]
[서비스명 — 대형 serif/sans 제목]
[한 줄 정의 — 중간 크기]
[부제 — 날짜/대회명 — 작은 크기, muted]
```

**콘텐츠 슬라이드** (CONTENT_BG 배경):
- 좌상단: 섹션 레이블 (소형, PRIMARY 컬러, 대문자)
- 상단: 슬라이드 제목 (중-대형)
- 본문: 레이아웃에 따라 — 2컬럼 / 카드 그리드 / 테이블 / 차트

**통계 callout 슬라이드**:
```
[큰 숫자 72pt PRIMARY 색]
[단위/레이블 18pt]
[설명 14pt muted]
```

**차트 슬라이드**:
- `chartColors`를 브랜드 PRIMARY/CARD_BG/ACCENT으로 지정
- `chartArea: { fill: { color: CONTENT_BG } }`
- 그리드선 subtle하게: `valGridLine: { color: "E5E5E5", size: 0.5 }`

### 스크립트 파일 저장 및 실행

```bash
# 저장
cat > /tmp/generate_ppt.js << 'EOF'
[생성한 스크립트]
EOF

# 실행
node /tmp/generate_ppt.js

# 출력 파일 확인
ls -la output.pptx
```

---

## Step 5: QA

### 이미지 변환 후 시각 검수

```bash
# PDF 변환
python ~/.claude/skills/pptx/scripts/office/soffice.py --headless --convert-to pdf output.pptx

# 이미지 변환
pdftoppm -jpeg -r 150 output.pdf slide
ls slide-*.jpg
```

변환된 이미지를 Read 도구로 읽어 시각 검수:
- 텍스트 잘림/오버플로우
- 색상 대비 (어두운 배경에 어두운 텍스트 금지)
- 레이아웃 일관성 (제목 위치, 여백)
- 빈 슬라이드 또는 내용 누락

### 텍스트 검수

```bash
python -m markitdown output.pptx | grep -iE "xxxx|lorem|placeholder|undefined"
```

문제 발견 시 스크립트 수정 → 재실행 → 재검수 루프.

---

## 출력

작업 완료 시:
- 생성된 `.pptx` 파일 경로 알려줌
- 슬라이드 목록 간략 요약
- 수정 요청 받을 준비 ("특정 슬라이드 바꾸고 싶으면 말해요")

---

## 빠른 참조

| 상황 | 액션 |
|------|------|
| 브랜드 미지정 | 사용자에게 물어봄 (추천: apple, claude, stripe, notion) |
| 폰트 없음 | Georgia(serif) / Calibri(sans) fallback |
| 차트 데이터 없음 | 문서에서 추출한 수치로 대체, 없으면 placeholder |
| 슬라이드 수 이견 | 8~12개 기준, 내용량에 따라 조정 |
| PDF 변환 실패 | `python ~/.claude/skills/pptx/scripts/thumbnail.py output.pptx`로 대체 |
