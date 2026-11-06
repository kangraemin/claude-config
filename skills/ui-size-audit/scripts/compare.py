"""기준(iOS 코드 또는 Figma) 요소 JSON과 대상(Android 코드) 요소 JSON을 짝짓고 속성마다 비교한다. LLM 없음.

usage: compare.py ref.json target.json -o result.json [--map map.json] [--ios-assets DIR] [--android-res DIR] [--tol 0.5]
- 짝짓기: 두 화면 요소를 그려지는 순서(DFS)대로 늘어놓고 점수 최대 정렬(서열 정렬, Needleman-Wunsch 변형).
  점수 = 역할 같음 + 앵커(글자·그림 이름·식 이름) 같음 + 정의 이름 비슷 + 같은 숫자 속성 수.
- 그림(아이콘)은 틀 크기가 아니라 실제로 그려지는 그림 크기(glyph)를 계산해 비교한다.
  iOS SF 기호: glyph.swift 로 렌더해서 잼 / iOS 에셋: imageset 파일을 틀에 맞춰 렌더 / Android 벡터: 경로 경계 계산.
- 스택 간격은 spacing 값 대신 '실제 아이 사이 간격 목록'(spacing + 고정 Spacer)으로 비교한다.
"""
import argparse, json, os, re, subprocess, sys, glob, math
from functools import lru_cache
HERE = os.path.dirname(os.path.abspath(__file__))

SYN = [('person', 'user'), ('gearshape', 'setting'), ('gear', 'setting'), ('bell', 'notification'),
       ('chevron', 'arrow'), ('xmark', 'close'), ('magnifyingglass', 'search'), ('house', 'home'),
       ('mappin', 'location'), ('checkmark', 'check'), ('plus', 'add'), ('trash', 'delete'), ('ellipsis', 'more')]
NUM_KEYS = ('width', 'height', 'font.size', 'radius', 'spacing', 'border.width', 'shadow.radius', 'shadow.y')


def toks(s):
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s or '')
    t = set(x for x in re.split(r'[^a-z0-9]+', s.lower()) if x and x not in ('ic', 'mono', 'fill', 'sf', 'img', 'image', 'view', 'screen', 'main', 'w', 'fit', 'private', 'icon'))
    for a, b in SYN:
        if a in t: t.add(b)
        if b in t: t.add(a)
    return t


def sim(a, b):
    ta, tb = toks(a), toks(b)
    return len(ta & tb) / max(1, len(ta | tb)) if ta and tb else 0


ROLE_EQ = {('Shape', 'Box'), ('Box', 'Shape'), ('Group', 'Box'), ('Box', 'Group'), ('Component', 'Box'), ('Box', 'Component')}


def score(a, b, amap):
    if a['role'] == 'Spacer' or b['role'] == 'Spacer': return -1
    s = 0
    if a['role'] == b['role']: s += 3
    elif (a['role'], b['role']) in ROLE_EQ: s += 1
    elif 'Component' not in (a['role'], b['role']): s -= 4
    aa, ba = a.get('anchor'), b.get('anchor')
    if aa and ba:
        if aa[0] == 'text' and ba[0] == 'text':
            s += 10 if aa[1] == ba[1] else -3
        elif aa[1] and amap.get(aa[1]) == ba[1]: s += 10
        elif aa[0] in ('asset', 'symbol', 'component') and ba[0] in ('asset', 'component'):
            s += 8 * sim(aa[1], ba[1])
        elif aa[0] == 'expr' and ba[0] == 'expr':
            s += 6 if aa[1].lower() == ba[1].lower() else 3 * sim(aa[1], ba[1])
    s += 2 * sim(a.get('scope', ''), b.get('scope', ''))
    pa, pb = a['props'], b['props']
    same = sum(1 for k in NUM_KEYS if k in pa and k in pb and isinstance(pa[k]['value'], (int, float))
               and isinstance(pb[k]['value'], (int, float)) and abs(pa[k]['value'] - pb[k]['value']) < 0.01)
    s += min(same, 4)
    return s


