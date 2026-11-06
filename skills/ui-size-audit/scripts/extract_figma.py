"""Figma 노드 데이터에서 요소와 크기 속성을 뽑아 extract_code.py 와 같은 모양의 JSON으로 쓴다. LLM 없음.

입력 둘 중 하나:
  1) Figma MCP get_design_context 가 준 코드(React+Tailwind)를 저장한 파일 (.txt/.tsx)
  2) Figma REST API  GET /v1/files/<key>/nodes?ids=<id>  응답 JSON (.json)  — FIGMA_TOKEN 이 있을 때
usage: extract_figma.py <input> -o out.json [--name 화면이름]
"""
import argparse, json, re, sys, os

SKIP = ['bar/status', 'bar/navigation', 'bar/indicator']
TAIL = re.compile(r'(-?)([a-z-]+)-\[([^\]]+)\]')


def px(v):
    m = re.fullmatch(r'(-?[\d.]+)(px)?', v.strip())
    return float(m.group(1)) if m else None


def snake(name):
    n = re.sub(r'^img', '', name)
    n = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', n).lower()
    return n


def tw_props(cls, put):
    toks = cls.split()
    flex = 'flex' in toks or 'inline-flex' in toks
    col = 'flex-col' in toks
    for t in toks:
        m = re.fullmatch(r'(-?)([a-z-]+)-\[([^\]]+)\]', t)
        if m:
            neg, k, v = m.groups(); n = px(v)
            if n is not None and neg: n = -n
            if k == 'w' and n is not None: put('width', t, n)
            elif k == 'h' and n is not None: put('height', t, n)
            elif k == 'size' and n is not None: put('width', t, n); put('height', t, n)
            elif k == 'rounded' and n is not None: put('radius', t, n)
            elif k == 'gap' and n is not None: put('spacing', t, n)
            elif k in ('p', 'px', 'py', 'pt', 'pb', 'pl', 'pr') and n is not None:
                edges = {'p': ['top', 'bottom', 'leading', 'trailing'], 'px': ['leading', 'trailing'], 'py': ['top', 'bottom'],
                         'pt': ['top'], 'pb': ['bottom'], 'pl': ['leading'], 'pr': ['trailing']}[k]
                for e in edges: put(f'padding.{e}', t, n)
            elif k == 'text' and n is not None: put('font.size', t, n)
            elif k == 'leading' and n is not None: put('line.height', t, n)
            elif k == 'left' and n is not None: put('pos.x', t, n)
            elif k == 'top' and n is not None: put('pos.y', t, n)
            elif k == 'border' and n is not None: put('border.width', t, n)
            elif k == 'font':
                w = v.split(':')[-1].strip("'").lower()
                put('font.weight', t, w)
            elif k == 'shadow':
                parts = [p for p in re.split(r'_(?![^()]*\))', v) if p]
                nums = [px(p) for p in parts[:4]]
                if len(nums) >= 3 and None not in nums[:3]:
                    put('shadow.x', t, nums[0]); put('shadow.y', t, nums[1])
                    put('shadow.blur', t, nums[2]); put('shadow.radius', t + ' (blur÷2 = SwiftUI radius)', nums[2] / 2)
                    put('shadow.color', t, parts[-1])
            elif k == 'flex' and v.startswith('1'):
                put('fill.main', t, True)
        elif t == 'rounded-full': put('radius', t, 'circle')
        elif t == 'w-full': put('fill.w', t, True)
        elif t == 'h-full': put('fill.h', t, True)
        elif t == 'size-full': put('fill.w', t, True); put('fill.h', t, True)
        elif t == 'border': put('border.width', t, 1.0)
        elif t.startswith('items-') and flex:
            a = t[6:]; a = {'start': 'leading' if col else 'top', 'end': 'trailing' if col else 'bottom'}.get(a, a)
            put('align.h' if col else 'align.v', t, a)
        elif t.startswith('justify-') and flex:
            put('arrangement', t, t[8:])
        elif t.startswith('opacity-'):
            put('opacity', t, float(t[8:]) / 100)
    return ('Column' if col else 'Row') if flex else None


