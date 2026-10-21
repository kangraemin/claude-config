#!/usr/bin/env python3
"""세션 상황판: 최근 Claude 세션들이 지금 뭘 하고 있는지 한 표로 보여준다.

사용자가 세션 4~8개를 동시에 띄워 두고 "되고있나", "야"를 보내며 돌아다니던 일(2026-10-22 분석)을 대신한다.
  인자 없음   -> 최근 24시간 세션 표 출력
  --notify    -> 직전 실행과 비교해 '작업 중'이던 세션이 끝나거나 멈추면 텔레그램으로 알림 (launchd 5분 주기)
  --hours N   -> 표에 넣을 기간(기본 24)
"""
import glob
import json
import os
import subprocess
import sys
import time

PROJECTS = os.path.expanduser("~/.claude/projects")
STATE = os.path.expanduser("~/.claude/session-board/state.json")
ENV = os.path.expanduser("~/.claude/.env")
STALL_MIN = 10  # 도구 결과를 기다린 채 이만큼 조용하면 멈춘 것으로 본다
TAIL_BYTES = 400_000


def tail_rows(path, limit=TAIL_BYTES):
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - limit) if limit else 0)
        data = f.read().decode("utf-8", "ignore")
    rows = []
    for line in data.splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    return [r for r in rows if r.get("type") in ("user", "assistant") and not r.get("isSidechain")]


def human_text(row):
    if row.get("type") != "user" or row.get("isMeta") or row.get("isCompactSummary"):
        return ""
    c = (row.get("message") or {}).get("content")
    if isinstance(c, str):
        return "" if c.startswith("<") else c
    if isinstance(c, list) and not any(x.get("type") == "tool_result" for x in c):
        return " ".join(x.get("text", "") for x in c if x.get("type") == "text")
    return ""


def assistant_text(row):
    c = (row.get("message") or {}).get("content")
    if row.get("type") != "assistant" or not isinstance(c, list):
        return ""
    return " ".join(x.get("text", "") for x in c if x.get("type") == "text").strip()


def summarize(path):
    rows = tail_rows(path)
    if not rows:
        return None
    age = (time.time() - os.path.getmtime(path)) / 60
    last_user = next((t for t in map(human_text, reversed(rows)) if t), "")
    if not last_user:  # 첫 지시가 끝부분 밖에 있으면 전체에서 찾는다
        last_user = next((t for t in map(human_text, reversed(tail_rows(path, 4_000_000))) if t), "")
    last_ai = next((t for t in map(assistant_text, reversed(rows)) if t), "")
    last = rows[-1]
    c = (last.get("message") or {}).get("content")
    # 마지막이 사용자 메시지·도구 결과이거나 도구 호출이면 아직 답이 끝나지 않은 것
    pending = last.get("type") == "user" or (
        isinstance(c, list) and any(x.get("type") == "tool_use" for x in c)
    )
    if pending:
        status = "작업 중" if age < STALL_MIN else "멈춤?"
    else:
        status = "끝남"
    cwd = next((r.get("cwd") for r in reversed(rows) if r.get("cwd")), "")
    return {
        "id": os.path.basename(path)[:-6],
        "project": os.path.basename(cwd) or os.path.basename(os.path.dirname(path)),
        "status": status,
        "age": age,
        "user": " ".join(last_user.split())[:60],
        "ai": " ".join(last_ai.split())[:200],
    }


def sessions(hours):
    cutoff = time.time() - hours * 3600
    paths = [p for p in glob.glob(f"{PROJECTS}/*/*.jsonl") if os.path.getmtime(p) >= cutoff]
    out = [s for s in map(summarize, sorted(paths, key=os.path.getmtime, reverse=True)) if s]
    return out


def ago(m):
    return f"{m:.0f}분" if m < 60 else f"{m / 60:.1f}시간"


def print_table(rows):
    if not rows:
        print("최근 세션 없음")
        return
    order = {"작업 중": 0, "멈춤?": 1, "끝남": 2}
    for s in sorted(rows, key=lambda s: (order[s["status"]], s["age"])):
        print(f"[{s['status']}] {s['project']} · {ago(s['age'])} 전 · {s['id'][:8]}")
        print(f"   나: {s['user']}")
        print(f"   AI: {s['ai'][:120]}")


def telegram(text):
    env = {}
    try:
        for line in open(ENV):
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.strip().removeprefix("export ").split("=", 1)
                env[k] = v.strip().strip("'\"")
    except OSError:
        return
    token, chat = env.get("CONTEST_TG_TOKEN"), env.get("CONTEST_TG_CHAT_ID")
    if token and chat:
        subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-d", f"chat_id={chat}", "--data-urlencode", f"text={text}",
             f"https://api.telegram.org/bot{token}/sendMessage"],
            timeout=20,
        )


def notify(rows):
    try:
        prev = json.load(open(STATE))
    except (OSError, ValueError):
        prev = {}
    alerts = []
    for s in rows:
        if prev.get(s["id"]) == "작업 중" and s["status"] != "작업 중":
            word = "끝났어요" if s["status"] == "끝남" else f"{STALL_MIN}분 넘게 조용해요"
            alerts.append(f"[{s['project']}] {word}\n나: {s['user']}\nAI: {s['ai']}")
    if alerts:
        telegram("[세션 상황판]\n\n" + "\n\n".join(alerts))
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump({s["id"]: s["status"] for s in rows}, open(STATE, "w"), ensure_ascii=False)
    return alerts


def main():
    args = sys.argv[1:]
    hours = float(args[args.index("--hours") + 1]) if "--hours" in args else 24
    rows = sessions(hours if "--notify" not in args else 2)
    if "--notify" in args:
        for a in notify(rows):
            print(a.splitlines()[0])
    else:
        print_table(rows)


if __name__ == "__main__":
    main()
