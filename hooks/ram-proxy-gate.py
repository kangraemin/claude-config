#!/usr/bin/env python3
"""Stop hook: 사용자가 손으로 보내던 독촉 메시지를 대신 보낸다.

사용자 메시지 26,300개 분석(2026-10-22)에서 반복되던 세 가지를 막는다.
  1. "할까요?"로 멈춤      -> 사용자가 'ㅇㅇ', 'ㄱㄱ'를 보내던 자리
  2. 커밋하고 push 안 함   -> "푸시좀 해 왤케 푸시들을 안해"
  3. 검증 없이 완료 선언   -> "확실한거야?", "직접 해봐"
stop_hook_active면 통과해서 한 번만 막는다(무한 루프 방지).
끄려면 RAM_PROXY_GATE=off.
"""
import json
import os
import re
import subprocess
import sys

ASK_END = re.compile(
    r"(할까요|볼까요|드릴까요|갈까요|될까요|좋을까요|원하시나요|괜찮을까요|어떨까요|진행할까|"
    r"하시겠어요|하시겠습니까|어느 쪽|어떤 걸로|어떻게 할까|shall I|should I|do you want|want me to)"
    r"[^\n]{0,40}\?\s*$",
    re.I,
)
ASK_WAIT = re.compile(
    r"(답 ?주시면|말씀해 ?주시면|알려 ?주시면|정해 ?주시면|골라 ?주시면|확인해 ?주시면|"
    r"라고 해 ?주세요|승인해 ?주시면|정해 ?주세요|골라 ?주세요|(라고|만) ?(알려|말해) ?주세요|해 ?주실 ?것|"
    r"(할지|어느|어떤|어떻게)[^\n]{0,12}(정해|골라|알려|말해) ?주세요|원하시면 ?말씀)"
)
# 물리적으로 사람만 할 수 있는 단계는 물어도 된다(CLAUDE.md '묻지 말고 끝까지')
IDLE_ASK = re.compile(r"(뭘|무엇을|무얼) (할까요|도와|해 ?드릴까요)|what would you like|how can I help", re.I)
HUMAN_ONLY = re.compile(r"인증번호|문자 ?인증|토스 앱에서|결제 본인인증|실물 도장|얼굴 인증|\"사\"라고|구매 지시|사려면", re.I)  # 11/28 보안문자·패스키 뺌(M14: 그 말로 넘기면 통째 통과)

DONE_CLAIM = re.compile(
    r"(완료했|완료됐|완료입니다|완료예요|완료야|끝났|고쳤|수정했|반영했|적용했|배포했|해결했|"
    r"구현했|됐습니다|됐어요|Done\b|fixed\b|deployed\b)",
    re.I,
)
CODE_EXT = re.compile(r"\.(py|js|jsx|ts|tsx|mjs|cjs|sh|go|rs|java|kt|swift|cs|gd|html|css|vue|svelte|sql|json|ya?ml|toml)$")
VERIFY_CMD = re.compile(
    r"\b(test|pytest|jest|vitest|playwright|e2e|npm (run|test)|pnpm|yarn|bun |node |python3? |uv run|"
    r"bash -n|shellcheck|tsc|eslint|lint|build|curl|chromectl|screencapture|screenshot|go test|cargo|"
    r"gradle|xcodebuild|godot|make|ait )",
    re.I,
)


UI_EXT = re.compile(r"\.(tsx|jsx|vue|svelte|css|scss|html)$")
IMG_EXT = re.compile(r"\.(png|jpe?g|webp|gif)$", re.I)


def load(path):
    rows = []
    try:
        with open(path) as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return rows


def is_human_turn(row):
    if row.get("type") != "user" or row.get("isMeta") or row.get("isSidechain"):
        return False
    c = (row.get("message") or {}).get("content")
    if isinstance(c, str):
        return not c.startswith("<")
    if isinstance(c, list):
        return any(x.get("type") == "text" for x in c) and not any(x.get("type") == "tool_result" for x in c)
    return False


def current_turn(rows):
    start = 0
    for i, r in enumerate(rows):
        if is_human_turn(r):
            start = i
    return rows[start + 1:]


