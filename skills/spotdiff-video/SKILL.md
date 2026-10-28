---
name: spotdiff-video
description: 틀린그림찾기 게임 '오늘의 눈썰미'(Sharp Eyes Daily, ~/programming/vibecoding/spot-difference)의 유튜브 쇼츠·롱폼 영상을 tools/video/render.py로 만들고, 화면을 직접 확인한 뒤 텔레그램으로 사용자에게 보낸다. "쇼츠 만들어", "롱폼 뽑아", "영상 만들어", "영어판도", "영상 보내", "유튜브 영상", "틀린그림 영상", "인트로/타이머/음악 고쳐" 같은 말이 나오면, 그리고 렌더 형식(문제 수·풀이 시간·게임 소개·아이콘)을 바꿀 때 반드시 이 스킬을 먼저 연다. SNS 게시 자체는 sns-post 스킬 몫이다.
---

# 오늘의 눈썰미 유튜브 영상

레포: `~/programming/vibecoding/spot-difference`. 렌더러는 `tools/video/render.py` 한 파일이다(파일 맨 위 docstring에 사용법이 있다).
결과물은 `Logs/shorts/<이름>.mp4`와 `_meta.txt`(제목·설명·챕터·음악 출처), `_comment.txt`(고정 댓글 초안)이다. Logs는 커밋하지 않는다.

## 1. 확정된 형식 (사용자가 직접 정함)
이 형식은 사용자가 영상을 보고 하나씩 교정해서 정해졌다. 바꾸려면 먼저 이유를 말한다.

쇼츠 (`--preset short3`, 약 2:00, 1080×1920)
- 3문제: 쉬움 → 보통 → 어려움. 그림은 난이도 순으로 자동 정렬된다.
- 풀이 20·30·40초. 10초는 "너무 짧다"고 했다.
- 끝에 약 12초 게임 소개: 게임 화면 3장 + "플레이스토어 · 앱스토어에서 '오늘의 눈썰미' 검색" + "토스 앱에서도 바로 할 수 있어요".

롱폼 (`--preset ko_long`, 약 8:07, 1920×1080)
- 12문제: 쉬움 4 → 보통 4 → 어려움 4. 풀이 20·30·40초, 정답 공개는 차이 하나당 1.6초.
- 이유: 5문제를 60~120초씩 늘렸더니 "시간만 늘려놓은 거냐"고 했다. 롱폼은 시간이 아니라 문제 수로 채운다.
- 8분 이상이어야 중간 광고가 붙는다. 렌더러가 8:00 미만이면 경고한다.
- 인트로: 제목이 3초에 걸쳐 한 글자씩 나오고, 다 나온 뒤 3초 유지. 10초 정지 화면은 "영상인지도 몰랐다", 3초는 "너무 짧다"고 했다.
- 시간 바는 매 프레임 줄어들고, 바 끝에 그림 주제 아이콘(`tools/video/icons/<주제>.png`, Noto Emoji 3D, Apache 2.0)이 좌우로 흔들리며 따라간다. 흔들림은 "귀엽다"고 했다. 2프레임마다 그리면 "부르르" 떨려 보이므로 매 프레임 그린다.
- 챕터는 문제마다 하나다. 빠른 정답 구간은 10초가 안 돼서 유튜브 챕터 규칙(각 10초 이상)을 깨기 때문이다.
- 끝에 15초 게임 소개(왼쪽 앱 이름·검색 안내, 오른쪽 게임 화면 3장).

공통
- 음악은 유튜브에서 흔히 쓰는 무료 음악인 Kevin MacLeod(CC BY 4.0)를 쓴다. 출처는 `_meta.txt`에 자동으로 들어간다. 다른 곡을 넣을 때도 상업 이용·출처 표기 조건을 공식 문서로 확인한다.
- 언어: `--lang en`(영어판), 기본은 프리셋의 ko. 영어판도 같은 프리셋을 쓴다(`en_long` 같은 프리셋은 없다).

## 2. 그림 고르기
- 영상에는 **유튜브 전용 그림**(`art/youtube/stages/y_*`)만 쓴다. 앱 그림은 쓰지 않는다. 영상에 정답이 나오므로 앱에서 같은 그림을 만나면 답을 알고 시작하게 된다(`docs/shorts/PLAN.md` 6장).
- 난이도(각 `stage.json`의 `difficulty`)
  - 쉬움(1): chestnut, honey, pottery, radiorepair, recordshop, tabletennis
  - 보통(2): aquarium, icerink, mushroom, noodleworks, quilt
  - 어려움(3, 작은 차이 5개): bicycle, recycling, sealcarving, umbrellamender
  - videorental은 난이도가 비어 있다. 쓰기 전에 확인한다.