def desc_anchors(els):
    kids = {}
    for e in els: kids.setdefault(e['parent'], []).append(e)
    memo = {}
    def go(e):
        if e['id'] in memo: return memo[e['id']]
        out = set()
        an = e.get('anchor')
        if an and an[0] != 'component': out.add(an[1].lower() if an[0] != 'text' else 't:' + an[1])
        for k in kids.get(e['id'], []): out |= go(k)
        memo[e['id']] = out; return out
    return {e['id']: go(e) for e in els}


def align(A, B, amap, thr=4):
    """순서에 묶이지 않는 탐욕 짝짓기. 1) 점수 + 아래쪽 앵커 겹침 으로 높은 것부터 2) 부모끼리 짝이면 가산해 남은 것 다시."""
    da, db = desc_anchors(A), desc_anchors(B)
    ia = {e['id']: i for i, e in enumerate(A)}; ib = {e['id']: j for j, e in enumerate(B)}
    base = {}
    for i, a in enumerate(A):
        for j, b in enumerate(B):
            sc = score(a, b, amap)
            if sc < 0: continue
            if a['role'] not in ('Text', 'Image', 'Spacer'):
                inter = len({x for x in da[a['id']] if x in db[b['id']] or amap.get(x) in db[b['id']]})
                uni = max(1, len(da[a['id']] | db[b['id']]))
                sc += 8 * inter / uni
            else:
                # 글자·그림은 같은 이름이 여러 군데 있다(행 아이콘 vs 아바타 아이콘). 부모 안 형제 앵커가 겹치는 쪽을 고른다
                pa_, pb_ = a['parent'], b['parent']
                if pa_ is not None and pb_ is not None:
                    sa_, sb_ = da.get(pa_, set()), db.get(pb_, set())
                    inter = len({x for x in sa_ if x in sb_ or amap.get(x) in sb_})
                    sc += 6 * inter / max(1, len(sa_ | sb_))
            base[(i, j)] = sc
    from collections import Counter
    ca = Counter(tuple(e['anchor']) for e in A if e.get('anchor')); cb = Counter(tuple(e['anchor']) for e in B if e.get('anchor'))
    def dup(e, c):
        an = e.get('anchor'); return an is not None and c[tuple(an)] > 1
    ma, mb = {}, {}
    for rnd in range(6):
        cand = []
        for (i, j), sc in base.items():
            if i in ma or j in mb: continue
            # 이름이 여러 번 나오는 글자·그림은 부모가 먼저 짝지어진 뒤에 고른다
            if rnd < 2 and A[i]['role'] in ('Text', 'Image') and (dup(A[i], ca) or dup(B[j], cb)): continue
            pa_, pb_ = A[i]['parent'], B[j]['parent']
            bonus = 0
            if pa_ is not None and pb_ is not None and ma.get(ia.get(pa_)) == ib.get(pb_): bonus += 4
            elif pa_ is None and pb_ is None: bonus += 2
            # 형제 순서 가까움
            cand.append((sc + bonus - 0.01 * abs(i / max(1, len(A)) - j / max(1, len(B))) * 10, i, j))
        cand.sort(reverse=True)
        added = 0
        for sc, i, j in cand:
            if sc < thr + (4 if rnd == 0 else 0): break
            if i in ma or j in mb: continue
            ma[i] = j; mb[j] = i; added += 1
        if not added and rnd > 1: break
    return sorted(ma.items())


# ---------- 그림 실제 크기 ----------
@lru_cache(None)
def sf_glyph(name, size, weight):
    out = subprocess.run(['swift', os.path.join(HERE, 'glyph.swift'), 'symbol', name, str(size), weight or 'regular'],
                         capture_output=True, text=True, timeout=120).stdout
    return json.loads(out) if out.strip().startswith('{') else None


