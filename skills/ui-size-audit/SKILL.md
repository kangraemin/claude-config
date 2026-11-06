---
name: ui-size-audit
description: 화면 크기 요소(아이콘 크기·실제 그림 크기, 상하좌우 여백, 라운드, 위치, 가운데/위쪽 정렬, 그림자, 전체 크기, 부모 채우기 fill, 간격, 글자 크기·굵기·줄 높이)를 iOS(SwiftUI)·Android(Compose) 코드와 Figma 노드에서 스크립트로 뽑아 1:1 대조하고, 무엇이 얼마나 다른지·같다면 왜 같은지 근거(파일:줄, Figma 노드)를 단 보고서를 만든다. LLM 판단 없이 정적 분석으로 한다. "크기 비교해", "아이콘 크기 같아?", "여백·라운드·그림자 맞아?", "아이폰이랑 수치 비교", "시안이랑 수치 대조", "모든 컴포넌트 수치로 비교", "피그마랑 크기 다른 거 찾아", "UI 정합 보고서", "size audit" 같은 말이 나오면 픽셀 캡처로 재기 전에 반드시 이 스킬을 쓴다. Use for any iOS↔Android↔Figma numeric UI parity check of sizes, paddings, radii, shadows, alignment, or fill.
---

# ui-size-audit

값은 **코드와 Figma 노드에서 읽는다.** 스크린샷 픽셀로 크기를 재서 "아이폰은 12.7"처럼 말하지 않는다(사용자 교정: "아이폰이 크기 몇으로 세팅돼 있는지 코드로 봐야지", "피그마는 피그마에서 요소 추출").
픽셀 캡처는 마지막 확인용으로만 쓴다.

## 흐름

```
S=~/.claude/skills/ui-size-audit/scripts
# 1) 코드에서 요소 뽑기 (화면 진입점 이름 + 그 화면이 부르는 파일들)
python3 $S/extract_code.py --root <iOS레포> --files <View.swift ...> --entry RankingView -o ios.json
python3 $S/extract_code.py --root <Android레포> --files <Screen.kt 공용컴포넌트.kt ...> --entry RankingScreen -o and.json
# 2) Figma에서 요소 뽑기 (get_design_context 결과를 파일로 저장한 것, 또는 REST nodes JSON)
python3 $S/extract_figma.py ctx.txt -o fig.json --name 랭킹 --assets-dir figassets
# 3) 짝짓고 속성 대조 (기준 → 대상)
python3 $S/compare.py ios.json and.json -o cmp.json --ios-assets <iOS레포> --android-res <Android res 폴더>
python3 $S/compare.py fig.json and.json -o cmp_fig.json --android-res <res>
# 4) 보고서
python3 $S/report.py cmp.json [cmp2.json ...] -o report.md --ref-name iOS --target-name Android
```

- 기준(ref)이 정답 쪽이다. iOS가 정답이면 iOS를 ref, Figma가 정답이면 Figma를 ref로 둔다.
- `--files`에는 화면 파일과 그 화면이 부르는 공용 컴포넌트 파일(Avatar.kt 등)을 같이 넣는다. 빠지면 그 요소는 펼쳐지지 않는다.
- 보고서는 사용자에게 파일로 보내고(SendUserFile), 답에는 ❌ 개수와 큰 차이 몇 줄만 적는다.

## Figma 데이터 받기

- Figma MCP 한도는 **파일이 든 팀의 플랜**을 따른다. 남의 Starter 팀 파일이면 월 6회라 금방 막힌다.
  - 내 팀으로 복사해서 사본을 읽는다: `python3 ~/.claude/skills/chrome-direct/scenarios/figma_copy_to_team.py <file_key>` → 새 key.
  - 사본은 노드 id가 바뀐다. `get_metadata(fileKey=사본, nodeId=페이지id)`로 화면 이름을 찾아 쓴다.