def parse_jsx(code):
    """함수 컴포넌트별 JSX를 태그 트리로. 반환: {함수이름: [root nodes]}, 이미지 변수→이름"""
    imgs = dict(re.findall(r'const (img\w+)\s*=\s*"([^"]+)"', code))
    funcs = {}
    for m in re.finditer(r'(?:export default )?function (\w+)\s*\([^)]*\)[^{]*\{\s*return \(', code):
        start = m.end(); depth = 1; i = start
        while i < len(code) and depth:
            if code[i] == '(': depth += 1
            elif code[i] == ')': depth -= 1
            i += 1
        funcs[m.group(1)] = code[start:i - 1]
    return funcs, imgs


TAG = re.compile(r'<(/?)([A-Za-z][\w.]*)((?:\s+[\w-]+(?:=(?:"[^"]*"|\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}))?)*)\s*(/?)>', re.S)


def build(jsx, funcs, imgs, line_of, depth=0, override=None):
    nodes = []; stack = []; pos = 0
    for m in TAG.finditer(jsx):
        text = jsx[pos:m.start()]
        if stack and text.strip() and not text.strip().startswith('{'):
            stack[-1]['text'] = (stack[-1].get('text', '') + text.strip())
        pos = m.end()
        close, tag, attrs, selfclose = m.groups()
        if close:
            if stack: stack.pop()
            continue
        at = dict(re.findall(r'([\w-]+)=(?:"([^"]*)")', attrs))
        cls = at.get('className', '')
        mcls = re.search(r'className=\{className \|\| "([^"]*)"\}', attrs)
        if mcls: cls = override if override else mcls.group(1)
        src = re.search(r'src=\{(\w+)\}', attrs)
        node = {'tag': tag, 'cls': cls, 'id': at.get('data-node-id'), 'name': at.get('data-name'),
                'img': src.group(1) if src else None, 'kids': [], 'line': line_of(m.start())}
        if tag[0].isupper() and tag in funcs and depth < 5:
            sub = build(funcs[tag], funcs, imgs, line_of, depth + 1, override=cls or None)
            node['kids'] = sub; node['component'] = tag
        (stack[-1]['kids'] if stack else nodes).append(node)
        if not selfclose and not (tag[0].isupper() and tag in funcs):
            stack.append(node)
    return nodes


def from_code(path, name):
    code = open(path, encoding='utf-8').read()
    funcs, imgs = parse_jsx(code)
    root_fn = re.search(r'export default function (\w+)', code).group(1)
    line_of = lambda p: 0
    tree = build(funcs[root_fn], funcs, imgs, line_of)
    els = []; seq = [0]

    def text_of(n):
        if n.get('text'): return n['text']
        for k in n['kids']:
            t = text_of(k)
            if t: return t
        return None

    def walk(n, parent, path):
        if SKIP and n.get('name') and any(n['name'].startswith(k) for k in SKIP):
            return None
        # 이미지 한 장만 감싼 껍데기 div 는 그 이미지 노드로 본다
        el = {'id': seq[0], 'parent': parent, 'path': path, 'scope': path.split('/')[-1], 'inst': 'root',
              'callee': n['tag'], 'role': None, 'via': None, 'file': path_file, 'line': 0,
              'anchor': None, 'props': {}, 'args': {}, 'figma_id': n['id'], 'figma_name': n['name']}
        seq[0] += 1
        put = lambda k, tok, v: el['props'].__setitem__(k, {'value': v, 'expr': tok, 'file': path_file, 'line': 0,
                                                             'src': f"node {n['id'] or '?'} {n['name'] or ''} `{tok}`"})
        stack_role = tw_props(n['cls'], put)
        imgk = [k for k in n['kids'] if k['tag'] == 'img']
        if n['tag'] == 'p':
            return None
        ps = [k for k in n['kids'] if k['tag'] == 'p']
        if ps and len(n['kids']) == len(ps):
            el['role'] = 'Text'; el['anchor'] = ('text', ''.join(p.get('text', '') for p in ps))
            # 글자 노드 크기는 Figma 글상자라 비교에서 뺀다
            for k in ('width', 'height', 'pos.x', 'pos.y'):
                el['props'].pop(k, None)
        elif imgk and len(n['kids']) == len(imgk):
            el['role'] = 'Image'
            nm = (n['name'] or snake(imgk[0]['img'] or '')).replace('/', '_').replace(' ', '_').lower()
            el['anchor'] = ('asset', nm if nm.startswith(('ic_', 'img_')) else snake(imgk[0]['img'] or nm))
            if imgk[0]['img'] in imgs: el['asset_url'] = imgs[imgk[0]['img']]
        elif n.get('component') and re.match(r'(Ic|Img)[A-Z0-9]', n['component']):
            # 아이콘 컴포넌트(IcUserMono 등)는 그림 하나로 본다 → 에셋 이름 ic_user_mono
            el['role'] = 'Image'; el['anchor'] = ('asset', snake(n['component']))
            ik = [k for k in n['kids'] if k.get('img')] or [g for k in n['kids'] for g in k['kids'] if g.get('img')]
            if ik and ik[0]['img'] in imgs: el['asset_url'] = imgs[ik[0]['img']]
        else:
            el['role'] = stack_role or ('Component' if n.get('component') else 'Box')
            if n.get('component'): el['anchor'] = ('component', n['component'])
        r = el['props'].get('radius')
        w, h = el['props'].get('width', {}).get('value'), el['props'].get('height', {}).get('value')
        if r and isinstance(r['value'], float) and isinstance(w, float) and isinstance(h, float) and r['value'] >= min(w, h) / 2:
            r['value'] = 'circle'; r['expr'] += ' (≥ 짧은 변/2 → 원)'
        if el['role'] in ('Column', 'Row') and 'spacing' not in el['props']:
            put('spacing', '(gap 없음)', 0.0)
        els.append(el)
        if el['role'] not in ('Text', 'Image'):
            for k in n['kids']:
                walk(k, el['id'], path + ('/' + n['component'] if n.get('component') else ''))
        return el

    path_file = os.path.basename(path)
    for n in tree: walk(n, None, name)
    return els