@lru_cache(None)
def file_glyph(path, w, h):
    if path.endswith('.xml') or path.endswith('.svg'):
        try:
            out = subprocess.run([sys.executable, os.path.join(HERE, 'vector_bbox.py'), path, str(w), str(h)], capture_output=True, text=True, timeout=60).stdout
            d = json.loads(out)
            return {'glyph_w': d['glyph_w'], 'glyph_h': d['glyph_h'], 'how': f'vector_bbox {os.path.basename(path)} 틀 {w:g}×{h:g}'}
        except Exception:
            if path.endswith('.xml'): return None
    out = subprocess.run(['swift', os.path.join(HERE, 'glyph.swift'), 'file', path, str(w), str(h)], capture_output=True, text=True, timeout=120).stdout
    if out.strip().startswith('{') and 'glyph_w' in out:
        d = json.loads(out); d['how'] = f'glyph.swift {os.path.basename(path)} 틀 {w:g}×{h:g}'; return d
    return None


def find_ios_asset(root, name):
    if not root: return None
    for p in glob.glob(os.path.join(root, '**', f'{name}.imageset', '*'), recursive=True):
        if p.lower().endswith(('.svg', '.pdf', '.png')) and not p.endswith('@1x.png'):
            return p
    return None


def find_android_res(root, name):
    if not root: return None
    c = [p for p in glob.glob(os.path.join(root, '**', 'drawable*', f'{name}.*'), recursive=True) if '/build/' not in p]
    c.sort(key=lambda p: (not p.endswith('.xml'), 'xxxhdpi' not in p))
    return c[0] if c else None


def add_glyph(e, side, a):
    an = e.get('anchor'); p = e['props']
    if not an or e['role'] != 'Image': return
    w = p.get('width', {}).get('value'); h = p.get('height', {}).get('value')
    if side == 'ref' and an[0] == 'symbol' and isinstance(p.get('font.size', {}).get('value'), (int, float)):
        fs = p['font.size']['value']; wt = p.get('font.weight', {}).get('value') or 'regular'
        g = sf_glyph(an[1], round(fs, 3), wt)
        rot = p.get('rotation', {}).get('value')
        if g and isinstance(rot, (int, float)) and round(rot) % 180 == 90:
            g = dict(g); g['glyph_w'], g['glyph_h'] = g['glyph_h'], g['glyph_w']
        if g:
            how = f'SF 기호 {an[1]} 글자 {fs:g}pt {wt} 를 렌더해 잼(glyph.swift)'
            for k in ('w', 'h'):
                p[f'glyph.{k}'] = {'value': g[f'glyph_{k}'], 'expr': how, 'file': p['font.size']['file'], 'line': p['font.size']['line'], 'src': p['font.size']['src']}
            e['symbol_box'] = True
        return
    if not (isinstance(w, (int, float)) and isinstance(h, (int, float))): return
    path = e.get('asset_file') or (find_ios_asset(a.ios_assets, an[1]) if side == 'ref' else find_android_res(a.android_res, an[1]))
    if not path: return
    g = file_glyph(path, w, h)
    if g:
        for k in ('w', 'h'):
            p[f'glyph.{k}'] = {'value': g[f'glyph_{k}'], 'expr': g['how'], 'file': p['width']['file'], 'line': p['width']['line'], 'src': p['width']['src']}


# ---------- 아이 사이 간격 ----------
def gaps(e, els_by_parent, axis):
    kids = [k for k in els_by_parent.get(e['id'], []) if not k.get('via')]
    sp = e['props'].get('spacing', {}).get('value')
    if sp == 'default(≈8)': sp = 8.0
    if not isinstance(sp, (int, float)): sp = 0.0
    items = []
    for k in kids:
        if k['role'] == 'Spacer':
            v = k['props'].get('height' if axis == 'v' else 'width', {}).get('value')
            if not isinstance(v, (int, float)): v = k['props'].get('minLength', {}).get('value')
            fixed = isinstance(v, (int, float)) and not k['props'].get('fill.main')
            items.append(('sp', v if fixed else None))
        else:
            items.append(('it', k))
    out = []; acc = 0.0; flex = False; started = False; first = True
    for idx, (kind, v) in enumerate(items):
        if idx > 0: acc += sp
        if kind == 'sp':
            if v is None: flex = True
            else: acc += v
        else:
            out.append(('lead' if not started else 'gap', 'flex' if flex else round(acc, 2)))
            started = True; acc = 0.0; flex = False
    if started:
        out.append(('trail', 'flex' if flex else round(acc, 2)))
    return out


