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
    r"라고 해 ?주세요|승인해 ?주시면|정해 ?주세요|골라 ?주세요)"
)
# 물리적으로 사람만 할 수 있는 단계는 물어도 된다(CLAUDE.md '묻지 말고 끝까지')
IDLE_ASK = re.compile(r"(뭘|무엇을|무얼) (할까요|도와|해 ?드릴까요)|what would you like|how can I help", re.I)
HUMAN_ONLY = re.compile(r"인증번호|문자 ?인증|토스 앱에서|결제 본인인증|실물 도장|보안문자|얼굴 인증|패스키|passkey", re.I)

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
    if HUMAN_ONLY.search(tail) or IDLE_ASK.search(tail):
        return None
    if ASK_END.search(last_line) or ASK_WAIT.search(tail):
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
    reasons = [r for r in (check_push(cwd, uses), check_verify(text, uses), check_ask(text)) if r]
    if reasons:
        print(json.dumps({"decision": "block", "reason": "[ram-proxy] " + " / ".join(reasons)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
