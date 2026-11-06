"""Android vector drawable(.xml)·SVG 안의 그림이 차지하는 영역을 비율로 잰다. LLM 없음.

usage: vector_bbox.py <file.xml|file.svg> [틀폭 틀높이]
출력 JSON: viewport, glyph(뷰포트 단위), ratio(그림/뷰포트), 틀을 주면 aspect fit으로 그렸을 때 그림 크기(pt/dp)
곡선은 잘게 나눠 실제 경계를 구한다(제어점 bbox로 부풀리지 않음).
"""
import sys, re, json, math
import xml.etree.ElementTree as ET

TOK = re.compile(r'[MmZzLlHhVvCcSsQqTtAa]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?')


def path_points(d):
    toks = TOK.findall(d); i = 0; pts = []
    x = y = sx = sy = 0.0; cmd = None; lc = None; lq = None

    def num():
        nonlocal i
        v = float(toks[i]); i += 1; return v

    def cubic(p0, p1, p2, p3):
        for k in range(1, 25):
            t = k / 24; mt = 1 - t
            pts.append((mt**3*p0[0]+3*mt*mt*t*p1[0]+3*mt*t*t*p2[0]+t**3*p3[0], mt**3*p0[1]+3*mt*mt*t*p1[1]+3*mt*t*t*p2[1]+t**3*p3[1]))

    def quad(p0, p1, p2):
        for k in range(1, 25):
            t = k / 24; mt = 1 - t
            pts.append((mt*mt*p0[0]+2*mt*t*p1[0]+t*t*p2[0], mt*mt*p0[1]+2*mt*t*p1[1]+t*t*p2[1]))

    def arc(x1, y1, rx, ry, phi, fa, fs, x2, y2):
        if rx == 0 or ry == 0:
            pts.append((x2, y2)); return
        rx, ry = abs(rx), abs(ry); ph = math.radians(phi); c, s = math.cos(ph), math.sin(ph)
        dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
        x1p, y1p = c*dx + s*dy, -s*dx + c*dy
        lam = x1p**2/rx**2 + y1p**2/ry**2
        if lam > 1: rx *= math.sqrt(lam); ry *= math.sqrt(lam)
        num_ = rx*rx*ry*ry - rx*rx*y1p*y1p - ry*ry*x1p*x1p
        den = rx*rx*y1p*y1p + ry*ry*x1p*x1p
        co = math.sqrt(max(0, num_ / den)) if den else 0
        if fa == fs: co = -co
        cxp, cyp = co*rx*y1p/ry, -co*ry*x1p/rx
        cx, cy = c*cxp - s*cyp + (x1+x2)/2, s*cxp + c*cyp + (y1+y2)/2
        ang = lambda ux, uy, vx, vy: math.atan2(ux*vy - uy*vx, ux*vx + uy*vy)
        t1 = ang(1, 0, (x1p-cxp)/rx, (y1p-cyp)/ry)
        dt = ang((x1p-cxp)/rx, (y1p-cyp)/ry, (-x1p-cxp)/rx, (-y1p-cyp)/ry)
        if not fs and dt > 0: dt -= 2*math.pi
        elif fs and dt < 0: dt += 2*math.pi
        for k in range(1, 49):
            t = t1 + dt*k/48
            pts.append((cx + rx*math.cos(t)*c - ry*math.sin(t)*s, cy + rx*math.cos(t)*s + ry*math.sin(t)*c))

    while i < len(toks):
        if re.match(r'[A-Za-z]', toks[i]): cmd = toks[i]; i += 1
        rel = cmd.islower(); C = cmd.upper()
        ox, oy = (x, y) if rel else (0, 0)
        if C == 'Z':
            x, y = sx, sy; lc = lq = None; continue
        if C == 'M':
            x, y = ox + num(), oy + num(); sx, sy = x, y; pts.append((x, y)); cmd = 'l' if rel else 'L'
        elif C == 'L':
            x, y = ox + num(), oy + num(); pts.append((x, y))
        elif C == 'H':
            x = ox + num(); pts.append((x, y))
        elif C == 'V':
            y = oy + num(); pts.append((x, y))
        elif C == 'C':
            p1 = (ox+num(), oy+num()); p2 = (ox+num(), oy+num()); p3 = (ox+num(), oy+num())
            cubic((x, y), p1, p2, p3); lc = p2; x, y = p3
        elif C == 'S':
            p1 = (2*x - lc[0], 2*y - lc[1]) if lc else (x, y); p2 = (ox+num(), oy+num()); p3 = (ox+num(), oy+num())
            cubic((x, y), p1, p2, p3); lc = p2; x, y = p3
        elif C == 'Q':
            p1 = (ox+num(), oy+num()); p2 = (ox+num(), oy+num()); quad((x, y), p1, p2); lq = p1; x, y = p2
        elif C == 'T':
            p1 = (2*x - lq[0], 2*y - lq[1]) if lq else (x, y); p2 = (ox+num(), oy+num()); quad((x, y), p1, p2); lq = p1; x, y = p2
        elif C == 'A':
            rx, ry, phi, fa, fs = num(), num(), num(), num(), num(); x2, y2 = ox+num(), oy+num()
            arc(x, y, rx, ry, phi, int(fa), int(fs), x2, y2); x, y = x2, y2
        if C not in 'CS': lc = None
        if C not in 'QT': lq = None
    return pts


