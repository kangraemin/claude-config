#!/usr/bin/env python3
"""폰 승인(카카오·QR·문자) 대기를 끝까지 지켜보게 강제하는 훅 (사용자 11/06 "무조건 지켜보게 훅으로라도 만들어").

PostToolUse(Bash): 출력에 승인 대기 신호가 있고 끝 결과(RESULT: OK/FAIL/...)가 없으면 표시 파일을 만든다.
                   끝 결과가 나오면 표시를 지운다.
Stop: 표시가 있으면(30분 이내) 멈추지 못하게 막고, 승인 완료를 직접 확인해 다음 단계를 이어 가라고 지시한다.
"""
import json, os, re, sys, time

DIR = os.path.expanduser("~/.cache/approval-watch")
TTL = 30 * 60
WAIT = re.compile(r"NEEDS_PHONE_APPROVAL|APPROVE_ON_PHONE|^QR\s+\S+\.png|인증\s*요청을\s*(?:보냈|승인)|휴대폰에서\s*승인|폰에서\s*승인|인증번호\s*대기", re.M)
WAIT_CMD = re.compile(r"naver_login\.py.*--qr|--qr\s+--notify|gov24_chobon\.py(?!.*--approved)")
DONE = re.compile(r"^RESULT:\s*(OK|FAIL|TIMEOUT|BLOCKED)\b", re.M)


def path(sid):
    return os.path.join(DIR, f"{sid or 'unknown'}.json")


def text_of(resp):
    if isinstance(resp, str):
        return resp
    if isinstance(resp, dict):
        return "\n".join(str(resp.get(k, "")) for k in ("stdout", "stderr", "output", "content"))
    return str(resp or "")


def post(d):
    if d.get("tool_name") != "Bash":
        return
    cmd = (d.get("tool_input") or {}).get("command", "")
    out = text_of(d.get("tool_response"))
    p = path(d.get("session_id"))
    waits = [m.start() for m in WAIT.finditer(out)]
    dones = [m.start() for m in DONE.finditer(out)]
    bg = bool((d.get("tool_input") or {}).get("run_in_background"))
    pending = (waits and (not dones or max(waits) > max(dones) or "NEEDS_PHONE_APPROVAL" in out)) or (bg and WAIT_CMD.search(cmd))
    if pending:
        os.makedirs(DIR, exist_ok=True)
        json.dump({"at": time.time(), "cmd": cmd[:300]}, open(p, "w"), ensure_ascii=False)
    elif dones and os.path.exists(p):
        os.remove(p)


def stop(d):
    p = path(d.get("session_id"))
    if not os.path.exists(p):
        return
    try:
        m = json.load(open(p))
    except Exception:
        os.remove(p); return
    if time.time() - m.get("at", 0) > TTL:
        os.remove(p); return
    print(json.dumps({"decision": "block", "reason": (
        "폰 승인 대기 중인 작업이 있다(" + m.get("cmd", "")[:120] + "). 사용자에게 '승인했어'를 기다리며 멈추지 마라. "
        "출력 파일·화면·상태를 직접 확인(Monitor until-loop 또는 짧은 폴링)해 승인되면 같은 턴에서 다음 단계(--approved 재실행 등)를 이어서 끝까지 해라. "
        "결과 줄 RESULT: OK/FAIL/TIMEOUT/BLOCKED가 Bash 출력에 나오면 이 막음은 풀린다. 30분이 지나면 자동 해제.")},
        ensure_ascii=False))


if __name__ == "__main__":
    try:
        d = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    ev = d.get("hook_event_name", "")
    (post if ev == "PostToolUse" else stop if ev == "Stop" else (lambda _: None))(d)