def last_text(turn):
    for r in reversed(turn):
        if r.get("type") != "assistant":
            continue
        c = (r.get("message") or {}).get("content")
        if isinstance(c, list):
            t = "\n".join(x.get("text", "") for x in c if x.get("type") == "text").strip()
            if t:
                return t
    return ""


def tool_uses(turn):
    out = []
    for r in turn:
        if r.get("type") != "assistant" or r.get("isSidechain"):
            continue
        c = (r.get("message") or {}).get("content")
        if isinstance(c, list):
            out += [x for x in c if x.get("type") == "tool_use"]
    return out


def git(cwd, *args):
    try:
        return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def check_ask(text):
    tail = text.strip()[-400:]
    last_line = tail.splitlines()[-1] if tail else ""
    if IDLE_ASK.search(tail):
        return None
    # 11/28 M11: 끝 400자에 '인증번호'가 한 번만 있어도 통째로 통과하던 구멍 — 묻는 줄 자체가 사람 몫일 때만 통과
    ask_lines = [l for l in tail.splitlines() if ASK_END.search(l) or ASK_WAIT.search(l)]
    if ask_lines and all(HUMAN_ONLY.search(l) for l in ask_lines):
        return None
    if ask_lines:
        return (
            "묻고 멈췄다. 사용자는 2026-10-22에 '니가 하는 거 전부 동의할 테니 멈추지 마라'고 했다. "
            "선택지가 있으면 가장 나은 걸 골라 바로 진행하고, 무엇을 골랐는지 한 줄로 알려라. "
            "인증번호·토스 앱 열기처럼 사람 손이 물리적으로 필요한 단계만 짧게 요청한다."
        )
    return None


def check_push(cwd, uses):
    cmds = [u.get("input", {}).get("command", "") for u in uses if u.get("name") == "Bash"]
    committed = any(re.search(r"\bgit\b[^\n]*\bcommit\b", c) for c in cmds)
    if not committed or not cwd or not git(cwd, "rev-parse", "--is-inside-work-tree"):
        return None
    if not git(cwd, "remote"):
        return None
    branch = git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    upstream = git(cwd, "rev-parse", "--abbrev-ref", "@{u}")
    if not upstream:
        return f"커밋만 하고 push를 안 했다. `git push -u origin {branch}`까지 해라(--force 금지)."
    ahead = git(cwd, "rev-list", "--count", "@{u}..HEAD")
    if ahead.isdigit() and int(ahead) > 0:
        return f"커밋 {ahead}개가 push 안 됐다. `git push`까지 해라(--force 금지). 막히면 원인을 고쳐서 push한다."
    return None


def check_verify(text, uses):
    if not DONE_CLAIM.search(text[-600:]) or HUMAN_ONLY.search(text[-400:]):
        return None
    last_edit = -1
    for i, u in enumerate(uses):
        if u.get("name") in ("Edit", "Write", "NotebookEdit") and CODE_EXT.search(u.get("input", {}).get("file_path", "")):
            last_edit = i
    if last_edit < 0:
        return None
    after = uses[last_edit + 1:]
    if UI_EXT.search(uses[last_edit].get("input", {}).get("file_path", "")):
        # 화면 파일은 실행만으로 부족하다 — 캡처를 직접 열어 봐야 한다("깔끔해졌다고???", "직접 보고 줘라")
        seen = any(
            (u.get("name") == "Read" and IMG_EXT.search(u.get("input", {}).get("file_path", "")))
            or (u.get("name", "").startswith("mcp__") and "screenshot" in u.get("name", ""))
            for u in after
        )
        if not seen:
            return (
                "화면 파일을 고치고 캡처를 직접 보지 않은 채 완료라고 했다. "
                "실제 브라우저·기기에서 캡처를 찍어 Read로 열어 보고, 고친 부분이 의도대로 보이는지 확인한 뒤 보고해라. "
                "움직임이 있는 화면은 `python3 ~/.claude/skills/no-ai-look-design/scripts/motion_check.py <url>`로 끊김·속도까지 재라."
            )
        return None
    for u in after:
        name = u.get("name", "")
        if name == "Bash" and VERIFY_CMD.search(u.get("input", {}).get("command", "")):
            return None
        if name in ("Agent", "Task", "Skill") or name.startswith("mcp__"):
            return None
    return (
        "코드를 고친 뒤 아무것도 실행해 보지 않고 완료라고 했다. "
        "테스트·빌드·실제 실행(웹이면 브라우저로 열어 확인) 중 맞는 걸 돌리고, 그 결과를 근거로 보고해라. "
        "확인할 방법이 정말 없으면 '확인 못 함'과 이유를 적어라."
    )


