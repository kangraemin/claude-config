#!/usr/bin/env python3
"""Turns a raw gameplay recording (Playwright .webm, screen recording .mov, ...) into the rating-submission mp4,
and writes a contact sheet so the cut can be checked by eye.

Usage:
  finish_video.py raw.webm out.mp4 [--start S] [--end S] [--width 780] [--sheet sheet.png] [--sheet-only]
--start/--end trim (seconds in the raw file). Without them the whole file is kept.
Always look at the sheet: the first/last seconds of an automated run are often a loader or a reload screen.
Use --sheet-only to inspect the raw file before choosing the cut (1 frame per second).
"""
import argparse, subprocess, json


def duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path])
    return float(json.loads(out)["format"]["duration"])


def sheet(src, dst, start=0.0, end=None, per_sec=True):
    d = (end or duration(src)) - start
    n = max(1, min(60, int(d)))  # about one frame per second, at most 60
    cols = min(n, 12)
    rows = (n + cols - 1) // cols
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(start), "-t", str(d), "-i", src,
                           "-vf", "fps=%f,scale=120:-1,tile=%dx%d" % (n / d, cols, rows), "-frames:v", "1", dst])
    print("sheet: %s (%d frames, ~%.1fs apart, row-major from %.1fs)" % (dst, n, d / n, start))


ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("dst")
ap.add_argument("--start", type=float, default=0.0)
ap.add_argument("--end", type=float)
ap.add_argument("--width", type=int, default=780)
ap.add_argument("--sheet")
ap.add_argument("--sheet-only", action="store_true")
ap.add_argument("--audio", help="game sound captured by webaudio_tap.js (Playwright video has no sound)")
ap.add_argument("--audio-offset", type=float, default=0.0,
                help="seconds after the raw video start at which the audio begins (tap startedAt/1000)")
a = ap.parse_args()

if a.sheet_only:
    sheet(a.src, a.sheet or a.dst, a.start, a.end)
    raise SystemExit
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", a.src]
if a.audio:
    cmd += ["-itsoffset", str(a.audio_offset), "-i", a.audio, "-map", "0:v", "-map", "1:a"]
cmd += ["-ss", str(a.start)]  # output-side seek trims video and audio together
if a.end:
    cmd += ["-t", str(a.end - a.start)]
cmd += ["-vf", "scale=%d:-2:flags=lanczos,format=yuv420p" % a.width, "-c:v", "libx264", "-crf", "20",
        "-movflags", "+faststart", "-c:a", "aac", "-b:a", "128k", a.dst]
subprocess.check_call(cmd)
print("video: %s (%.1fs)" % (a.dst, duration(a.dst)))
sheet(a.dst, a.sheet or a.dst.rsplit(".", 1)[0] + "_sheet.png")