- 이 목록은 그림이 추가되면 바뀐다. `art/youtube/stages/*/stage.json`에서 다시 확인한다.
- 어려움 그림이 4장뿐이라 롱폼 한 편에 다 쓴다. 다음 편을 위해 그림이 더 필요하면 Codex로 그린다(이미지 생성은 Codex 몫). 새 그림은 `art/youtube/validate_youtube.py`를 통과해야 한다.
- 새 그림 주제를 넣으면 `tools/video/icons/<주제>.png` 아이콘도 넣는다. 없으면 돋보기(`default.png`)가 나온다. 아이콘은 `https://raw.githubusercontent.com/googlefonts/noto-emoji/main/3D/png/128/emoji_u<코드>.png`에서 받는다.

## 3. 만들기
```bash
cd ~/programming/vibecoding/spot-difference
# 쇼츠
python3 tools/video/render.py short --preset short3 --stages y_honey_01,y_quilt_01,y_sealcarving_01 --out Logs/shorts/s_ko
python3 tools/video/render.py short --preset short3 --lang en --stages ... --out Logs/shorts/s_en
# 롱폼 (쉬움4,보통4,어려움4)
python3 tools/video/render.py long --preset ko_long --stages <12개> --out Logs/shorts/long_ko
python3 tools/video/render.py long --preset ko_long --lang en --stages <12개> --out Logs/shorts/long_en
```
- `--check`를 붙이면 렌더 없이 길이·스포일러 검사만 한다. `--quick`은 풀이를 4초로 줄인 미리보기다.
- 한국어·영어는 백그라운드에서 동시에 돌린다. 롱폼은 둘이 합쳐 몇 분 걸린다.
- 렌더 설정을 바꿀 때는 그림 1장으로 짧게 먼저 뽑아 본다(`--stages y_chestnut_01`, 약 50초 영상, 8초 렌더).
- 경고 중 "also used in episode ko_long_001", "toss_url is a placeholder", "no tip"는 알려진 경고다. 그 밖의 경고는 읽고 처리한다.

## 4. 보내기 전에 직접 본다
렌더가 성공해도 화면이 틀릴 수 있다. 사용자에게 보내기 전에 프레임을 직접 본다.
```bash
bash ~/.claude/skills/spotdiff-video/scripts/frames.sh Logs/shorts/long_ko.mp4 /tmp/sheet.png 2 7 30 400 470
```
그다음 Read로 시트를 연다. 볼 것: 인트로 글자, 문제 번호·남은 초, 아이콘 위치, 정답 원, 끝 게임 소개, 영어판 글자 넘침.
움직임(떨림·끊김)은 정지 프레임으로 안 보인다. 연속 프레임 몇 장을 잘라 위치가 고르게 변하는지 숫자로 확인한다.

## 5. 사용자에게 보내기
"영상 보내"는 텔레그램으로 보내라는 뜻이다.
```bash
bash ~/.claude/skills/spotdiff-video/scripts/send_tg.sh Logs/shorts/long_ko.mp4 "롱폼(한국어) 8:07 — 바꾼 점 한 줄"
```
- 가로·세로·길이·썸네일을 같이 보낸다. 빼면 텔레그램이 영상을 찌그러뜨려 보여 준다("왤케 찌부돼있냐").
- 출력 `True 1920 1080`이 성공이다. JSONDecodeError가 나면 한 번 더 보낸다(큰 파일 업로드가 가끔 끊긴다).
- 키는 `~/.claude/.env`의 `RAM_NOTI_TG_TOKEN`·`RAM_NOTI_TG_CHAT_ID`. 값을 출력하지 않는다.

## 6. 마무리
- `tools/video/` 변경은 파일별로 `git add`해서 커밋·푸시한다. Logs/ 영상은 커밋하지 않는다.
- 형식을 사용자가 새로 정하면 `docs/shorts/PLAN.md`와 이 SKILL.md 1장을 고치고, library `decisions/spot-difference/scope/`에도 남긴다.
- 게시(유튜브·인스타·스레드·X)는 하지 않는다. 사용자가 "올려"라고 한 뒤 sns-post 스킬로 한다. 유튜브 채널은 아직 인증 전이다.
