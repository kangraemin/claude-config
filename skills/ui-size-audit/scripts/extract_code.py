"""iOS(SwiftUI)·Android(Compose) 코드에서 화면 요소와 크기 속성을 뽑아 JSON으로 쓴다. LLM 없음.

usage: extract_code.py --root <소스폴더> --entry <정의이름> [--files a.swift b.swift ...] -o out.json
  --entry: 화면 최상위 정의(예: RankingView / RankingScreen). 여기서 호출하는 하위 정의를 인자 값 넣어 펼친다.
  --files 생략 시 root 아래 같은 언어 파일 전체에서 정의를 찾는다(공통 컴포넌트 포함).
출력 요소마다: path(정의 경로), role, anchor, props{키: {value, expr, file, line, src}}
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from codeparse import Parser, collect_defs, evaluate, split_args

SF_TEXT_STYLES = {'largeTitle': 34, 'title': 28, 'title2': 22, 'title3': 20, 'headline': 17, 'body': 17,
                  'callout': 16, 'subheadline': 15, 'footnote': 13, 'caption': 12, 'caption2': 11}
ROLE = {
    'VStack': 'Column', 'LazyVStack': 'Column', 'Column': 'Column', 'LazyColumn': 'Column',
    'HStack': 'Row', 'LazyHStack': 'Row', 'Row': 'Row', 'LazyRow': 'Row',
    'ZStack': 'Box', 'Box': 'Box', 'Group': 'Group', 'ScrollView': 'Scroll',
    'Text': 'Text', 'Image': 'Image', 'Icon': 'Image', 'AsyncImage': 'Image', 'AsyncImagePainter': 'Image',
    'Spacer': 'Spacer', 'Divider': 'Divider', 'HorizontalDivider': 'Divider',
    'Circle': 'Shape', 'RoundedRectangle': 'Shape', 'Rectangle': 'Shape', 'Capsule': 'Shape',
    'Button': 'Button', 'TextButton': 'Button', 'ProgressView': 'Progress', 'CircularProgressIndicator': 'Progress',
    'Toggle': 'Toggle', 'Switch': 'Toggle', 'TextField': 'TextField', 'BasicTextField': 'TextField',
}


def src_line(d_src_lines, line):
    try:
        return d_src_lines[line - 1].strip()[:160]
    except Exception:
        return ''


class Extractor:
    def __init__(self, files):
        self.defs = {}; self.consts = {}; self.srcs = {}
        for f in files:
            src = open(f, encoding='utf-8').read(); self.srcs[f] = src.split('\n')
            d, c = collect_defs(f, src)
            for k, v in d.items():
                # 같은 이름이 여러 파일에 있으면 먼저 본 것(=--files 앞쪽) 유지, 뒤엣것은 파일명 붙여 보관
                if k in self.defs: self.defs[f'{k}@{os.path.basename(f)}'] = v
                else: self.defs[k] = v
            self.consts.update(c)
        self.elements = []; self.seq = 0; self.cur_inst = 'root'

    def parse_def(self, d):
        p = Parser(d.src, d.lang, self.defs)
        return p.scan(*d.body_span)

    def run(self, entry):
        d = self.defs[entry]
        env = dict(self.consts)
        for pn, dv in d.params:
            env[pn] = dv
        self.walk_def(d, env, [entry], 0)
        return self.elements

    def walk_def(self, d, env, path, depth, parent=None):
        body = d.src[d.body_span[0]:d.body_span[1]] if d.src else ''
        env = dict(env)
        for m in re.finditer(r'^\s*(?:val|let|var)\s+(\w+)\s*(?::\s*[\w.]+)?\s*=\s*([^\n{]+?)\s*$', body, re.M):
            env.setdefault(m.group(1), m.group(2))
        self.scope_stack = getattr(self, 'scope_stack', [])
        for n in self.parse_def(d):
            self.walk(n, d, env, path, depth, parent)

    def walk(self, n, d, env, path, depth, parent):
        lang = d.lang
        el = {'id': self.seq, 'parent': parent, 'path': '/'.join(path), 'scope': path[-1], 'inst': self.cur_inst, 'callee': n.callee,
              'role': ROLE.get(n.callee, 'Component' if n.ref else n.callee), 'via': n.via,
              'file': d.file, 'line': n.line, 'anchor': None, 'props': {}, 'args': {}}
        self.seq += 1
        lines = self.srcs[d.file]
        put = lambda k, expr, line, val=None: el['props'].__setitem__(k, {
            'value': val if val is not None else evaluate(expr, env, lang), 'expr': expr, 'file': d.file,
            'line': line, 'src': src_line(lines, line)})
        # 인자
        for i, (lab, val, ln) in enumerate(n.args):
            el['args'][lab or f'#{i}'] = val
        self.anchor(n, el, env, lang)
        if lang == 'swift':
            self.swift_props(n, el, put, env)
        else:
            self.kt_props(n, el, put, env)
        self.elements.append(el)
        # 정의된 뷰 → 펼치기
        if n.ref and depth < 6:
            sub = self.defs[n.callee]
            env2 = dict(env)
            if sub.owner is None:
                env2 = dict(self.consts)
                pos = [a for a in n.args if a[0] is None]
                named = {a[0]: a[1] for a in n.args if a[0]}
                for i, (pn, dv) in enumerate(sub.params):
                    if pn in named:
                        v = evaluate(named[pn], env, lang); env2[pn] = v if v is not None else named[pn]
                    elif pos:
                        v = evaluate(pos[0][1], env, lang); env2[pn] = v if v is not None else pos.pop(0)[1]
                        if v is not None: pos.pop(0)
                    else:
                        env2[pn] = dv
                el['args_resolved'] = {k: v for k, v in env2.items() if k in dict(sub.params)}
            saved = self.cur_inst; self.cur_inst = el['id'] if sub.owner is None else saved
            self.walk_def(sub, env2, path + [n.callee], depth + 1, el['id'])
            self.cur_inst = saved
        for ch in n.children:
            self.walk(ch, d, env, path, depth, el['id'])

    # ---------- 앵커 ----------
    def anchor(self, n, el, env, lang):
        a = n.args
        first = a[0][1] if a else ''
        named = {x[0]: x[1] for x in a if x[0]}
        if n.callee == 'Text':
            t = named.get('text', first if a and a[0][0] is None else named.get('text', ''))
            m = re.fullmatch(r'"((?:[^"\\]|\\.)*)"', t.strip()) if t else None
            el['anchor'] = ('text', m.group(1)) if m else ('expr', last_ident(t))
        elif n.callee == 'Image' and lang == 'swift':
            if 'systemName' in named:
                el['anchor'] = ('symbol', named['systemName'].strip('"'))
            else:
                m = re.fullmatch(r'"([^"]+)"', first.strip())
                el['anchor'] = ('asset', m.group(1)) if m else ('expr', last_ident(first))
        elif lang == 'kotlin':
            blob = ' '.join(x[1] for x in a)
            m = re.search(r'R\.drawable\.(\w+)', blob)
            if m:
                el['anchor'] = ('asset', m.group(1))
            elif n.callee in ('Icon', 'Image'):
                m = re.search(r'Icons\.[\w.]+', blob)
                el['anchor'] = ('asset', m.group(0)) if m else ('expr', last_ident(first))
        if el['anchor'] is None and n.ref:
            el['anchor'] = ('component', n.callee)
        # 정의 안에서 인자 이름(icon, title)으로만 보이면 호출한 쪽 값으로 바꾼다
        an = el['anchor']
        if an and an[0] == 'expr' and isinstance(env.get(an[1]), str):
            v = env[an[1]].strip()
            m = re.fullmatch(r'"((?:[^"\\]|\\.)*)"', v)
            d = re.search(r'R\.drawable\.(\w+)', v)
            if m and n.callee == 'Text': el['anchor'] = ('text', m.group(1))
            elif d: el['anchor'] = ('asset', d.group(1))
            elif lang == 'swift' and m and n.callee == 'Image': el['anchor'] = ('asset', m.group(1))

    # ---------- Swift 수식어 ----------
    def swift_props(self, n, el, put, env):
        named = {x[0]: (x[1], x[2]) for x in n.args if x[0]}
        if n.callee in ('VStack', 'HStack', 'LazyVStack', 'LazyHStack'):
            if 'spacing' in named: put('spacing', named['spacing'][0], named['spacing'][1])
            else: put('spacing', 'default', n.line, 'default(≈8)')
            if 'alignment' in named:
                put('align.h' if 'V' in n.callee else 'align.v', named['alignment'][0], named['alignment'][1], named['alignment'][0].lstrip('.'))
            else:
                put('align.h' if 'V' in n.callee else 'align.v', 'default', n.line, 'center')
        if n.callee == 'ZStack':
            al = named.get('alignment', ('.center', n.line))
            put('align', al[0], al[1], al[0].lstrip('.'))
        if n.callee in ('RoundedRectangle',) and 'cornerRadius' in named:
            put('radius', named['cornerRadius'][0], named['cornerRadius'][1])
        if n.callee == 'Circle': put('radius', 'circle', n.line, 'circle')
        if n.callee == 'Capsule': put('radius', 'capsule', n.line, 'capsule')
        if n.callee == 'Spacer':
            if 'minLength' in named: put('minLength', named['minLength'][0], named['minLength'][1])
        bg_seen = False
        for name, argt, ln in n.mods:
            args = split_args(argt); nm = {a[0]: a[1] for a in args if a[0]}; pos = [a[1] for a in args if not a[0]]
            if name == 'frame':
                for k_src, k in (('width', 'width'), ('height', 'height'), ('minHeight', 'minHeight'), ('minWidth', 'minWidth')):
                    if k_src in nm: put(k, nm[k_src], ln)
                if nm.get('maxWidth', '').strip() == '.infinity': put('fill.w', '.infinity', ln, True)
                if nm.get('maxHeight', '').strip() == '.infinity': put('fill.h', '.infinity', ln, True)
                if 'alignment' in nm: put('frame.align', nm['alignment'], ln, nm['alignment'].lstrip('.'))
            elif name == 'padding':
                kind = 'margin' if bg_seen else 'padding'
                edges, val = parse_swift_padding(pos, nm)
                for e in edges:
                    old = el['props'].get(f'{kind}.{e}')
                    v = evaluate(val, env, 'swift') if val != 'default' else 16.0
                    if old and isinstance(old['value'], (int, float)) and isinstance(v, (int, float)):
                        v += old['value']
                    put(f'{kind}.{e}', val, ln, v)
            elif name == 'cornerRadius':
                put('radius', pos[0] if pos else argt, ln)
            elif name == 'clipShape':
                m = re.search(r'RoundedRectangle\(cornerRadius:\s*([^,)]+)', argt)
                if m: put('radius', m.group(1), ln)
                elif 'Circle' in argt: put('radius', 'circle', ln, 'circle')
                elif 'Capsule' in argt: put('radius', 'capsule', ln, 'capsule')
            elif name in ('background', 'overlay'):
                if name == 'background': bg_seen = True
                m = re.search(r'RoundedRectangle\(cornerRadius:\s*([^,)]+)', argt)
                if m and 'radius' not in el['props']: put('radius', m.group(1), ln)
                m = re.search(r'lineWidth:\s*([^,)]+)', argt)
                if m and name == 'overlay': put('border.width', m.group(1), ln)
            elif name == 'shadow':
                put('shadow.radius', nm.get('radius', '0'), ln)
                put('shadow.x', nm.get('x', '0'), ln); put('shadow.y', nm.get('y', '0'), ln)
                put('shadow.color', nm.get('color', 'Color(.sRGBLinear, white: 0, opacity: 0.33)'), ln, nm.get('color', 'default 0.33 black'))
            elif name == 'font':
                m = re.search(r'size:\s*([^,)]+)', argt)
                if m: put('font.size', m.group(1), ln)
                else:
                    m = re.match(r'\s*\.(\w+)', argt)
                    if m and m.group(1) in SF_TEXT_STYLES: put('font.size', argt, ln, SF_TEXT_STYLES[m.group(1)])
                m = re.search(r'weight:\s*\.(\w+)', argt)
                if m: put('font.weight', m.group(1), ln, m.group(1))
            elif name == 'fontWeight':
                put('font.weight', argt, ln, argt.strip().lstrip('.'))
            elif name == 'offset':
                if 'x' in nm: put('offset.x', nm['x'], ln)
                if 'y' in nm: put('offset.y', nm['y'], ln)
            elif name == 'rotationEffect':
                m = re.search(r'degrees\(\s*(-?[\d.]+)', argt)
                if m: put('rotation', m.group(1), ln)
            elif name == 'lineSpacing':
                put('lineSpacing', argt, ln)
            elif name == 'opacity':
                put('opacity', argt, ln)
            elif name in ('ignoresSafeArea', 'edgesIgnoringSafeArea'):
                put('ignoresSafeArea', argt or 'all', ln, True)
            elif name not in SWIFT_IGNORED_MODS:
                el.setdefault('unknown_mods', []).append(f'{name}({argt[:60]})')
        el['has_bg'] = bg_seen

    # ---------- Compose ----------
    def kt_props(self, n, el, put, env):
        named = {x[0]: (x[1], x[2]) for x in n.args if x[0]}
        for k, key in (('fontSize', 'font.size'), ('lineHeight', 'line.height')):
            if k in named: put(key, named[k][0], named[k][1])
        if 'fontWeight' in named:
            put('font.weight', named['fontWeight'][0], named['fontWeight'][1], named['fontWeight'][0].split('.')[-1].lower())
        for k in ('verticalArrangement', 'horizontalArrangement'):
            if k in named:
                v, ln = named[k]
                m = re.search(r'spacedBy\(\s*([^,)]+)', v)
                if m: put('spacing', m.group(1), ln)
                else: put('arrangement', v, ln, v.split('.')[-1])
        if n.callee in ('Column', 'Row', 'LazyColumn', 'LazyRow') and 'verticalArrangement' not in named and 'horizontalArrangement' not in named:
            put('spacing', 'default', n.line, 0.0)
        for k, key in (('horizontalAlignment', 'align.h'), ('verticalAlignment', 'align.v'), ('contentAlignment', 'align')):
            if k in named:
                put(key, named[k][0], named[k][1], kt_align(named[k][0]))
        if n.callee in ('Column', 'LazyColumn') and 'horizontalAlignment' not in named: put('align.h', 'default', n.line, 'leading')
        if n.callee in ('Row', 'LazyRow') and 'verticalAlignment' not in named: put('align.v', 'default', n.line, 'top')
        if n.callee == 'Box' and 'contentAlignment' not in named: put('align', 'default', n.line, 'topLeading')
        if 'contentPadding' in named:
            v, ln = named['contentPadding']
            m = re.search(r'PaddingValues\((.*)\)', v, re.S)
            if m:
                a2 = split_args(m.group(1))
                for e, val in parse_kt_padding([x[1] for x in a2 if not x[0]], {x[0]: x[1] for x in a2 if x[0]}):
                    put(f'padding.{e}', val, ln)
        for k in ('size', 'iconSize', 'width', 'height'):
            if k in named and k not in ('width', 'height'):
                put(f'arg.{k}', named[k][0], named[k][1])
        bg_seen = False
        mods = list(n.mods); k = 0
        while k < len(mods):
            name, argt, ln = mods[k]; k += 1
            argt = resolve_idents(argt, env)
            args = split_args(argt); nm = {a[0]: a[1] for a in args if a[0]}; pos = [a[1] for a in args if not a[0]]
            mf = env.get('__mod__' + name)
            if mf and name not in ('iosShadow', 'iosImageShadow'):
                ps, body = mf
                if body:
                    for i, (lab, val, _) in enumerate(split_args(argt)):
                        pn = lab or (ps[i] if i < len(ps) else None)
                        if pn: body = re.sub(r'(?<![\w.])' + re.escape(pn) + r'(?!\w)', val, body)
                    from codeparse import Parser as _P
                    sub = _P('', 'kotlin').kt_chain('.' + body.removeprefix('this.').removeprefix('.'), ln)
                    mods[k:k] = sub
                    el.setdefault('expanded_mods', []).append(f'{name} → {body}')
                    continue
            if mf and name in ('iosShadow', 'iosImageShadow'):
                ps = mf[0]
                nm = dict(nm)
                for i, a in enumerate(args):
                    if not a[0] and i < len(ps): nm[ps[i]] = a[1]
            if name == 'size':
                if len(pos) >= 2: put('width', pos[0], ln); put('height', pos[1], ln)
                elif pos: put('width', pos[0], ln); put('height', pos[0], ln)
                else:
                    if 'width' in nm: put('width', nm['width'], ln)
                    if 'height' in nm: put('height', nm['height'], ln)
            elif name in ('width', 'height', 'requiredWidth', 'requiredHeight'):
                put(name.replace('required', '').lower(), pos[0] if pos else argt, ln)
            elif name in ('heightIn', 'widthIn', 'defaultMinSize'):
                if 'min' in nm: put('minHeight' if 'height' in name else 'minWidth', nm['min'], ln)
                if 'minHeight' in nm: put('minHeight', nm['minHeight'], ln)
            elif name == 'fillMaxWidth': put('fill.w', name, ln, True)
            elif name == 'fillMaxHeight': put('fill.h', name, ln, True)
            elif name == 'fillMaxSize': put('fill.w', name, ln, True); put('fill.h', name, ln, True)
            elif name == 'weight': put('fill.main', f'weight({argt})', ln, True)
            elif name == 'padding':
                kind = 'padding' if bg_seen else 'margin'
                for e, val in parse_kt_padding(pos, nm):
                    v = evaluate(val, env, 'kotlin')
                    old = el['props'].get(f'{kind}.{e}')
                    if old and isinstance(old['value'], (int, float)) and isinstance(v, (int, float)): v += old['value']
                    put(f'{kind}.{e}', val, ln, v)
            elif name in ('clip', 'background', 'border', 'shadow', 'iosShadow', 'iosImageShadow'):
                if name in ('background', 'clip', 'border'): bg_seen = True
                m = re.search(r'RoundedCornerShape\(\s*([^,)]+)\)', argt)
                if m and 'radius' not in el['props']: put('radius', m.group(1), ln)
                elif 'CircleShape' in argt and 'radius' not in el['props']: put('radius', 'circle', ln, 'circle')
                if name == 'border':
                    bw = nm.get('width', pos[0] if pos else None)
                    if bw: put('border.width', bw, ln)
                if name == 'shadow':
                    put('shadow.elevation', nm.get('elevation', pos[0] if pos else '0'), ln)
                if name in ('iosShadow', 'iosImageShadow'):
                    put('shadow.radius', nm.get('radius', '0'), ln)
                    put('shadow.x', nm.get('x', '0'), ln); put('shadow.y', nm.get('y', '0'), ln)
                    put('shadow.color', nm.get('color', '?'), ln, nm.get('color', '?'))
            elif name == 'offset':
                if 'x' in nm: put('offset.x', nm['x'], ln)
                if 'y' in nm: put('offset.y', nm['y'], ln)
                if len(pos) >= 2: put('offset.x', pos[0], ln); put('offset.y', pos[1], ln)
            elif name == 'aspectRatio': put('aspectRatio', argt, ln)
            elif name == 'drawBehind':
                m = re.search(r'Stroke\(\s*width\s*=\s*([^,)]+)', argt)
                if m: put('border.width', m.group(1).replace('.toPx()', ''), ln)
            elif name == 'alpha': put('opacity', argt, ln)
            elif name not in KT_IGNORED_MODS:
                el.setdefault('unknown_mods', []).append(f'{name}({argt[:60]})')
        el['has_bg'] = bg_seen


SWIFT_IGNORED_MODS = {'foregroundColor', 'foregroundStyle', 'fill', 'stroke', 'tint', 'lineLimit', 'truncationMode',
    'multilineTextAlignment', 'renderingMode', 'resizable', 'aspectRatio', 'scaledToFit', 'scaledToFill', 'onTapGesture',
    'task', 'onAppear', 'onDisappear', 'onChange', 'sheet', 'fullScreenCover', 'alert', 'navigationBarHidden',
    'navigationBarBackButtonHidden', 'toolbar', 'buttonStyle', 'contentShape', 'accessibilityLabel', 'disabled',
    'animation', 'transition', 'id', 'tag', 'tabItem', 'environment', 'environmentObject', 'rotationEffect',
    'allowsHitTesting', 'zIndex', 'listRowBackground', 'listRowInsets', 'scrollIndicators', 'textFieldStyle',
    'keyboardType', 'focused', 'submitLabel', 'onSubmit', 'refreshable', 'overlay', 'background', 'clipped', 'bold',
    'italic', 'kerning', 'tracking', 'minimumScaleFactor', 'fixedSize', 'layoutPriority', 'interpolation', 'antialiased',
    'navigationDestination', 'preferredColorScheme', 'statusBarHidden', 'presentationDetents', 'safeAreaInset',
    'onReceive', 'confirmationDialog', 'textCase', 'symbolRenderingMode', 'imageScale', 'labelsHidden', 'toggleStyle',
    'progressViewStyle', 'scaleEffect', 'hidden', 'ignoresSafeArea'}
KT_IGNORED_MODS = {'clickable', 'semantics', 'testTag', 'verticalScroll', 'horizontalScroll', 'pointerInput', 'focusRequester',
    'onFocusChanged', 'onGloballyPositioned', 'statusBarsPadding', 'navigationBarsPadding', 'systemBarsPadding',
    'windowInsetsPadding', 'imePadding', 'zIndex', 'graphicsLayer', 'rotate', 'scale', 'animateContentSize',
    'combinedClickable', 'selectable', 'toggleable', 'focusable', 'nestedScroll', 'align', 'matchParentSize',
    'wrapContentWidth', 'wrapContentHeight', 'wrapContentSize', 'paint', 'clipToBounds', 'onSizeChanged', 'then'}


def resolve_idents(t, env, depth=0):
    """인자 글자 중 지역 상수 이름(shape 등)을 그 값 글자로 바꾼다."""
    if depth > 4 or not t: return t
    def rep(m):
        v = env.get(m.group(0))
        return resolve_idents(v, env, depth + 1) if isinstance(v, str) and ('(' in v or v.startswith(('Circle', 'Rect'))) else m.group(0)
    return re.sub(r'(?<![\w.])[a-z]\w*(?![\w(])', rep, t)


def parse_swift_padding(pos, nm):
    allE = ['top', 'bottom', 'leading', 'trailing']
    if not pos and not nm: return allE, 'default'
    if len(pos) == 1 and not pos[0].strip().startswith(('.', '[')): return allE, pos[0]
    edge = pos[0].strip(); val = pos[1] if len(pos) > 1 else 'default'
    m = {'.horizontal': ['leading', 'trailing'], '.vertical': ['top', 'bottom'], '.top': ['top'], '.bottom': ['bottom'],
         '.leading': ['leading'], '.trailing': ['trailing'], '.all': allE}
    if edge.startswith('['):
        es = []
        for x in edge.strip('[]').split(','):
            es += m.get(x.strip(), [])
        return es, val
    return m.get(edge, allE), val


def parse_kt_padding(pos, nm):
    if pos: return [(e, pos[0]) for e in ('top', 'bottom', 'leading', 'trailing')]
    out = []
    for k, es in (('horizontal', ['leading', 'trailing']), ('vertical', ['top', 'bottom']), ('all', ['top', 'bottom', 'leading', 'trailing']),
                  ('start', ['leading']), ('end', ['trailing']), ('top', ['top']), ('bottom', ['bottom'])):
        if k in nm: out += [(e, nm[k]) for e in es]
    return out


def kt_align(v):
    v = v.split('.')[-1]
    return {'CenterHorizontally': 'center', 'CenterVertically': 'center', 'Center': 'center', 'Start': 'leading',
            'End': 'trailing', 'Top': 'top', 'Bottom': 'bottom', 'TopCenter': 'top', 'TopStart': 'topLeading',
            'BottomCenter': 'bottom', 'CenterStart': 'leading', 'CenterEnd': 'trailing'}.get(v, v)


def last_ident(t):
    ids = re.findall(r'[A-Za-z_]\w*', t or '')
    ids = [i for i in ids if i not in ('self', 'it', 'state', 'viewModel', 'entry', 'String', 'format', 'Locale', 'US')]
    return ids[-1] if ids else (t or '').strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root'); ap.add_argument('--entry', required=True)
    ap.add_argument('--files', nargs='*'); ap.add_argument('-o', required=True)
    a = ap.parse_args()
    files = a.files or []
    if a.root:
        ext = None
        if files: ext = os.path.splitext(files[0])[1]
        for dp, dn, fn in os.walk(a.root):
            if any(x in dp for x in ('/build/', '/.build', '/Pods', '/test', '/Test', 'DerivedData', '/.git')): continue
            for f in fn:
                if f.endswith(('.swift', '.kt')) and (ext is None or f.endswith(ext)):
                    p = os.path.join(dp, f)
                    if p not in files: files.append(p)
    ex = Extractor(files)
    if a.entry not in ex.defs:
        sys.exit(f'정의 {a.entry} 없음. 후보: {sorted(k for k in ex.defs if a.entry.lower()[:4] in k.lower())[:20]}')
    els = ex.run(a.entry)
    json.dump({'entry': a.entry, 'lang': ex.defs[a.entry].lang, 'elements': els}, open(a.o, 'w'), ensure_ascii=False, indent=1)
    print(f'{a.entry}: 요소 {len(els)}개, 속성 {sum(len(e["props"]) for e in els)}개 → {a.o}')


if __name__ == '__main__':
    main()
