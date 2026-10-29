#!/usr/bin/env python3
"""Chrome 창을 화면 왼쪽 반·오른쪽 반으로 나눠 둔다. 사용자 10/29 "화면 반은 다른세션 화면 반은 다른세션 이렇게쓸순없어".

  python3 win_split.py                      # 한 번 배치: Profile 1 창 → 왼쪽, 나머지 프로필(SNS 페르소나) 창 → 오른쪽
  python3 win_split.py --left "Profile 1" --left "Profile 4"   # 왼쪽에 둘 프로필을 바꾼다
  python3 win_split.py --loop 60            # 60초마다 새로 생긴 창·커진 창을 다시 제자리로 (tmux -L gh에서)
왜: 세션마다 chromectl front()가 자기 창을 맨 앞으로 올린다. 창이 모두 전체 화면 크기라 그때마다 화면 전체가 바뀌었다.
  창을 반씩 나누면 한 세션이 창을 올려도 자기 반만 바뀐다. 가려지지 않은 창은 Chrome이 렌더를 멈추지 않는다.
창 → 프로필은 AppleScript로 안 보인다 → 프로필마다 about:blank 탭을 열어 어느 창에 생기는지 보고 닫는다(새 창이 생기면 그 창도 닫는다).
기본 tmux에선 Apple 이벤트가 시간 초과 → tmux -L gh에서 돌린다. 마지막 줄 RESULT: OK <왼쪽 n> <오른쪽 n>.
"""
import argparse, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chromectl as c

PROFILES = ["Profile 1", "Profile 4", "Profile 5", "Profile 6", "Profile 7", "Profile 8", "Profile 9",
            "Profile 10", "Profile 11", "Profile 12", "Profile 13"]


def osa(s):
    return subprocess.run(["osascript", "-e", s], capture_output=True, text=True, timeout=60).stdout.strip()


def windows():
    out = osa('tell application "Google Chrome"\nset o to ""\nrepeat with w in windows\n'
              'set b to bounds of w\nset o to o & (id of w) & "," & (item 1 of b) & "," & (item 2 of b) & "," & (item 3 of b) & "," & (item 4 of b) & linefeed\n'
              'end repeat\nreturn o\nend tell')
    return {int(l.split(",")[0]): tuple(map(int, l.split(",")[1:])) for l in out.splitlines() if l.strip()}


def window_of_tab(tid):
    return int(osa(f'tell application "Google Chrome"\nrepeat with w in windows\n'
                   f'if (count of (tabs of w whose id = {tid})) > 0 then return id of w\nend repeat\nreturn 0\nend tell') or 0)


def profile_map():
    """{창 id: 프로필}. 그 프로필 창이 없으면 생긴 새 창을 닫고 건너뛴다."""
    m = {}
    for p in PROFILES:
        before = set(windows())
        try:
            tid = c.new_tab("about:blank", p, timeout=8).split(":")[1]
        except Exception:
            continue
        w = window_of_tab(tid)
        if w and w not in before:  # 그 프로필 창이 원래 없었다 → 방금 생긴 창을 닫는다
            osa(f'tell application "Google Chrome" to close (first window whose id = {w})')
            continue
        osa(f'tell application "Google Chrome" to close (first tab of (first window whose id = {w}) whose id = {tid})')
        if w:
            m[w] = p
    return m


def screen():
    # Finder는 자주 멈춘다 → AppKit으로 화면 크기(논리 픽셀)를 읽는다
    b = subprocess.run(["osascript", "-l", "JavaScript", "-e", "ObjC.import('AppKit');var f=$.NSScreen.mainScreen.frame;f.size.width+','+f.size.height"],
                       capture_output=True, text=True, timeout=20).stdout.strip()
    return tuple(int(float(x)) for x in b.split(","))


def place(m, left):
    W, H = screen()
    top = 25  # 메뉴 막대 아래
    cur = windows()
    n = [0, 0]
    for w, p in m.items():
        side = 0 if p in left else 1
        want = (0, top, W // 2, H) if side == 0 else (W // 2, top, W, H)
        n[side] += 1
        if cur.get(w) != want:
            osa(f'tell application "Google Chrome" to set bounds of (first window whose id = {w}) to {{{",".join(map(str, want))}}}')
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--left", action="append", help="왼쪽 반에 둘 프로필(기본 Profile 1)")
    ap.add_argument("--loop", type=int, default=0, help="N초마다 다시 맞춘다")
    a = ap.parse_args()
    left = set(a.left or ["Profile 1"])
    m = profile_map()
    n = place(m, left)
    print("RESULT: OK", n[0], n[1], flush=True)
    while a.loop:
        time.sleep(a.loop)
        try:
            if set(windows()) - set(m):  # 새 창이 생겼을 때만 다시 프로필을 알아낸다
                m = profile_map()
            place(m, left)
        except Exception as e:
            print("ERROR", e, flush=True)


if __name__ == "__main__":
    main()