def num_attr(v):
    return float(re.match(r'[-\d.]+', v).group()) if v else None


def main():
    f = sys.argv[1]; root = ET.parse(f).getroot()
    A = '{http://schemas.android.com/apk/res/android}'
    allp = []
    if root.tag == 'vector':
        vw, vh = num_attr(root.get(A + 'viewportWidth')), num_attr(root.get(A + 'viewportHeight'))
        iw, ih = num_attr(root.get(A + 'width')), num_attr(root.get(A + 'height'))

        def walk(el, tf):
            if el.tag == 'group':
                tx, ty = float(el.get(A + 'translateX', 0)), float(el.get(A + 'translateY', 0))
                sx_, sy_ = float(el.get(A + 'scaleX', 1)), float(el.get(A + 'scaleY', 1))
                px, py = float(el.get(A + 'pivotX', 0)), float(el.get(A + 'pivotY', 0))
                tf = tf + [(tx, ty, sx_, sy_, px, py)]
            if el.tag == 'path' and el.get(A + 'pathData'):
                if el.get(A + 'fillColor') in ('#00000000', '@android:color/transparent') and not el.get(A + 'strokeColor'):
                    return
                # 선(stroke)으로 그린 경로는 선 굵기의 절반만큼 바깥으로 더 그려진다
                hw = (num_attr(el.get(A + 'strokeWidth')) or 0) / 2 if el.get(A + 'strokeColor') else 0
                for (x0, y0) in path_points(el.get(A + 'pathData')):
                    for dx, dy in ((0, 0),) if not hw else ((-hw, -hw), (hw, hw)):
                        x, y = x0 + dx, y0 + dy
                        for tx, ty, sx_, sy_, px, py in reversed(tf):
                            x = (x - px) * sx_ + px + tx; y = (y - py) * sy_ + py + ty
                        allp.append((x, y))
            for ch in el: walk(ch, tf)
        walk(root, [])
    else:  # svg
        vb = root.get('viewBox')
        vw, vh = (float(v) for v in vb.split()[2:]) if vb else (num_attr(root.get('width')), num_attr(root.get('height')))
        iw, ih = num_attr(root.get('width')), num_attr(root.get('height'))
        for el in root.iter():
            t = el.tag.split('}')[-1]
            if t == 'path' and el.get('d'):
                hw = (num_attr(el.get('stroke-width')) or 0) / 2 if el.get('stroke') not in (None, 'none') else 0
                for (x, y) in path_points(el.get('d')):
                    allp += [(x - hw, y - hw), (x + hw, y + hw)] if hw else [(x, y)]
            elif t in ('rect',):
                x, y, w, h = (float(el.get(k, 0)) for k in ('x', 'y', 'width', 'height')); allp += [(x, y), (x + w, y + h)]
            elif t in ('circle', 'ellipse'):
                cx, cy = float(el.get('cx', 0)), float(el.get('cy', 0)); rx = float(el.get('r', el.get('rx', 0))); ry = float(el.get('r', el.get('ry', 0)))
                allp += [(cx - rx, cy - ry), (cx + rx, cy + ry)]
    xs = [p[0] for p in allp]; ys = [p[1] for p in allp]
    g = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    out = {'file': f, 'viewport': [vw, vh], 'intrinsic': [iw, ih], 'glyph_vp': [round(v, 3) for v in g],
           'ratio_w': round(g[2] / vw, 4), 'ratio_h': round(g[3] / vh, 4)}
    if len(sys.argv) >= 4:
        bw, bh = float(sys.argv[2]), float(sys.argv[3])
        s = min(bw / vw, bh / vh)
        out['fit_box'] = [bw, bh]; out['glyph_w'] = round(g[2] * s, 2); out['glyph_h'] = round(g[3] * s, 2)
        out['glyph_x'] = round((bw - vw * s) / 2 + g[0] * s, 2); out['glyph_y'] = round((bh - vh * s) / 2 + g[1] * s, 2)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