def infer_fill(els):
    """코드에 fill 이 안 적혀 있어도 늘어나는 요소를 표시한다.
    - 최상위 요소는 화면을 채운다.
    - 가로 스택(Row/HStack)에 늘어나는 Spacer·weight 아이가 있으면 가로로 늘어난다.
    - 아이가 가로로 늘어나면 부모(Column/Box/Group)도 가로로 늘어난다."""
    byid = {e['id']: e for e in els}; kids = {}
    for e in els: kids.setdefault(e['parent'], []).append(e)
    def mark(e, k, why):
        if k not in e['props']:
            e['props'][k] = {'value': True, 'expr': why, 'file': e['file'], 'line': e['line'], 'src': '(암묵) ' + why}
    for e in els:
        if e['parent'] is None and not e.get('via'):
            mark(e, 'fill.w', '최상위 요소'); mark(e, 'fill.h', '최상위 요소')
    changed = True
    while changed:
        changed = False
        for e in els:
            if 'fill.w' in e['props'] or 'width' in e['props'] or e['role'] not in ('Row', 'Column', 'Box', 'Group', 'Component', 'Scroll', 'Shape'): continue
            ks = [k for k in kids.get(e['id'], []) if not k.get('via')]
            flex = e['role'] == 'Row' and any(k['role'] == 'Spacer' and not any(x in k['props'] for x in ('width',)) or k['props'].get('fill.main') for k in ks)
            child = any(k['props'].get('fill.w') for k in ks if k['role'] != 'Spacer')
            if flex or child:
                mark(e, 'fill.w', '늘어나는 Spacer/weight 아이' if flex else '아이가 가로로 늘어남'); changed = True


def norm_val(k, v):
    if isinstance(v, str):
        v = v.lower().replace('centerhorizontally', 'center').replace('centervertically', 'center').replace('start', 'leading').replace('end', 'trailing')
    return v


