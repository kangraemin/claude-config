---
description: 프로젝트의 기존 실험 결과, 분석 파일, 백테스트 결론을 ~/.claude/.claude-library/library/로 마이그레이션. '기존 실험 결과 library에 넣어줘', '분석 파일 정리해줘', 'library로 옮겨줘', '과거 실험 지식 저장', 'migrate to library' 등의 요청 시 반드시 이 스킬을 사용. 지식이 쌓여있는 프로젝트에서 처음 library를 세팅할 때도 사용.
---

# /migrate-to-library

프로젝트의 기존 지식을 global library로 체계적으로 마이그레이션한다.
library는 카테고리 → 주제 → 지식 파일 계층으로 구성된다.

## 준비

1. `~/.claude/.claude-library/GUIDE.md` 읽기 (구조/형식 파악)
2. `~/.claude/.claude-library/LIBRARY.md` 읽기 (이미 있는 항목 파악)
3. 현재 프로젝트 파악

## 1단계: 지식 소스 스캔

프로젝트에서 탐색:
- `analysis/INDEX.md` 또는 `docs/analysis/INDEX.md`
- `hypothesis/*/conclusion.md`
- `analysis/backtest/*.md`, `docs/analysis/*.md`
- 프로젝트 루트 `*.md`

스캔 후 요약:
```
📂 발견된 지식 소스:
- analysis/INDEX.md: 32개 항목
- hypothesis/: 8개 폴더
총 X개 파일 검토 예정
```

## 2단계: 카테고리/주제 분류

각 항목을 읽고 카테고리와 주제를 판단:

**카테고리 예시**: equity, crypto, ml, macro, claude

**주제**: 구체적인 개념 (fibonacci-retracement, lgbm, indicator-timing 등)

**포함 기준**: 기록할 가치가 있는 지식. 미결이어도 괜찮음.
**제외 기준**: 단순 수치 나열, 기록 가치 없는 중간 과정

분류 결과를 사용자에게 보여주고 확인:
```
✅ library 추가 예정 (X개):
[equity/fibonacci-retracement] 피보나치 되돌림
[equity/indicator-timing] 지표 기반 타이밍
[ml/lgbm] LightGBM 예측 모델
...

⏭️ 스킵 (Y개):
- 단순 파라미터 그리드 수치 나열

계속할까요?
```

## 3단계: 배치 처리 (5~10개씩)

각 배치:
1. 분석 파일 실제로 읽어 내용 파악
2. 주제 폴더 구조 결정
3. 미리보기 후 확인:

```
📝 미리보기:

[1] library/equity/fibonacci-retracement/
    index.md — 요약
    backtest.md — 2026-03-08 실험 내용

[2] library/equity/indicator-timing/
    index.md — 85.5K건 실험 내용

추가할까요? [Y/n/수정]
```

## 4단계: 파일 생성

확인된 항목:
1. `library/[카테고리]/[주제]/` 폴더 생성
2. `index.md` 생성 (GUIDE.md 형식)
3. 지식 파일 생성 (내용 설명하는 이름, 날짜 없음)
4. `LIBRARY.md` 카테고리별 업데이트
5. 배치 완료 후 즉시 commit/push:
   ```
   git -C ~/.claude/.claude-library add -A
   git -C ~/.claude/.claude-library commit -m "feat: [프로젝트] migration - [카테고리] 추가"
   git -C ~/.claude/.claude-library push
   ```
6. 알림: `📚 library에 추가: [경로]`

## 5단계: 완료 리포트

```
✅ 마이그레이션 완료

추가됨: X개 주제
스킵됨: Y개
이미 있음: Z개

library 현황:
  equity/ — A개 주제
  crypto/ — B개 주제
  ml/ — C개 주제
```

## 주의사항
- 이미 같은 주제 폴더가 있으면 index.md 업데이트 + 파일 추가
- 파일명에 날짜 붙이지 않는다
- 억지로 결론 내리지 않는다. 아는 것만 써라
