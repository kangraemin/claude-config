"""화면 움직임을 숫자로 잰다 — "끊겨", "애니메이션 너무 빠름", "부드럽지 않다" 방지.

사용: python3 motion_check.py <url> [--click 선택자 ...] [--cpu 4] [--width 390]
하는 일:
  1. 폰 크기·CPU 느리게(기본 4배, 중급 폰 흉내)로 페이지를 연다.
  2. requestAnimationFrame으로 프레임 간격을 기록하면서 스크롤 3번 + 지정한 요소 클릭.
  3. 그동안 돈 애니메이션·트랜지션 길이를 모은다.
기준(넘으면 FAIL):
  - 끊긴 프레임(25ms 초과, 60fps에서 1.5프레임 이상) 5% 이하, 프레임 간격 p95 25ms 이하.
  - 애니메이션 길이 150~500ms (Material motion: 짧은 전환 150~250ms, 화면 전환 300~500ms).
    120ms 미만은 "너무 빠름"(2026-10-20 "애니메이션 빠르다고, 구글 공식 머티리얼 몇 초인데").
마지막 줄: RESULT PASS|FAIL <요약>
"""
import argparse
import json
import sys

from playwright.sync_api import sync_playwright

LOGGER = """
window.__ft=[];window.__anims=new Set();
(function loop(t){window.__ft.push(t);
  try{document.getAnimations().forEach(a=>{const d=a.effect&&a.effect.getTiming().duration;
    if(typeof d==='number'&&d>0) window.__anims.add((a.animationName||a.transitionProperty||'anim')+':'+Math.round(d));});}catch(e){}
  requestAnimationFrame(loop);})(performance.now());
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--click", nargs="*", default=[])
    ap.add_argument("--cpu", type=float, default=4)
    ap.add_argument("--width", type=int, default=390)
    a = ap.parse_args()
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": a.width, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
        cdp = pg.context.new_cdp_session(pg)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": a.cpu})
        pg.goto(a.url, wait_until="networkidle")
        pg.evaluate(LOGGER)
        for _ in range(3):
            pg.mouse.wheel(0, 900)
            pg.wait_for_timeout(700)
        for sel in a.click:
            try:
                pg.click(sel, timeout=3000)
                pg.wait_for_timeout(900)
            except Exception as e:
                print(f"클릭 실패 {sel}: {e.__class__.__name__}")
        ft = pg.evaluate("window.__ft")
        anims = pg.evaluate("[...window.__anims]")
        b.close()
    d = [y - x for x, y in zip(ft, ft[1:])]
    if len(d) < 30:
        print("RESULT FAIL 프레임 기록 부족")
        sys.exit(1)
    ds = sorted(d)
    p95 = ds[int(len(ds) * 0.95)]
    jank = sum(1 for x in d if x > 25) / len(d)
    durs = {}
    for s in anims:
        name, _, ms = s.rpartition(":")
        durs.setdefault(name, int(ms))
    fast = {k: v for k, v in durs.items() if v < 120}
    slow = {k: v for k, v in durs.items() if v > 600}
    print(json.dumps({"frames": len(d), "p95_ms": round(p95, 1), "jank_pct": round(jank * 100, 1),
                      "max_ms": round(max(d), 1), "animations_ms": durs}, ensure_ascii=False))
    fails = []
    if jank > 0.05:
        fails.append(f"끊김 {jank*100:.1f}%>5%")
    if p95 > 25:
        fails.append(f"p95 {p95:.0f}ms>25")
    if fast:
        fails.append(f"너무 빠름 {fast}")
    if slow:
        fails.append(f"너무 느림 {slow}")
    print(("RESULT FAIL " + "; ".join(fails)) if fails else f"RESULT PASS 끊김 {jank*100:.1f}% p95 {p95:.0f}ms")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