def prop_table(a, b, tol):
    rows = []
    pa, pb = dict(a['props']), dict(b['props'])
    # 배경 없는 요소는 안쪽/바깥 여백 구분이 화면에 안 드러나므로 합쳐 비교
    for side in (pa, pb):
        for k in list(side):
            if k.startswith(('padding.', 'margin.')) and not (a.get('has_bg') and b.get('has_bg')):
                nk = 'space.' + k.split('.', 1)[1]
                if nk in side and isinstance(side[nk]['value'], (int, float)) and isinstance(side[k]['value'], (int, float)):
                    side[nk] = dict(side[nk]); side[nk]['value'] += side[k]['value']
                else:
                    side[nk] = side[k]
                del side[k]
    if a.get('symbol_box') and 'glyph.h' in pa:
        # SF 기호는 틀이 없다. 안드로이드 아이콘 틀·글자 크기는 참고, 실제 그림 크기로 판정
        for k in ('width', 'height', 'font.size', 'font.weight'):
            if k in pa: pa['info.' + k] = pa.pop(k)
            if k in pb: pb['info.' + k] = pb.pop(k)
    skip = {'spacing'}  # 간격은 gaps 로 비교
    for k in sorted(set(pa) | set(pb)):
        if k in skip or k.startswith('arg.'): continue
        ra, rb = pa.get(k), pb.get(k)
        va = ra['value'] if ra else None; vb = rb['value'] if rb else None
        if k.startswith('info.'):
            verdict = 'info'
        elif ra is None or rb is None:
            verdict = 'only_ref' if rb is None else 'only_target'
        elif isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            verdict = 'same' if abs(va - vb) <= tol else 'diff'
        elif va is None or vb is None:
            verdict = 'unresolved'
        elif k == 'shadow.color':
            verdict = 'check'  # 색은 이름이 달라 코드만으로 판정 안 함 → 근거 줄 둘 다 보여 줌
        else:
            verdict = 'same' if norm_val(k, va) == norm_val(k, vb) else 'diff'
        rows.append({'key': k, 'ref': ra, 'target': rb, 'verdict': verdict,
                     'delta': (vb - va) if isinstance(va, (int, float)) and isinstance(vb, (int, float)) else None})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref'); ap.add_argument('target'); ap.add_argument('-o', required=True)
    ap.add_argument('--map'); ap.add_argument('--ios-assets'); ap.add_argument('--android-res'); ap.add_argument('--tol', type=float, default=0.5)
    a = ap.parse_args()
    R = json.load(open(a.ref)); T = json.load(open(a.target))
    amap = {}
    if a.map and os.path.exists(a.map):
        mp = json.load(open(a.map)); amap = mp.get('assets', {})
    A = R['elements']; B = T['elements']
    infer_fill(A); infer_fill(B)
    for e in A: add_glyph(e, 'ref', a)
    for e in B: add_glyph(e, 'target', a)
    pairs = align(A, B, amap)
    byp_a, byp_b = {}, {}
    for e in A: byp_a.setdefault(e['parent'], []).append(e)
    for e in B: byp_b.setdefault(e['parent'], []).append(e)
    res = {'ref': R.get('entry'), 'target': T.get('entry'), 'tol': a.tol, 'pairs': [], 'only_ref': [], 'only_target': []}
    pa = {i for i, _ in pairs}; pb = {j for _, j in pairs}
    for i, j in pairs:
        ea, eb = A[i], B[j]
        rows = prop_table(ea, eb, a.tol)
        axis = {'Column': 'v', 'Row': 'h'}.get(ea['role'])
        if axis and ea['role'] == eb['role']:
            ga, gb = gaps(ea, byp_a, axis), gaps(eb, byp_b, axis)
            for idx in range(max(len(ga), len(gb))):
                x = ga[idx] if idx < len(ga) else None; y = gb[idx] if idx < len(gb) else None
                key = f'gap.{idx}:' + (x or y)[0]
                vx = x[1] if x else None; vy = y[1] if y else None
                if x is None or y is None: v = 'count_diff'
                elif isinstance(vx, float) and isinstance(vy, float): v = 'same' if abs(vx - vy) <= a.tol else 'diff'
                else: v = 'same' if vx == vy else 'diff'
                src_a = {'value': vx, 'expr': f"spacing {ea['props'].get('spacing', {}).get('value')} + 고정 Spacer", 'file': ea['file'], 'line': ea['line'], 'src': ea['props'].get('spacing', {}).get('src', '')}
                src_b = {'value': vy, 'expr': f"spacing {eb['props'].get('spacing', {}).get('value')} + 고정 Spacer", 'file': eb['file'], 'line': eb['line'], 'src': eb['props'].get('spacing', {}).get('src', '')}
                rows.append({'key': key, 'ref': src_a if x else None, 'target': src_b if y else None, 'verdict': v,
                             'delta': (vy - vx) if isinstance(vx, float) and isinstance(vy, float) else None})
        res['pairs'].append({'ref': {k: ea[k] for k in ('id', 'path', 'callee', 'role', 'anchor', 'file', 'line')},
                             'target': {k: eb[k] for k in ('id', 'path', 'callee', 'role', 'anchor', 'file', 'line')},
                             'score': score(ea, eb, amap), 'rows': rows,
                             'unknown_mods': {'ref': ea.get('unknown_mods', []), 'target': eb.get('unknown_mods', [])}})
    for i, e in enumerate(A):
        if i not in pa and e['props'] and e['role'] != 'Spacer':
            res['only_ref'].append({k: e[k] for k in ('id', 'path', 'callee', 'role', 'anchor', 'file', 'line', 'props')})
    for j, e in enumerate(B):
        if j not in pb and e['props'] and e['role'] != 'Spacer':
            res['only_target'].append({k: e[k] for k in ('id', 'path', 'callee', 'role', 'anchor', 'file', 'line', 'props')})
    json.dump(res, open(a.o, 'w'), ensure_ascii=False, indent=1)
    cnt = {}
    for p in res['pairs']:
        for r in p['rows']: cnt[r['verdict']] = cnt.get(r['verdict'], 0) + 1
    print(f"짝 {len(pairs)}쌍 · 속성 판정 {cnt} · 기준에만 {len(res['only_ref'])} · 대상에만 {len(res['only_target'])} → {a.o}")


if __name__ == '__main__':
    main()
