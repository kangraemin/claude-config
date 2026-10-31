"""네이버 이미지 검색으로 실사진 표본을 모은다.

사용: python3 naver_image_collect.py --out <폴더> [--scrolls 4] [--min 300] 검색어 [검색어 ...]

하는 일:
  1. 실제 Chrome으로 검색어마다 네이버 이미지 검색을 열고 스크롤해 썸네일의 원본 URL(src=)을 뽑는다 → <out>/urls.tsv
  2. 원본 blogfiles/cafefiles를 Referer blog.naver.com으로 받는다(동시 6개) → <out>/img/<md5 10자>.jpg, <out>/index.tsv
  3. 짧은 변 <min>px 미만·깨진 파일을 지우고, 육안 검수용 접촉 시트를 만든다 → <out>/sheetNN.jpg (8x6, 파일명 표시)

사전 조건: chrome-direct chromectl이 동작하는 Mac Chrome. Claude 셸에서 -1743이 나면 Ghostty로 돌린다.
왜 화면 조작인가: curl로 search.naver.com 이미지 검색을 부르면 보안문자가 뜬다.
함정:
  - search.pstatic.net 썸네일에 type=w966을 붙이면 404, 반복하면 429. 원본 URL만 쓴다.
  - Bing 이미지 검색은 한국어 질의에 무관한 이미지를 준다.
  - 검색어 라벨 ≠ 내용. 접촉 시트를 직접 보고 고른다.
멱등: 이미 받은 파일은 다시 받지 않는다. urls.tsv는 덧붙이고 중복 원본은 건너뛴다.
"""
import argparse, glob, hashlib, os, subprocess, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.expanduser("~/.claude/skills/chrome-direct"))
import chromectl as c


def search(qy, scrolls):
    url = "https://search.naver.com/search.naver?where=image&query=" + urllib.parse.quote(qy)
    tab = c.new_tab(url)
    try:
        time.sleep(4)
        for _ in range(scrolls):
            c.run_js(tab, "window.scrollBy(0, 3000)"); time.sleep(1.5)
        res = c.js_json(tab, """
          const out=[];
          document.querySelectorAll('img').forEach(i=>{
            const s=i.currentSrc||i.src||''; if(!s.includes('search.pstatic.net')) return;
            const a=i.closest('a'); out.push([s, a?a.href:'']);
          });
          return out;""") or []
    finally:
        c.close_tab(tab)
    rows = []
    for s, href in res:
        orig = urllib.parse.parse_qs(urllib.parse.urlparse(s).query).get("src", [""])[0]
        if orig:
            rows.append((qy, orig, href))
    return rows


def fetch(out, row):
    qy, orig, href = row
    h = hashlib.md5(orig.encode()).hexdigest()[:10]
    f = f"{out}/img/{h}.jpg"
    if not os.path.exists(f):
        subprocess.run(["curl", "-sL", "-m", "20", "-A", "Mozilla/5.0", "-e", "https://blog.naver.com/", "-o", f, orig])
    return h, qy, orig, href


def sheets(out, files, T=200):
    from PIL import Image, ImageDraw
    for p in range(0, len(files), 48):
        sheet = Image.new("RGB", (T * 8, T * 6), "white"); d = ImageDraw.Draw(sheet)
        for k, f in enumerate(files[p:p + 48]):
            im = Image.open(f).convert("RGB"); im.thumbnail((T - 6, T - 18))
            x, y = (k % 8) * T, (k // 8) * T
            sheet.paste(im, (x + 3, y + 16)); d.text((x + 4, y + 2), os.path.basename(f)[:10], fill="red")
        sheet.save(f"{out}/sheet{p // 48:02d}.jpg", quality=80)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--scrolls", type=int, default=4)
    ap.add_argument("--min", type=int, default=300)
    ap.add_argument("queries", nargs="+")
    a = ap.parse_args()
    from PIL import Image
    os.makedirs(f"{a.out}/img", exist_ok=True)

    seen = set()
    if os.path.exists(f"{a.out}/urls.tsv"):
        seen = {l.split("\t")[1] for l in open(f"{a.out}/urls.tsv") if "\t" in l}
    new = []
    for qy in a.queries:
        rows = [r for r in search(qy, a.scrolls) if r[1] not in seen]
        for r in rows:
            seen.add(r[1])
        new += rows
        print(f"{qy}: 새 URL {len(rows)}")
    with open(f"{a.out}/urls.tsv", "a") as fp:
        fp.writelines("\t".join(r) + "\n" for r in new)

    rows = [tuple(l.rstrip("\n").split("\t")) for l in open(f"{a.out}/urls.tsv")]
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda r: fetch(a.out, r), rows))
    open(f"{a.out}/index.tsv", "w").write("".join("\t".join(r) + "\n" for r in res))

    ok = []
    for f in sorted(glob.glob(f"{a.out}/img/*.jpg")):
        try:
            im = Image.open(f); im.load()
            if min(im.size) >= a.min:
                ok.append(f)
        except Exception:
            os.remove(f)
    sheets(a.out, ok)
    print(f"RESULT: urls={len(rows)} images={len(ok)} sheets={(len(ok) + 47) // 48} out={a.out}")


if __name__ == "__main__":
    main()