- 화면마다 `get_design_context`(clientFrameworks=react 기본)를 불러 결과 코드를 `ctx/<노드>.txt`로 저장한 뒤 extract_figma.py에 넣는다.
- 결과가 너무 커서 tool-results 파일로 떨어지면 `jq -r '.[0].text'`로 꺼내 저장한다.
- `--assets-dir`를 주면 에셋 svg를 받아 그림 실제 크기(glyph)까지 잰다. MCP 에셋 주소는 7일 뒤 만료되니 그 안에 돌린다.
- 상태바·탭바(`bar/status`, `bar/navigation`, `bar/indicator`)는 기본으로 뺀다. 화면 코드 밖에 있기 때문이다. `--skip ""`면 안 뺀다.
- Figma 프레임 폭(360)과 iOS 기기 폭(402)이 다르면 fill 요소의 width는 다르게 나온다. fill 여부로 판정한다.

## 무엇을 어떻게 비교하나

- 요소 고르기는 스크립트가 한다: 글자(문구), 그림(에셋·SF 기호 이름), 아래쪽에 있는 글자·그림 겹침, 부모 짝, 역할(Row/Column/Text/Image) 순으로 짝을 짓는다.
- 아이콘은 틀(frame/size)이 아니라 **실제로 그려지는 그림 크기**를 비교한다.
  - iOS SF 기호: `glyph.swift symbol <이름> <pt> [weight]`로 렌더해 잰다(글자 크기 14.4pt person.fill → 12.0×12.88).
  - iOS 에셋·Figma svg: 틀에 맞춰 렌더/경로 경계로 잰다.
  - Android 벡터: `vector_bbox.py <xml> <w> <h>`로 경로 경계를 틀에 맞춰 잰다.
- 간격은 spacing + 고정 Spacer를 합친 실제 아이 사이 간격으로 비교한다.
- padding·margin은 배경 앞뒤 순서가 같을 때만 따로 보고, 아니면 `space.*`로 합쳐 본다(SwiftUI·Compose 표기 차이).
- fill은 명시(`maxWidth: .infinity`, `fillMaxWidth`, `w-full`)와 암묵(아이가 늘어남)을 구분해 근거에 적는다.
- 허용 오차 기본 0.5pt(`--tol`).

## 보고서 읽는 법

- ❌ 다름: 차이와 양쪽 근거(파일:줄 + 그 줄, Figma 노드 id + 클래스)가 있다. 이걸 고친다.
- ✅ 같음: 같은 이유(양쪽 값과 근거)가 붙어 있다. 그대로 증명으로 쓴다.
- ⚠️ 한쪽에만: 한쪽 코드에만 적힌 속성. 기본값끼리 같은지 사람이 한 번 본다(예: Compose Column 기본 정렬 start vs SwiftUI VStack center).
- 🔍 모르는 수식어: 스크립트가 해석 못 한 modifier. 크기에 영향 있으면 extract_code.py의 *_props에 추가한다.
- 짝 없는 요소: 구조가 다르거나(중첩 vs 평평), if/when 분기라 한쪽에만 보이는 것. 오탐 원인 1순위다.

## 고칠 때

- 정답 쪽 코드는 손대지 않는다(예: RunnersHi는 iOS가 정답, iOS 레포 수정 금지).
- 대상 코드에 숫자를 넣을 때는 정답 쪽 코드 수식을 그대로 옮기고 주석에 출처를 단다(`// 아이폰 RankingView.ProfileAvatar: size * 0.6`). 픽셀로 잰 값(12.7 등)을 넣지 않는다.
- 고친 뒤 같은 명령을 다시 돌려 ❌가 줄었는지 확인하고, 마지막에 실제 화면 캡처로 한 번 본다.

## 한계

- 런타임 값(서버 데이터 길이, 동적 폰트 배율)은 못 본다.
- SwiftUI 부모 `.shadow`가 아이에게 번지는 것, `GeometryReader` 계산은 ⚠️로 남는다.
- Roborazzi 같은 스크린샷 테스트는 이 프로젝트에 없다. 필요하면 `adb shell uiautomator dump`로 실제 bounds를 받아 대조하는 것을 마지막 단계로 붙인다.
