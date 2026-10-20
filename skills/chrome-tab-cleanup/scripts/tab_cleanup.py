#!/usr/bin/env python3
"""쓸모없는 Chrome 탭을 닫는다. 기본은 미리보기(--apply 있을 때만 닫음).

사용: python3 tab_cleanup.py [--apply] [--keep 문자열]... [--close 문자열]... [--json]

- 페르소나별 핵심 SNS 탭(창마다 서비스당 1개)과 사람 몫 화면(얼굴 인증 등)만 남기고 나머지를 닫는다.
- 같은 창의 같은 URL 중복, 같은 서비스 두 번째 탭도 닫는다.
- 10분 안에 새로 열린 로그인 탭(다른 세션이 쓰는 중)은 --keep으로 지키라고 미리보기에 표시한다.

왜 AppleScript를 직접 쓰나: 다른 세션의 Playwright가 실제 Chrome 바이너리를 두 번째 인스턴스로 띄우면
`tell application "Google Chrome"`이 가끔 그쪽을 잡아 창 1개·탭 1개만 보인다(2026-10-20).
그래서 여러 번 읽어 탭이 가장 많은 결과를 쓰고, 닫을 땐 창 id·탭 id로 가리켜 실패하면 다시 시도한다.
"""
import argparse, json, re, subprocess, sys, time

LIST = '''set o to ""
tell application "Google Chrome"
  repeat with w in every window
    set wid to id of w
    repeat with t in every tab of w
      set o to o & wid & "\\t" & (id of t) & "\\t" & (URL of t) & "\\t" & (title of t) & linefeed
    end repeat
  end repeat
end tell
return o'''

# 남길 탭: (서비스 키, URL 정규식). 창마다 서비스 키당 첫 탭 1개만 남긴다.
KEEP = [
    ("x", r"^https://x\.com/(home|[A-Za-z0-9_]+)/?$"),
    ("x-signup", r"x\.com/i/jf/onboarding"),          # 가입 중 얼굴 인증 = 사용자 몫
    ("instagram", r"^https://www\.instagram\.com/"),
    ("threads", r"^https://www\.threads\.com/@[^/]+/?(\?.*)?$"),
    ("linkedin", r"^https://www\.linkedin\.com/feed/"),
    ("linkedin-company", r"^https://www\.linkedin\.com/company/[^/]+/admin/"),
    ("gmail", r"^https://mail\.google\.com/"),
]


def osa(script, timeout=60):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
    if r.returncode: raise RuntimeError(r.stderr.strip())
    return r.stdout


def list_tabs(tries=8):
    best = []
    for _ in range(tries):
        try: out = osa(LIST)
        except Exception: out = ""
        rows = [l.split("\t", 3) for l in out.splitlines() if l.count("\t") >= 3]
        if len(rows) > len(best): best = rows
        if len({r[0] for r in best}) > 1: break   # 창이 2개 이상 보이면 진짜 Chrome
        time.sleep(1.5)
    return [dict(win=w, tab=t, url=u, title=ti) for w, t, u, ti in best]


def close(win, tab, tries=5):
    for _ in range(tries):
        try:
            osa(f'tell application "Google Chrome" to close (first tab of (first window whose id = {win}) whose id = {tab})')
            return True
        except Exception:
            time.sleep(1)
    return False


def plan(tabs, keep_extra, close_extra):
    kept, seen = set(), set()
    out = []
    for t in tabs:
        u = t["url"]
        key = None
        if not any(s in u for s in close_extra):
            if any(s in u for s in keep_extra): key = ("extra", t["tab"])
            else: key = next((k for k, rx in KEEP if re.search(rx, u)), None)
        dup = (t["win"], u) in seen
        seen.add((t["win"], u))
        keep = key is not None and not dup and (t["win"], key) not in kept
        if keep: kept.add((t["win"], key))
        out.append({**t, "keep": keep, "why": ("keep:" + (key[0] if isinstance(key, tuple) else key)) if keep
                    else "중복" if dup else "같은 서비스 2번째" if key else "핵심 아님"})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--keep", action="append", default=[], help="URL에 이 문자열이 있으면 남김")
    ap.add_argument("--close", action="append", default=[], help="URL에 이 문자열이 있으면 핵심이어도 닫음")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    tabs = list_tabs()
    if len({t["win"] for t in tabs}) <= 1:
        print("RESULT: BLOCKED 창이 1개만 보임 — 다른 Chrome 인스턴스를 잡았을 수 있음. 다시 실행"); sys.exit(2)
    p = plan(tabs, a.keep, a.close)
    if a.json: print(json.dumps(p, ensure_ascii=False, indent=1))
    for t in p:
        print(("KEEP " if t["keep"] else "CLOSE"), t["win"], t["why"], (t["title"] or t["url"])[:60], "|", t["url"][:90])
    targets = [t for t in p if not t["keep"]]
    if not a.apply:
        print(f"RESULT: DRY-RUN 닫을 탭 {len(targets)}개 / 전체 {len(p)}개 (--apply로 실행)"); return
    fail = [t for t in targets if not close(t["win"], t["tab"])]
    print(f"RESULT: OK 닫음 {len(targets) - len(fail)}개, 실패 {len(fail)}개, 남음 {len(p) - len(targets) + len(fail)}개")


if __name__ == "__main__":
    main()