PLAIN_ALLOW = {"API", "AI", "UI", "URL", "SEO", "GEO", "MVP", "PC", "OK", "PDF", "CSV", "QR", "SNS", "GA", "DB", "ID",
               "PR", "iOS", "Android", "Haiku", "Sonnet", "Opus", "Claude", "Codex", "GPT", "ChatGPT"}


def check_plain(text):
    """"먼말이여"·"한글로 말해" 방지. 코드·경로·URL을 뺀 본문의 영어 단어 비율로 본다.
    2026-10-31 보정: 혼란 반응 직전 답의 30%를 잡고, 그 외 답은 7%만 걸린다(0.3, 15단어)."""
    t = re.sub(r"```.*?```", "", text, flags=re.S)
    t = re.sub(r"`[^`]*`", "", t)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"\S*[/\\]\S*", "", t)
    toks = re.findall(r"[A-Za-z][A-Za-z0-9.+_-]*|[가-힣]+", t)
    lat = [x for x in toks if re.match(r"[A-Za-z]", x) and x not in PLAIN_ALLOW and len(x) >= 2]
    if len(lat) >= 15 and len(lat) / max(1, len(toks)) > 0.3:
        return (
            "답에 영어·내부 용어가 너무 많다(사용자 반응 '먼말이여', '한글로 말해'가 반복된 유형). "
            "물은 것에 대한 결론부터 쉬운 한국어로 다시 써라. 영어 단어·약어·내부 이름은 빼거나 괄호로 풀어 쓴다."
        )
    return None


def user_text(rows):
    """이번 턴을 연 사용자 말."""
    for r in reversed(rows):
        if is_human_turn(r):
            c = (r.get("message") or {}).get("content")
            if isinstance(c, str):
                return c
            return "\n".join(x.get("text", "") for x in c if x.get("type") == "text")
    return ""


def first_text(turn):
    for r in turn:
        if r.get("type") != "assistant":
            continue
        c = (r.get("message") or {}).get("content")
        if isinstance(c, list):
            t = "\n".join(x.get("text", "") for x in c if x.get("type") == "text").strip()
            if t:
                return t
    return ""


# M14 (11/28, 30회 "로그를씨발달라고하는게말이되냐"): 기존 스크립트를 안 찾고 사람에게 넘김
HANDOFF = re.compile(r"로그인(을|해)? ?(해 ?)?주세요|본인인증[^\n]{0,6}(해 ?)?주세요|가입(을|해)? ?(해 ?)?주세요|보안문자[^\n]{0,10}주세요|"
                     r"(캡차|리캡챠|패스키)[^\n]{0,10}주세요|눌러 ?주세요|로그(를)? ?(보내|복사해|붙여) ?주세요|캡처(를)? ?(보내|찍어) ?주세요|직접 (해|눌러|열어) ?주세요")


def check_handoff(text, uses):
    lines = [l for l in text.splitlines() if HANDOFF.search(l) and not re.search(r"제출|거부|현황판|고르|골라|OK면|괜찮으면", l)]
    if not lines:
        return None
    cmds = " ".join(u.get("input", {}).get("command", "") for u in uses if u.get("name") == "Bash")
    if re.search(r"(grep|ls|find|rg)[^\n]*(skills|scenarios)", cmds):
        return None
    return ("사용자에게 로그인·인증·보안문자·버튼·로그 일을 넘겼다(11/28 M14, 30회). 넘기기 전에 "
            "`grep -rli <키워드> ~/.claude/skills/*/scripts ~/.claude/skills/chrome-direct/scenarios ~/.claude/skills/chrome-direct/SKILL.md`로 "
            "기존 스크립트를 찾아 직접 해라. 보안문자는 그림을 읽어 직접 넣는다. 문자 인증번호·토스 앱 열기만 사람 몫.")