def from_rest(path, name):
    d = json.load(open(path)); nodes = d.get('nodes', {})
    root = next(iter(nodes.values()))['document']
    els = []; seq = [0]; path_file = os.path.basename(path)

    def walk(n, parent, ox, oy):
        if SKIP and any(n.get('name', '').startswith(k) for k in SKIP):
            return
        el = {'id': seq[0], 'parent': parent, 'path': name, 'scope': name, 'inst': 'root', 'callee': n['type'], 'role': 'Box',
              'via': None, 'file': path_file, 'line': 0, 'anchor': None, 'props': {}, 'args': {}, 'figma_id': n['id'], 'figma_name': n.get('name')}
        seq[0] += 1
        put = lambda k, tok, v: el['props'].__setitem__(k, {'value': v, 'expr': tok, 'file': path_file, 'line': 0, 'src': f"node {n['id']} {n.get('name', '')} `{tok}`"})
        bb = n.get('absoluteBoundingBox') or {}
        if bb:
            put('width', 'absoluteBoundingBox.width', float(bb['width'])); put('height', 'absoluteBoundingBox.height', float(bb['height']))
            put('pos.x', 'absoluteBoundingBox.x', float(bb['x'] - ox)); put('pos.y', 'absoluteBoundingBox.y', float(bb['y'] - oy))
        if n.get('layoutMode') in ('VERTICAL', 'HORIZONTAL'):
            el['role'] = 'Column' if n['layoutMode'] == 'VERTICAL' else 'Row'
            put('spacing', 'itemSpacing', float(n.get('itemSpacing', 0)))
            for k, e in (('paddingTop', 'top'), ('paddingBottom', 'bottom'), ('paddingLeft', 'leading'), ('paddingRight', 'trailing')):
                if n.get(k): put(f'padding.{e}', k, float(n[k]))
            ca = n.get('counterAxisAlignItems', 'MIN')
            put('align.h' if el['role'] == 'Column' else 'align.v', 'counterAxisAlignItems', {'MIN': 'leading' if el['role'] == 'Column' else 'top', 'CENTER': 'center', 'MAX': 'trailing' if el['role'] == 'Column' else 'bottom'}.get(ca, ca.lower()))
        if n.get('layoutSizingHorizontal') == 'FILL' or n.get('layoutAlign') == 'STRETCH': put('fill.w', 'layoutSizingHorizontal=FILL', True)
        if n.get('layoutSizingVertical') == 'FILL': put('fill.h', 'layoutSizingVertical=FILL', True)
        if n.get('layoutGrow') == 1: put('fill.main', 'layoutGrow=1', True)
        if 'cornerRadius' in n:
            w, h = bb.get('width', 0), bb.get('height', 0)
            put('radius', 'cornerRadius', 'circle' if n['cornerRadius'] >= min(w, h) / 2 else float(n['cornerRadius']))
        for s in n.get('strokes', []):
            if s.get('visible', True): put('border.width', 'strokeWeight', float(n.get('strokeWeight', 1)))
        for ef in n.get('effects', []):
            if ef.get('type') == 'DROP_SHADOW' and ef.get('visible', True):
                put('shadow.x', 'effects.offset.x', float(ef['offset']['x'])); put('shadow.y', 'effects.offset.y', float(ef['offset']['y']))
                put('shadow.blur', 'effects.radius', float(ef['radius'])); put('shadow.radius', 'effects.radius÷2', float(ef['radius']) / 2)
                c = ef['color']; put('shadow.color', 'effects.color', f"rgba({c['r']*255:.0f},{c['g']*255:.0f},{c['b']*255:.0f},{c['a']:.2f})")
        if n['type'] == 'TEXT':
            el['role'] = 'Text'; el['anchor'] = ('text', n.get('characters', ''))
            st = n.get('style', {})
            if 'fontSize' in st: put('font.size', 'style.fontSize', float(st['fontSize']))
            if 'fontWeight' in st: put('font.weight', 'style.fontWeight', {400: 'regular', 500: 'medium', 600: 'semibold', 700: 'bold'}.get(st['fontWeight'], str(st['fontWeight'])))
            if 'lineHeightPx' in st: put('line.height', 'style.lineHeightPx', float(st['lineHeightPx']))
            for k in ('width', 'height', 'pos.x', 'pos.y'): el['props'].pop(k, None)
        elif n['type'] in ('VECTOR', 'BOOLEAN_OPERATION') or (n['type'] in ('INSTANCE', 'COMPONENT', 'FRAME') and (n.get('name', '').startswith(('ic/', 'ic_', 'img')))):
            el['role'] = 'Image'; el['anchor'] = ('asset', n.get('name', '').replace('/', '_').lower())
        els.append(el)
        if el['role'] not in ('Text', 'Image'):
            for k in n.get('children', []):
                if k.get('visible', True): walk(k, el['id'], ox, oy)
    rb = root.get('absoluteBoundingBox', {'x': 0, 'y': 0})
    walk(root, None, rb['x'], rb['y'])
    return els


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input'); ap.add_argument('-o', required=True); ap.add_argument('--name', default='figma')
    ap.add_argument('--skip', default=','.join(SKIP), help='이 이름으로 시작하는 노드는 뺀다(상태바·탭바처럼 화면 코드 밖에 있는 것). 빈 값이면 안 뺌')
    ap.add_argument('--assets-dir', help='그림 에셋(svg)을 받아 둘 폴더. 주면 compare 가 그림 실제 크기(glyph)를 잰다')
    a = ap.parse_args()
    SKIP[:] = [k for k in a.skip.split(',') if k]
    els = from_rest(a.input, a.name) if a.input.endswith('.json') else from_code(a.input, a.name)
    if a.assets_dir:
        # Figma MCP 에셋 주소는 7일 뒤 만료된다. 받아 둔 svg 로 실제 그림(glyph) 크기를 잰다
        import urllib.request
        os.makedirs(a.assets_dir, exist_ok=True); got = {}
        for e in els:
            u = e.get('asset_url')
            if not u: continue
            if u not in got:
                f = os.path.join(a.assets_dir, e['anchor'][1] + os.path.splitext(u)[1])
                try:
                    if not os.path.exists(f) or os.path.getsize(f) == 0:
                        import subprocess
                        subprocess.run(['curl', '-sfL', '-o', f, u], check=True, timeout=60)
                    got[u] = f if os.path.getsize(f) > 0 else None
                except Exception as ex:
                    print('에셋 못 받음', u, ex, file=sys.stderr); got[u] = None
            if got[u]: e['asset_file'] = got[u]
    json.dump({'entry': a.name, 'lang': 'figma', 'elements': els}, open(a.o, 'w'), ensure_ascii=False, indent=1)
    print(f'{a.name}: 요소 {len(els)}개, 속성 {sum(len(e["props"]) for e in els)}개 → {a.o}')


if __name__ == '__main__':
    main()
