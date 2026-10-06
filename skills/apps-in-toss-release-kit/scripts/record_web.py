#!/usr/bin/env python3
"""Records a web build (Unity WebGL or vite/granite dist) being played, for the rating video.

Usage:
  record_web.py <build_dir_or_url> <out_dir> [--query "?date=2026-10-06"] [--seconds 60] [--script play.py]
Serves the build dir on a local port (or opens the URL), records the page at phone size, and runs --script if given:
a Python file executed with `page`, `box` (canvas/body bounding box), `logs` (console lines) and `wait_log(prefix,
timeout)` in scope, which should play the game the way a person would (pauses of 1-2 s between taps so a reviewer
can follow). Without --script it just records --seconds of the first screen (only useful as a fallback).

Sound: webaudio_tap.js is injected so the game's own Web Audio output is saved as <out>/audio.webm with its start
offset; mux with finish_video.py --audio --audio-offset. Playwright's video alone is silent.

Lessons baked in:
- record_video_size equals the CSS viewport. With device_scale_factor 2 and a larger record size, frames flip
  between full-size and quarter-size whenever page.screenshot() runs. Upscale afterwards with finish_video.py.
- Headless Chrome screencasts the window, not the viewport: without --window-size equal to the viewport the video is a
  shrunken, cropped page on a gray letterbox (screenshots look fine, so only the video shows it).
- WebGL in headless Chrome needs swiftshader flags.
"""
import argparse, functools, http.server, os, threading, time
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("build")
ap.add_argument("out")
ap.add_argument("--query", default="")
ap.add_argument("--seconds", type=float, default=30)
ap.add_argument("--script")
ap.add_argument("--width", type=int, default=390)
ap.add_argument("--height", type=int, default=844)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

if a.build.startswith("http"):
    url = a.build + a.query
else:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *x):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=os.path.abspath(a.build)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d/index.html%s" % (srv.server_address[1], a.query)

logs = []
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True,
                          args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
                                "--autoplay-policy=no-user-gesture-required",
                                "--window-size=%d,%d" % (a.width, a.height)])
    vp = {"width": a.width, "height": a.height}
    page = b.new_page(viewport=vp, device_scale_factor=2, record_video_dir=a.out, record_video_size=vp)
    page.add_init_script(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "webaudio_tap.js"))
    page.on("console", lambda m: logs.append(m.text))
    t0 = time.time()
    page.goto(url)

    def wait_log(prefix, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            hit = [l for l in logs if prefix in l]
            if hit:
                return hit[-1]
            page.wait_for_timeout(200)
        raise SystemExit("timeout waiting for %s; last logs: %s" % (prefix, logs[-8:]))

    if a.script:
        page.wait_for_timeout(1000)
        el = page.query_selector("canvas") or page.query_selector("body")
        box = el.bounding_box()
        exec(open(a.script).read(), {"page": page, "box": box, "logs": logs, "wait_log": wait_log, "time": time})
    else:
        page.wait_for_timeout(a.seconds * 1000)
    print("RECORDED_SECONDS=%.1f" % (time.time() - t0))
    tap = page.evaluate("window.__tapStop ? window.__tapStop() : null")
    if tap and tap.get("b64"):
        import base64
        open(os.path.join(a.out, "audio.webm"), "wb").write(base64.b64decode(tap["b64"]))
        print("audio: %s offset=%.2f (pass to finish_video.py --audio-offset)" % (os.path.join(a.out, "audio.webm"), tap["startedAt"] / 1000))
    else:
        print("audio: none captured (game played no Web Audio?)")
    raw = page.video.path()
    page.close()
    b.close()
print("raw video:", raw)