# M2 (11/28, 48회 "한국어로말하라고씨발련아"): 한글 내부어·파일명이 섞인 답
JARGON = re.compile(r"(?<![A-Za-z가-힣])(slot|slots|gate|manifest|picks|choosing|state\.json|\.done|job|cron|sync|push|pull|tmux|payload|"
                    r"schema|fixture|evaluation|rankJudges|displayLines|userAction|doing|running|handled|queue|launchd|PASS|BLOCK|FAIL|"
                    r"게이트|슬롯|매니페스트|페이로드)(?![A-Za-z])")


def check_jargon(text):
    t = re.sub(r"```.*?```", "", text, flags=re.S)
    t = re.sub(r"`[^`]*`", "", t)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"\S*[/\\]\S*", "", t)
    hits = JARGON.findall(t)
    files = re.findall(r"\b[\w-]+\.(py|sh|json|md|txt|plist)\b", t)
    if len(hits) + len(files) >= 4:
        uniq = sorted(set(hits))[:6]
        return ("답에 내부 이름·영어 용어가 많다(" + ", ".join(uniq) + f" 등 {len(hits) + len(files)}개, 11/28 M2 48회). "
                "사용자가 보는 화면의 말(현황판 카드·고르기 화면·작업)로 바꾸고, 꼭 필요한 파일명만 백틱으로 남겨라.")
    return None


# M21 (11/28, 13회 "너 막혓다는말 씨발렴아"): 찾아보지 않고 막혔다·못 한다
BLOCKED = re.compile(r"(지금은|여기서|더는|더 이상|이 ?세션에선|당장은)[^\n]{0,10}(할 수 없|못 ?해|진행 ?못|멈춰|멈춥|막혀)|직접 하셔야|"
                     r"불가능(해요|합니다|이에요)|할 수 없(어요|습니다)\.?\s*$|규칙(상|대로) ?안 ?(돼|됩)|"
                     r"한도(가|에)[^\n]{0,8}(다 ?돼|걸려|찼)[^\n]{0,20}(멈|못|기다|대기)", re.M)


def check_blocked(text, uses):
    tail = "\n".join(l for l in text[-800:].splitlines() if BLOCKED.search(l) and not re.search(r"(?<!수 )없(어요|음|습니다)\s*\.?$", l.strip()))
    if not tail or HUMAN_ONLY.search(tail):
        return None
    names = [u.get("name", "") for u in uses]
    cmds = " ".join(u.get("input", {}).get("command", "") for u in uses if u.get("name") == "Bash")
    searched = any("library_search" in n or "decision_search" in n or n in ("WebSearch", "Agent") for n in names)
    looked = re.search(r"(grep|rg|find|ls)[^\n]*(skills|scripts|scenarios|hooks)", cmds)
    if searched and looked:
        return None
    return ("'막혔다·못 한다·한도'라고 답했는데 이번 턴에 " + ("library 검색" if not searched else "") +
            (" · " if not searched and not looked else "") + ("기존 스크립트 찾기(grep skills/scripts)" if not looked else "") +
            "를 안 했다(11/28 M21). 둘 다 해 보고 다른 방법이 정말 없을 때만 막혔다고 말해라. 규칙 때문이면 그 규칙 파일 경로를 같이 적어라.")


# M7 (11/28, 31회 "개소리야씨발여낭 1,2합치라고"): '아니'·욕 뒤엔 이해한 것부터
ANGRY = re.compile(r"^\s*아니|씨발|시발|ㅅㅂ|지랄|개소리|병신|이해를? ?못|이해하고|못 ?알아|말귀")


