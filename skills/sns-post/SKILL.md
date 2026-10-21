---
name: sns-post
description: 사용자 SNS 계정(개인 dev_ram_kang·@dev_ram_, 오구리웍스 oguriworks, 어디썼 eodi_sseot, 글마감 geulmagam, 먹맵 mukmap.kr)에 무엇이든 올리기 전에 반드시 거치는 공통 규칙. 어느 세션·어느 레포에서든 인스타·스레드·X·유튜브 쇼츠·링크드인·블로그에 게시·예약·댓글·답글을 하려 하면, 또는 "올려", "게시해", "홍보 글", "출시 소식 올려", "인스타에 카드", "스레드에 써" 같은 말이 나오면 이 스킬부터 연다. 앱 출시 홍보를 앱 레포 세션에서 하려 할 때도 해당한다.
---

# SNS 게시 공통 규칙

여러 세션이 같은 계정에 따로 올리면 하루에 몰리고, 같은 앱이 두 번 나가고, 엉뚱한 Chrome 프로필로 올라간다.
2026-10-22에 실제로 오구리웍스 스레드에 하루 2개가 나갔다.
그래서 누가 올리든 아래 순서를 똑같이 밟는다.
계정·말투·주기의 원본은 my-sns 레포(`~/programming/vibecoding/my-sns/CLAUDE.md`, `style/`)다.
여기는 모든 세션이 지켜야 할 최소 규칙만 담는다.

## 0. 내가 올려도 되는 세션인가
- SNS 운영은 my-sns 세션(`sns 홍보`)이 맡는다.
- 앱 레포 세션은 카드·캡션 같은 재료까지만 만든다.
  - 그다음 오구리웍스면 큐 표(`my-sns/drafts/oguri-release-queue.md`)에 날짜를 잡아 적는다.
  - 다른 계정이면 my-sns 세션에 SendMessage로 넘긴다.
- 앱 레포 세션에서 사용자가 "올려"라고 해도 큐에 이미 날짜가 잡혀 있으면 그 날짜를 따른다. 사용자에게는 "오늘 몇 개 나갔고 ○일에 잡혀 있다"고 한 줄로 알린다. 큐에 날짜가 있으면 my-sns 세션에 따로 알릴 필요는 없다.
- 사용자가 "오늘 꼭", "지금 바로"처럼 날짜를 콕 집으면 그 지시가 하루 1개·간격 규칙보다 우선한다. 올린 뒤 큐의 다음 항목을 하루씩 뒤로 민다.
- my-sns 세션에 넘길 때는 `ListAgents`에서 `sns 홍보`가 살아 있는지 확인한다. 없으면 큐 표나 my-sns `drafts/`에 적어 두면 매일 10:07 cron이 집어 간다.

## 0-1. 개인 계정은 자동 게시 금지
- 개인 계정(dev_ram_kang, @dev_ram_, 링크드인, GeekNews, 개발 블로그 kangraemin.github.io)은 사용자가 그 글을 콕 집어 "올려"라고 했을 때만 올린다(10/22 "절대 자동으로 올리지 말고 내가 올리라고 한 것만").
- 사전 동의·큐·cron·초안이 있어도 올리지 않는다. 초안까지만 만든다.

## 1. 계정과 Chrome 프로필을 맞춘다
| 페르소나 | 계정 | Chrome 프로필 |
|---|---|---|
| 개인 | 스레드·인스타 dev_ram_kang, X @dev_ram_, 링크드인 | Profile 1 |
| 어디썼(동업자 공용) | eodi_sseot (인스타·스레드·X·유튜브) | Profile 4 |
| 오구리웍스(사업자) | oguriworks (인스타·스레드) | Profile 5 |
| 글마감 | geulmagam | Profile 6 |
| 먹맵 | mukmap.kr | Profile 7 |
- 다른 프로필로 로그인하거나 게시하지 않는다. 페르소나가 섞인다.
- 탭은 `--match id:`로 잡는다. URL로 잡으면 다른 프로필의 같은 사이트 탭을 잡는다.
- 개인 프로필에는 "여기어때 개발자"라고 쓴다. "오구리웍스 대표"라고 쓰지 않는다.
- 어디썼은 동업자와 함께 쓰는 계정이다. 계정 설정은 바꾸지 않는다.

## 2. 오늘 이미 올렸는지, 같은 걸 올렸는지 본다
```bash
python3 ~/.claude/scripts/sns_tg.py check --account oguriworks   # 오늘 이 계정 게시(시각·서비스·링크·무엇), RESULT: ALREADY_TODAY n | FREE
```
- 오구리웍스 출시 소식이면 큐 표(`my-sns/drafts/oguri-release-queue.md`)의 상태 칸부터 읽는다. 어느 앱이 어느 서비스에 이미 나갔는지 거기 적혀 있다.
- **한 계정에는 하루에 글 하나만 올린다.** 같은 글을 인스타와 스레드에 함께 올리면 하나로 친다.
  - 사용자 지시(10/22): "하루에 와다다 올리지 말고 며칠에 걸쳐서".
  - 사용자가 정한 주기가 따로 있으면 그것을 따른다. 예: 글마감은 07시와 19시에 번갈아 올린다.
