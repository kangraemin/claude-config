#!/usr/bin/env python3
"""PreToolUse(Write|Edit|NotebookEdit): 사용자 말이 들어온 뒤 library 검색 없이 파일을 쓰면 첫 쓰기를 한 번 막는다.
11/28 M6(32회 "개소리야 씌발아 그뒤에 이거 냈었는데 ?"): 이전 기록·결정을 안 찾고 새로 함 — 안내문만 있고 찾았는지 아무도 안 봤다.
임시 폴더(/tmp·scratchpad·.cache) 쓰기와 서브에이전트는 건너뛴다. 같은 사용자 말엔 한 번만 막는다."""
import hashlib, json, os, re, sys
STATE = os.path.expanduser("~/.claude/hooks/.libsearch-state.json")
SKIP_PATH = re.compile(r"^(/private)?/tmp/|/scratchpad/|/\.cache/|\.library-review-excerpt")


def human(e):
    if e.get("type") != "user" or e.get("isMeta") or e.get("isSidechain"):
        return None
    c = (e.get("message") or {}).get("content")
    if isinstance(c, str):
        return None if c.startswith("<") else c
    if isinstance(c, list) and not any(x.get("type") == "tool_result" for x in c if isinstance(x, dict)):
        t = "\n".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
        return t if t.strip() and not t.lstrip().startswith("<") else None
    return None


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return 0
    if d.get("agent_id") or d.get("agent_type"):
        return 0
    fp = (d.get("tool_input") or {}).get("file_path", "") or (d.get("tool_input") or {}).get("notebook_path", "")
    if not fp or SKIP_PATH.search(fp):
        return 0
    try:
        lines = open(d["transcript_path"], encoding="utf-8").read().splitlines()[-600:]
    except Exception:
        return 0
    q = None
    searched = False
    for l in reversed(lines):
        try:
            e = json.loads(l)
        except Exception:
            continue
        if e.get("type") == "assistant":
            for x in (e.get("message") or {}).get("content") or []:
                if isinstance(x, dict) and x.get("type") == "tool_use" and re.search(r"library_search|decision_search|instruction_search|library_read|decision_read", x.get("name", "")):
                    searched = True
        h = human(e)
        if h:
            q = h
            break
    if not q or searched or q.startswith(("정기 점검", "This session is being continued")):
        return 0
    key = hashlib.sha1((d.get("session_id", "") + "|" + q).encode()).hexdigest()
    try:
        st = json.load(open(STATE))
    except Exception:
        st = {}
    if st.get(d.get("session_id", "")) == key:
        return 0
    st[d.get("session_id", "")] = key
    try:
        json.dump(st, open(STATE, "w"))
    except Exception:
        return 0
    sys.stderr.write("⛔ 이 사용자 말 뒤에 library_search를 안 하고 파일을 쓰려 한다(11/28 M6, 32회 '이전 기록 안 찾고 새로 함'). "
                     "mcp__claude-library__library_search(사용자 말 원문)를 먼저 부르고, '전에·이전·다른 세션·하기로'가 있으면 decision_search·지난 세션 jsonl grep까지 한 뒤 다시 써라: " + q[:80].replace("\n", " ") + "\n")
    return 2


sys.exit(main())