def check_understood(user, turn):
    if not user or not ANGRY.search(user) or user.lstrip().startswith(("<", "정기 점검")):
        return None
    if re.search(r"\?\s*$|(냐|니|까|음|임|는데|ㅁ)\s*\?*\s*$", user.strip()) and not user.lstrip().startswith("아니"):
        return None  # 화난 질문은 답이 먼저(answer-question-first)
    head = "\n".join(first_text(turn).splitlines()[:3])
    if re.search(r"이해했|이해한 ?것|잘못 알아들", head):
        return None
    return ("사용자가 '아니'나 욕으로 바로잡았다(11/28 M7, 31회). 답 첫 줄에 '이렇게 이해했어요: ~'로 이번에 이해한 것을, "
            "아니로 시작했으면 무엇을 잘못 알아들었는지 한 줄로 쓰고 진행해라.")


# M13 (11/28, 21회 "좀 고치라고"): '두 번 다시·기계적으로' 말했는데 글 규칙만 고침
MECH_ASK = re.compile(r"두 ?번 ?다시|훅으로|스크립트화|재발|기계적으로|다시는 ?안|절대 ?안 ?(나|생기)|안 ?빼먹게")
MECH_PATH = re.compile(r"(/hooks/|/scripts/|\.plist|_check\.py|_gate\.py|guard|test_|/board/[^ ]*\.py|/jobs/[^ ]*\.(py|sh))")


def check_mechanize(user, uses):
    if not user or not MECH_ASK.search(user) or user.lstrip().startswith("<"):
        return None
    for u in uses:
        i = u.get("input", {})
        if u.get("name") in ("Edit", "Write") and MECH_PATH.search(i.get("file_path", "")):
            return None
        if u.get("name") == "Bash" and re.search(r"(>|tee|sed -i|python3 - )[^\n]*" + MECH_PATH.pattern, i.get("command", "")):
            return None
        if u.get("name") == "Agent":
            return None
    return ("사용자가 '두 번 다시·기계적으로·훅으로'를 말했는데 이번 턴에 훅·검사기·스크립트·launchd를 안 만들었다(11/28 M13). "
            "규칙 글(CLAUDE.md·메모리)만 고치지 말고 막는 장치를 만들고, 일부러 틀린 예로 막히는지 시험한 뒤 보고해라.")


MEDIA_MAKE = re.compile(r"(ffmpeg|remotion|render\.py|render\b|moviepy|say -o|tts)[^\n]*\.(mp4|mov|webm|mp3|wav|m4a)\b", re.I)


def check_media(text, uses):
    """영상·소리를 만들고 숫자 검사 없이 넘기면 막는다("음악 너무 커", "음성 끊겨", "냅다 시간만 늘림")."""
    cmds = [u.get("input", {}).get("command", "") for u in uses if u.get("name") == "Bash"]
    made = [i for i, c in enumerate(cmds) if MEDIA_MAKE.search(c)]
    if not made or not DONE_CLAIM.search(text[-600:] + " " + ("보냈" if "보냈" in text else "")):
        return None
    if any("av_check" in c for c in cmds[made[-1]:]):
        return None
    return (
        "영상·소리를 만들고 숫자 검사 없이 넘겼다. "
        "`python3 ~/.claude/skills/no-ai-look-design/scripts/av_check.py <파일> [--bgm 배경음악 --voice 음성]`을 돌려 "
        "음량·중간 끊김·정지 화면·배경음악 반복을 확인하고, FAIL이면 고친 뒤 보고해라. 영상은 프레임 몇 장을 뽑아 Read로 직접 본다."
    )


def main():
    if os.environ.get("RAM_PROXY_GATE", "on") == "off":
        return
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    if data.get("stop_hook_active"):
        return
    turn = current_turn(load(data.get("transcript_path", "")))
    if not turn:
        return
    text = last_text(turn)
    uses = tool_uses(turn)
    cwd = data.get("cwd", "")
    rows_all = load(data.get("transcript_path", ""))
    user = user_text(rows_all)
    reasons = [r for r in (check_push(cwd, uses), check_verify(text, uses), check_ask(text), check_plain(text), check_media(text, uses),
                           check_handoff(text, uses), check_jargon(text), check_blocked(text, uses), check_understood(user, turn),
                           check_mechanize(user, uses)) if r]
    if reasons:
        print(json.dumps({"decision": "block", "reason": "[ram-proxy] " + " / ".join(reasons)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
