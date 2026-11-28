#!/usr/bin/env python3
"""블라인드 섞기: 우리 APNG/GIF와 LINE 상위 진짜 APNG를 같은 형식으로 섞어 판정용 폴더를 만든다.
사용: blind.py --ours a.png b.png ... --bench <bench폴더> --out <폴더> [--real 8] [--seed 1]
출력: <out>/sNN.gif(같은 배경·크기 320×300), <out>/sNN-frames.jpg(전 프레임 표), 정답키는 <out>/../<out이름>.key.json (판정자에게 주지 않는다)."""
import argparse, glob, json, random, os
from pathlib import Path
from PIL import Image, ImageSequence
ap = argparse.ArgumentParser(); ap.add_argument("--ours", nargs="+", required=True); ap.add_argument("--bench", required=True)
ap.add_argument("--out", required=True); ap.add_argument("--real", type=int, default=8); ap.add_argument("--seed", type=int, default=None)
a = ap.parse_args(); rnd = random.Random(a.seed)
W, H, BG = 320, 300, (255, 255, 255)
real = sorted(glob.glob(f"{a.bench}/*/*.png"))
# 세트마다 최대 1개씩 골고루
by = {}
for f in real: by.setdefault(Path(f).parent.name, []).append(f)
sets = rnd.sample(sorted(by), min(a.real, len(by))); pick = [rnd.choice(by[s]) for s in sets]
items = [("ours", f) for f in a.ours] + [("real", f) for f in pick]; rnd.shuffle(items)
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
for old in out.glob("s*"): old.unlink()
key = {}
for i, (k, f) in enumerate(items, 1):
    im = Image.open(f); fr = []; du = []
    for x in ImageSequence.Iterator(im):
        x = x.convert("RGBA"); s = min(W / x.width, H / x.height); x = x.resize((round(x.width * s), round(x.height * s)), Image.LANCZOS)
        c = Image.new("RGB", (W, H), BG); c.paste(x, ((W - x.width) // 2, (H - x.height) // 2), x); fr.append(c); du.append(x.info.get("duration", im.info.get("duration", 100)) or 100)
    name = f"s{i:02d}"; key[name] = dict(kind=k, src=f)
    fr[0].save(out / f"{name}.gif", save_all=True, append_images=fr[1:], duration=du, loop=0)
    cols = 5; rows = (len(fr) + cols - 1) // cols; g = Image.new("RGB", (W * cols, H * rows), (230, 230, 230))
    for j, x in enumerate(fr): g.paste(x, (j % cols * W, j // cols * H))
    g.save(out / f"{name}-frames.jpg", quality=88)
    (out / f"{name}-timing.txt").write_text(" ".join(map(str, du)) + f"  (합 {sum(du)}ms, {len(fr)}프레임)\n")
kf = out.parent / f".{out.name}.key.json"; kf.write_text(json.dumps(key, ensure_ascii=False, indent=1))
print("samples", len(items), "ours", len(a.ours), "key", kf)