- ALREADY_TODAY가 나오면 오늘은 올리지 않는다. 큐에서 다음 빈 날로 옮긴다.
- 이미 하루에 2개 이상 나갔으면 지우지 않는다. 그 계정의 다음 게시를 하루 비워서 간격을 되찾는다.
- 같은 앱·같은 주제가 이미 나갔는지도 확인한다. 그 계정 프로필 화면을 보거나 `ls ~/programming/vibecoding/my-sns/posted/`를 본다.
  - 한쪽 서비스에만 나갔으면 나머지 서비스에만 올린다.
- 출시 소식은 큐(`my-sns/drafts/oguri-release-queue.md`)를 따른다. 간격은 2일이다.
  - 새 출시는 `my-sns/drafts/src/release_watch.py`가 매일 잡는다.

## 3. 글을 점검한다
- 숫자는 원본 데이터에 있는 것만 쓴다. 지어내지 않는다.
- 사람 이름과 직책은 쓰지 않는다.
- AI 티가 나는 문장을 쓰지 않는다. 과한 이모지, "~의 세계로" 같은 상투어, 지나치게 깔끔한 병렬 목록이 그 예다.
- 글자 수 한도는 X 280자(한글 1자 = 2), 스레드 500자, 인스타 2,200자다.
- 인스타 본문의 링크는 눌리지 않는다. "프로필 링크"로 안내하고, 스레드는 링크를 첫 댓글에 넣는다.
- 계정별 말투는 `my-sns/style/`에 있다. x-dev, threads-dev, linkedin-dev, cadence 문서를 본다.

## 4. 올리기 전에 알리고, 스크립트로 올린다
- 게시 확인 요청은 텔레그램 SNS 봇으로 보낸다.
  - 사용자가 사전 동의(10/22)를 했으니 답을 기다리지 않고 진행한다.
```bash
python3 ~/.claude/scripts/sns_tg.py ask --msg "<계정> <서비스>: <무엇>" --text-file caption.txt 01.png 02.png
```
- 게시는 손으로 클릭하지 않고 아래 스크립트로 한다. 스크립트는 기본이 dry-run이고, 같은 글이 이미 있으면 SKIP_EXISTS를 낸다.
  - 스레드: `my-sns/.claude/skills/eodi-sns/scripts/th_post.py --profile "Profile N" --handle H --body-file b.txt [--media ...] [--topic T] [--comment-file c.txt] --post`
  - X: `my-sns/.claude/skills/eodi-sns/scripts/x_post.py ... --post`
  - 유튜브: `.../yt_post.py ... --post`
  - 스레드 답글: `.../th_reply.py ... --post`
  - 인스타: `~/programming/vibecoding/seoul-expense-app/.claude/skills/insta-web/scripts/ig_post.py 01.png ... --caption-file c.txt --profile "Profile N" --share`
- 인스타 `--share`가 "기다림 시간 초과"로 FAIL을 내도 실제로는 올라갔을 수 있다.
  - 다시 올리기 전에 `ig_status.py --profile "Profile N"`으로 게시물 수를 확인한다. 중복 게시는 지우기 어렵다.
- 다른 앱이 화면 앞으로 튀어나오면 붙여넣기가 엉뚱한 곳에 간다.
  - 원인은 th-notify 루프와 공모전 세션의 한글 뷰어다.
  - 오래 걸리는 예약 게시는 `my-sns/drafts/src/geul_post_run.sh`처럼 th-notify 루프를 잠깐 멈춘 뒤 올린다.

## 5. 올린 뒤
- 위 게시 스크립트는 성공하면 알아서 처리한다.
  - @sns_daily_noti_bot으로 "[업로드 완료]"와 본문·사진을 보낸다.
  - 오늘 게시 기록(`~/.cache/sns-ledger.jsonl`)에도 남긴다.
- 스크립트 없이 손으로 올렸으면 둘 다 직접 한다.
```bash
python3 ~/.claude/scripts/sns_tg.py done --msg "<서비스> <계정>\n<링크>" --text-file caption.txt 01.png ...
python3 ~/.claude/scripts/sns_tg.py log --service 인스타 --account oguriworks --url <링크> --what "오늘타로 출시 소식"
```
- my-sns `posted/YYYY-MM-DD-<slug>.md`에 링크를 적고 커밋·푸시한다. 오구리웍스 출시 소식이면 큐 표의 상태 칸도 채운다.
- 알림은 공모전 봇(CONTEST_TG)으로 보내지 않는다. SNS 봇(SNS_UPLOAD_TG_*)으로만 보낸다.
