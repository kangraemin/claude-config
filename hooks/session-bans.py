#!/usr/bin/env python3
"""사용자가 "X 하지 마"라고 한 것을 기계로 막는다 (11/28 M8, 29회 — "크롬쓰지말라고", "보내지마", "내가 하라고하기전까지하지마").
UserPromptSubmit: 금지 말을 잡아 ~/.cache/session-bans/<세션>.json 에 6시간 기록, "다시 해/써도 돼/풀어"면 지움.
PreToolUse(Bash|Write|Edit): 기록된 금지와 맞는 명령이면 막는다. 무엇을 막는지는 아래 표에 있는 것만(헷갈리는 건 안 막음)."""
import json, os, re, sys, time
DIR = os.path.expanduser("~/.cache/session-bans")
TTL = 6 * 3600
# 말 속 낱말 -> 막을 명령 정규식
TABLE = {
    "chrome": (r"크롬|chrome|브라우저", r"chromectl|chrome-direct|Google Chrome|osascript[^\n]*Chrome|open -a ['\"]?Google Chrome"),
    "telegram": (r"텔레그램|알림|메시지 ?보내|보내", r"sns_tg\.py|api\.telegram\.org|send_digest\.py|tg_send|notify"),
    "commit": (r"커밋", r"\bgit (commit|push)\b"),
    "push": (r"푸시|push", r"\bgit push\b"),
    "deploy": (r"배포|deploy", r"wrangler (deploy|pages)|cf\.sh deploy|ait deploy|deploy\.sh|vercel"),
    "codex": (r"코덱스|codex", r"\bcodex( exec|_console|\b)"),
    "submit": (r"제출", r"\.submit\.lock|submit_|submission_gate\.py [^\n]*--stage sent|smtp"),
    "post": (r"게시|올리|업로드", r"sns_tg\.py done|my-sns|insta-web|post_|upload"),
    "claudep": (r"claude ?-p|헤드리스", r"\bclaude(-account)? [^\n]*(-p|--print)\b"),
    "job": (r"job|잡|작업 띄우|큐", r"queue\.txt|run_queue\.sh|tmux new-session[^\n]*job-"),
}
BAN = re.compile(r"(하지 ?마|하지 ?말|쓰지 ?마|쓰지 ?말|보내지 ?마|건드리지 ?마|손대지 ?마|올리지 ?마|띄우지 ?마|돌리지 ?마|금지|멈춰|그만)")
UNBAN = re.compile(r"(다시 ?(해|써|켜|보내|올려)|써도 ?돼|해도 ?돼|풀어|허락|이제 ?해)")


def path(sid):
    return os.path.join(DIR, re.sub(r"[^\w-]", "_", sid or "x") + ".json")


def load(sid):
    try:
        d = json.load(open(path(sid)))
    except Exception:
        return {}
    now = time.time()
    return {k: v for k, v in d.items() if now - v.get("at", 0) < TTL}


def on_prompt(d):
    q = d.get("prompt") or ""
    if q.lstrip().startswith(("<", "정기 점검")):
        return 0
    bans = load(d.get("session_id"))
    changed = False
    for sent in re.split(r"[\n.!?]|(?<=[요다])\s", q):
        for k, (word, _) in TABLE.items():
            if not re.search(word, sent, re.I):
                continue
            if BAN.search(sent) and not re.search(r"(안|못) ?하지 ?마|하지 ?마(세요)?\?|하지 ?말까", sent):
                bans[k] = {"at": time.time(), "said": sent.strip()[:80]}; changed = True
            elif UNBAN.search(sent) and k in bans:
                bans.pop(k); changed = True
    if changed:
        os.makedirs(DIR, exist_ok=True)
        json.dump(bans, open(path(d.get("session_id")), "w"), ensure_ascii=False)
        if bans:
            print("기록된 금지(이 세션, 6시간): " + " / ".join(f"{k}: \"{v['said']}\"" for k, v in bans.items()))
    return 0


def on_tool(d):
    if d.get("agent_id") or d.get("agent_type"):
        sid = d.get("session_id")  # 서브에이전트도 같은 금지를 지킨다
    bans = load(d.get("session_id"))
    if not bans:
        return 0
    ti = d.get("tool_input") or {}
    s = ti.get("command") or ((ti.get("file_path") or "") + "\n" + (ti.get("content") or ti.get("new_string") or ""))
    for k, v in bans.items():
        if re.search(TABLE[k][1], s, re.I):
            sys.stderr.write(f"⛔ 사용자가 이 세션에서 금지했다: \"{v['said']}\" (11/28 M8). 이 명령은 하지 않는다. "
                             "꼭 필요하면 하지 말고 사용자에게 왜 필요한지 한 줄로 말해라. 사용자가 '다시 해/써도 돼'라고 하면 풀린다.\n")
            return 2
    return 0


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return 0
    return on_prompt(d) if d.get("hook_event_name") == "UserPromptSubmit" or "prompt" in d and "tool_name" not in d else on_tool(d)


sys.exit(main())
