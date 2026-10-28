#!/usr/bin/env python3
"""Apps-in-Toss release images from real game captures.

Makes portrait screenshots 636x1048 (console needs >= 3) and the thumbnail 1932x828.
For App Store sizes add "shot_size": [1320, 2868], "shot_prefix": "ios69_", "shots_only": true to the spec. The capture itself is pasted
unedited (scaled, rounded corners); only a caption sits above it, so the images stay honest to the game.

Usage:
  store_images.py spec.json
spec.json:
  {
    "out": "docs/store",
    "name": "오늘의 눈썰미",            # thumbnail title
    "tagline": "하루 세 장, 매일 새 틀린그림찾기",
    "cta": "오늘의 3문제 시작",          # optional pill on the thumbnail
    "icon": "docs/store/icon_600.png",   # optional
    "colors": {"bg": "#FAF6EE", "panel": "#1F3A68", "accent": "#C54428", "title": "#1F3A68", "sub": "#6E6860"},
    "title_font": "path/to/display.ttf", # optional; default Apple SD Gothic Neo Bold
    "shots": [ {"path": "capture.png", "line1": "큰 문구", "line2": "작은 문구"}, ... ],
    "thumb_shots": [0, 1, 3]              # which shots appear on the thumbnail (default first 3)
  }
Paths are relative to the spec file's directory unless absolute. Landscape captures are fitted the same way.
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SD = "/System/Library/Fonts/AppleSDGothicNeo.ttc"  # index 2 = Regular-ish, 6 = Bold on macOS 14+


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load_font(path, size, index=0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except Exception:
        return ImageFont.truetype(SD, size, index=0)


def framed(path, max_w, max_h):
    """Capture scaled to fit max_w x max_h, rounded, white rim, soft shadow; returns RGBA with 24px padding."""
    im = Image.open(path).convert("RGB")
    s = min(max_w / im.width, max_h / im.height)
    w, h = round(im.width * s), round(im.height * s)
    im = im.resize((w, h), Image.LANCZOS)
    r = max(12, min(w, h) // 14)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    pad = 24
    c = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    sh = Image.new("L", c.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 6, pad + w, pad + h + 6), r, fill=70)
    c.paste((0, 0, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(10)))
    ImageDraw.Draw(c).rounded_rectangle((pad - 3, pad - 3, pad + w + 2, pad + h + 2), r + 3, fill=(255, 255, 255, 255))
    c.paste(im, (pad, pad), mask)
    return c


def fit_text(d, text, path, size, index, max_w):
    f = load_font(path, size, index)
    while d.textlength(text, font=f) > max_w and size > 14:
        size -= 2
        f = load_font(path, size, index)
    return f


def main(spec_path):
    base = os.path.dirname(os.path.abspath(spec_path))
    sp = json.load(open(spec_path))
    P = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    out = P(sp.get("out", "store"))
    os.makedirs(out, exist_ok=True)
    col = {"bg": "#FAF6EE", "panel": "#1F3A68", "accent": "#C54428", "title": "#1F3A68", "sub": "#6E6860"}
    col.update(sp.get("colors", {}))
    col = {k: hexrgb(v) for k, v in col.items()}
    tfont = P(sp["title_font"]) if sp.get("title_font") else SD
    tindex = 0 if sp.get("title_font") else 6
    shots = sp["shots"]
    if len(shots) < 3:
        sys.exit("need at least 3 shots (console minimum for portrait screenshots)")

    W, H = sp.get("shot_size", [636, 1048])  # App Store 6.9": [1320, 2868]
    k = W / 636
    prefix = sp.get("shot_prefix", "screenshot_")
    for i, s in enumerate(shots, 1):
        img = Image.new("RGB", (W, H), col["bg"])
        d = ImageDraw.Draw(img)
        f1 = fit_text(d, s.get("line1", ""), tfont, int(40 * k), tindex, W - 48 * k)
        d.text(((W - d.textlength(s.get("line1", ""), font=f1)) / 2, 40 * k), s.get("line1", ""), font=f1, fill=col["title"])
        f2 = fit_text(d, s.get("line2", ""), SD, int(26 * k), 2, W - 48 * k)
        d.text(((W - d.textlength(s.get("line2", ""), font=f2)) / 2, 98 * k), s.get("line2", ""), font=f2, fill=col["sub"])
        top = int(150 * k)
        p = framed(P(s["path"]), int(W - 80 * k), H - top - int(40 * k))
        img.paste(p, ((W - p.width) // 2, top + (H - top - p.height) // 2 - int(10 * k)), p)
        img.save(os.path.join(out, "%s%d.png" % (prefix, i)))
    if sp.get("shots_only"):
        print("wrote %d screenshots %dx%d to %s" % (len(shots), W, H, out))
        return

    W, H = 1932, 828
    img = Image.new("RGB", (W, H), col["bg"])
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 820, H), fill=col["panel"])
    y = 150
    if sp.get("icon"):
        icon = Image.open(P(sp["icon"])).convert("RGBA").resize((150, 150), Image.LANCZOS)
        m = Image.new("L", icon.size, 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, 149, 149), 34, fill=255)
        img.paste(icon, (96, y), m)
    tf = fit_text(d, sp["name"], tfont, 96, tindex, 680)
    d.text((96, 340), sp["name"], font=tf, fill=(255, 255, 255))
    gf = fit_text(d, sp.get("tagline", ""), SD, 40, 2, 680)
    d.text((100, 480), sp.get("tagline", ""), font=gf, fill=(232, 228, 218))
    if sp.get("cta"):
        cf = load_font(SD, 32, 4)
        tw = d.textlength(sp["cta"], font=cf)
        bw = max(374, tw + 80)
        d.rounded_rectangle((96, 570, 96 + bw, 640), 35, fill=col["accent"])
        d.text((96 + (bw - tw) / 2, 585), sp["cta"], font=cf, fill=(255, 255, 255))
    picks = [shots[i] for i in sp.get("thumb_shots", [0, 1, 2])][:3]
    slot = (W - 850 - 40) // len(picks)
    for n, s in enumerate(picks):
        p = framed(P(s["path"]), slot - 50, 690)
        img.paste(p, (850 + n * slot + (slot - p.width) // 2, (H - p.height) // 2), p)
    img.save(os.path.join(out, "thumbnail_1932x828.png"))
    print("wrote %d screenshots + thumbnail to %s" % (len(shots), out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "store_spec.json")
