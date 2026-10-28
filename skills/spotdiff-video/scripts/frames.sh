#!/bin/bash
# usage: frames.sh <video> <out.png> <t1> [t2 ...] — grabs frames at the given seconds into one contact sheet (3 per row)
# Read the sheet yourself before sending; a passing render can still look wrong.
set -e
v="$1"; out="$2"; shift 2
tmp=$(mktemp -d)
i=0
for t in "$@"; do
  ffmpeg -v error -y -ss "$t" -i "$v" -frames:v 1 -vf scale=640:-1 "$tmp/$(printf %03d $i).png"
  i=$((i + 1))
done
python3 - "$tmp" "$out" <<'EOF'
import glob, sys
from PIL import Image
fs = sorted(glob.glob(sys.argv[1] + "/*.png"))
ims = [Image.open(f) for f in fs]
w, h = ims[0].size
cols = min(3, len(ims)); rows = (len(ims) + cols - 1) // cols
c = Image.new("RGB", (w * cols, h * rows), "white")
for i, im in enumerate(ims):
    c.paste(im, ((i % cols) * w, (i // cols) * h))
c.save(sys.argv[2])
print(sys.argv[2])
EOF
rm -rf "$tmp"
