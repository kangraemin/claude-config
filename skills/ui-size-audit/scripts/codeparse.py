"""SwiftUI / Jetpack Compose 소스를 LLM 없이 읽어 화면 요소 트리를 만든다.

- 뷰 호출(대문자로 시작하는 호출 + 같은 파일에 정의된 뷰 함수/변수)을 노드로 잡는다.
- Swift는 `.frame(...)` 같은 뒤따르는 수식어 줄을, Kotlin은 `modifier = Modifier.a().b()` 인자를 수식어로 잡는다.
- 정의(struct View / some View 변수·함수 / @Composable fun)를 모아 호출하는 곳에서 펼친다(인자 값 대입).
"""
import re, ast, math

SWIFT_NON_VIEW = {
    'Color', 'Font', 'CGFloat', 'CGSize', 'CGPoint', 'EdgeInsets', 'Angle', 'URL', 'String', 'Int', 'Double',
    'LinearGradient', 'Gradient', 'UnitPoint', 'StrokeStyle', 'Animation', 'Binding', 'State', 'StateObject',
    'Task', 'DispatchQueue', 'UIColor', 'UIFont', 'NSAttributedString', 'AttributedString', 'Date', 'Locale',
    'Array', 'Set', 'Dictionary', 'Optional', 'Text.Scale', 'Self', 'Bool', 'Float', 'UUID', 'Data', 'JSONDecoder',
}
KT_NON_VIEW = {
    'Modifier', 'Color', 'RoundedCornerShape', 'CircleShape', 'Arrangement', 'Alignment', 'FontWeight', 'TextStyle',
    'PaddingValues', 'BorderStroke', 'Brush', 'Offset', 'Size', 'Shadow', 'DpOffset', 'Dp', 'TextUnit', 'Locale',
    'String', 'Int', 'Float', 'Double', 'Toast', 'PickVisualMediaRequest', 'ActivityResultContracts', 'Intent',
    'Uri', 'LaunchedEffect', 'DisposableEffect', 'SideEffect', 'CompositionLocalProvider', 'TextAlign',
    'TextOverflow', 'FontFamily', 'Font', 'LineHeightStyle', 'PlatformTextStyle', 'SpanStyle', 'KeyboardOptions',
    'Stroke', 'Path', 'Rect', 'CornerRadius', 'ContentScale', 'ColorFilter', 'BlendMode', 'Paint', 'Shape',
    'GenericShape', 'Outline', 'RectangleShape', 'MutableInteractionSource', 'Unit', 'List', 'Map', 'Pair',
}


def strip_comments(src):
    """주석을 같은 길이 공백으로 바꿔 줄 번호를 그대로 둔다. 문자열은 건드리지 않는다."""
    out = list(src); i = 0; n = len(src)
    while i < n:
        c = src[i]
        if src.startswith('"""', i):
            j = src.find('"""', i + 3); i = n if j < 0 else j + 3; continue
        if c == '"':
            i += 1
            while i < n and src[i] != '"' and src[i] != '\n':
                i += 2 if src[i] == '\\' else 1
            i += 1; continue
        if src.startswith('//', i):
            j = src.find('\n', i); j = n if j < 0 else j
            for k in range(i, j): out[k] = ' '
            i = j; continue
        if src.startswith('/*', i):
            j = src.find('*/', i + 2); j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != '\n': out[k] = ' '
            i = j; continue
        i += 1
    return ''.join(out)


def match_close(s, i):
    """s[i]가 ( [ { 일 때 짝 닫는 위치. 문자열 안 괄호는 건너뛴다."""
    pairs = {'(': ')', '[': ']', '{': '}'}
    stack = [pairs[s[i]]]; j = i + 1; n = len(s)
    while j < n and stack:
        c = s[j]
        if s.startswith('"""', j):
            k = s.find('"""', j + 3); j = n if k < 0 else k + 3; continue
        if c == '"':
            j += 1
            while j < n and s[j] != '"':
                j += 2 if s[j] == '\\' else 1
            j += 1; continue
        if c in pairs: stack.append(pairs[c])
        elif c in ')]}':
            if stack and c == stack[-1]: stack.pop()
        j += 1
    return j - 1


def split_args(s):
    """최상위 쉼표로 나눠 [(label, value, offset)]."""
    parts = []; depth = 0; start = 0; i = 0; n = len(s)
    while i < n:
        c = s[i]
        if c == '"':
            i += 1
            while i < n and s[i] != '"':
                i += 2 if s[i] == '\\' else 1
        elif c in '([{': depth += 1
        elif c in ')]}': depth -= 1
        elif c == ',' and depth == 0:
            parts.append((start, s[start:i])); start = i + 1
        i += 1
    if s[start:].strip(): parts.append((start, s[start:]))
    out = []
    for off, p in parts:
        m = re.match(r'\s*([A-Za-z_]\w*)\s*(?::(?!:)|=(?!=))\s*', p)
        lead = len(p) - len(p.lstrip())
        if m and not p.strip().startswith('{'):
            out.append((m.group(1), p[m.end():].strip(), off + m.end()))
        else:
            out.append((None, p.strip(), off + lead))
    return out


class Node:
    def __init__(self, callee, line, lang):
        self.callee = callee; self.line = line; self.lang = lang
        self.args = []        # [(label, text, line)]
        self.mods = []        # [(name, argtext, line)]  Swift 수식어 / Kotlin Modifier 체인
        self.children = []
        self.ref = False      # 정의된 뷰를 부르는 노드
        self.via = None       # overlay/background 같이 수식어 안에서 나온 자식

    def __repr__(self):
        return f'{self.callee}@{self.line}'


IDENT = re.compile(r'[A-Za-z_]\w*')


class Parser:
    def __init__(self, src, lang, defs=None):
        self.raw = src; self.s = strip_comments(src); self.lang = lang
        self.defs = defs or {}
        self.nl = [0]
        for m in re.finditer('\n', self.s): self.nl.append(m.end())

    def line(self, pos):
        lo, hi = 0, len(self.nl)
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if self.nl[mid] <= pos: lo = mid
            else: hi = mid
        return lo + 1

    def skip_ws(self, i, end):
        while i < end and self.s[i] in ' \t\r\n': i += 1
        return i

    def is_view_callee(self, name, nxt):
        if name in self.defs: return True
        if not name[0].isupper(): return False
        bad = SWIFT_NON_VIEW if self.lang == 'swift' else KT_NON_VIEW
        if name in bad or name.split('.')[0] in bad: return False
        if self.lang == 'kotlin' and name.startswith('R.'): return False
        return True

    def scan(self, a, b):
        """[a,b) 범위의 최상위 뷰 노드 목록."""
        s = self.s; i = a; nodes = []
        while i < b:
            c = s[i]
            if c == '"':
                i = self._skip_str(i, b); continue
            m = IDENT.match(s, i)
            if not m or (i > 0 and (s[i - 1].isalnum() or s[i - 1] in '_.@$')):
                i += 1; continue
            name = m.group(); j = m.end()
            # 점으로 이어진 이름(Text.Something) 은 하나로
            while j < b and s[j] == '.' and IDENT.match(s, j + 1) and s[j + 1].isupper():
                j = IDENT.match(s, j + 1).end(); name = s[i:j]
            k = self.skip_ws(j, b)
            nxt = s[k] if k < b else ''
            if self.lang == 'swift' and name in ('func', 'var', 'let', 'struct', 'case', 'enum', 'extension'):
                i = j; continue
            if self.lang == 'kotlin' and name in ('fun', 'val', 'var', 'class', 'object', 'when', 'if', 'else', 'is'):
                i = j; continue
            if nxt == '<' and self.lang == 'kotlin':
                i = j; continue
            bare_def = (name in self.defs and self.defs[name].bare and nxt not in ('(', ':', '=') and
                        not (k < b and s[k] == '='))
            if (nxt in '({' and nxt and self.is_view_callee(name, nxt)) or bare_def:
                if self.lang == 'kotlin' and nxt == '{' and name not in self.defs and not name[0].isupper():
                    i = j; continue
                node, end = self.parse_call(name, i, k, b, bare=bare_def)
                nodes.append(node); i = end; continue
            i = j
        return nodes

    def _skip_str(self, i, b):
        s = self.s
        if s.startswith('"""', i):
            k = s.find('"""', i + 3); return b if k < 0 else k + 3
        i += 1
        while i < b and s[i] != '"':
            i += 2 if s[i] == '\\' else 1
        return i + 1

    def parse_call(self, name, start, k, b, bare=False):
        s = self.s
        node = Node(name, self.line(start), self.lang)
        node.ref = name in self.defs
        i = k
        if not bare and i < b and s[i] == '(':
            e = match_close(s, i)
            body = s[i + 1:e]
            for lab, val, off in split_args(body):
                node.args.append((lab, val, self.line(i + 1 + off)))
                if val.startswith('{'):  # Kotlin content = { } 같은 람다 인자
                    p0 = i + 1 + off; p1 = match_close(s, p0)
                    node.children += self.scan(p0 + 1, p1)
            # 인자 안 Modifier 체인
            if self.lang == 'kotlin':
                for lab, val, off_line in node.args:
                    if lab == 'modifier' or (lab is None and val.startswith('Modifier')):
                        node.mods += self.kt_chain(val, off_line)
            i = e + 1
        elif bare:
            i = start + len(name)
        # 뒤따르는 람다들 { } (Swift 다중 trailing closure 'label:' 포함)
        while True:
            t = self.skip_ws(i, b)
            if t < b and s[t] == '{':
                e = match_close(s, t)
                node.children += self.scan(t + 1, e); i = e + 1; continue
            if self.lang == 'swift':
                m = re.compile(r'([a-z]\w*)\s*:\s*\{').match(s, t)
                if m and node.children:
                    t2 = m.end() - 1; e = match_close(s, t2)
                    node.children += self.scan(t2 + 1, e); i = e + 1; continue
            break
        if self.lang == 'swift':
            while True:
                t = self.skip_ws(i, b)
                m = re.compile(r'\.\s*([A-Za-z_]\w*)').match(s, t)
                if not m: break
                mname = m.group(1); t2 = m.end()
                if t2 < b and s[t2] == '(':
                    e = match_close(s, t2); argtext = s[t2 + 1:e]
                    node.mods.append((mname, argtext, self.line(t)))
                    if mname in ('overlay', 'background', 'mask'):
                        for ch in self.scan(t2 + 1, e):
                            ch.via = mname; node.children.append(ch)
                    i = e + 1
                    t3 = self.skip_ws(i, b)
                    if t3 < b and s[t3] == '{':  # .overlay { } / .background { }
                        e2 = match_close(s, t3)
                        for ch in self.scan(t3 + 1, e2):
                            ch.via = mname; node.children.append(ch)
                        i = e2 + 1
                elif t2 < b and s[t2] == '{' and mname in ('overlay', 'background', 'mask', 'task', 'onAppear', 'sheet', 'onTapGesture', 'contextMenu'):
                    e = match_close(s, t2)
                    if mname in ('overlay', 'background', 'mask'):
                        for ch in self.scan(t2 + 1, e):
                            ch.via = mname; node.children.append(ch)
                    i = e + 1
                else:
                    node.mods.append((mname, '', self.line(t))); i = t2
        return node, i

    def kt_chain(self, expr, line):
        """Modifier.a(x).b(y) → [(a,x,line),(b,y,line)]. 조건부 then(...)은 안을 펼친다."""
        out = []; i = 0; s = expr
        while i < len(s):
            m = re.compile(r'\.\s*([A-Za-z_]\w*)\s*').match(s, i)
            if not m:
                i += 1; continue
            name = m.group(1); j = m.end()
            if j < len(s) and s[j] == '(':
                e = match_close(s, j); arg = s[j + 1:e]
                if name == 'then':
                    out += self.kt_chain(arg, line)
                else:
                    out.append((name, arg, line + s[:j].count('\n')))
                i = e + 1
            elif j < len(s) and s[j] == '{':
                e = match_close(s, j); out.append((name, s[j + 1:e], line + s[:j].count('\n'))); i = e + 1
            else:
                i = j
        return out


class Def:
    def __init__(self, name, file, line, params, body_span, lang, bare, owner=None, src=None):
        self.name = name; self.file = file; self.line = line; self.params = params  # [(name, default_text)]
        self.body_span = body_span; self.lang = lang; self.bare = bare; self.owner = owner; self.src = src
        self.consts = {}


def collect_defs(path, src):
    """정의와 상수를 모은다. 반환: defs(dict name->Def), consts(dict)"""
    s = strip_comments(src); defs = {}; consts = {}
    lang = 'swift' if path.endswith('.swift') else 'kotlin'
    line = lambda p: s.count('\n', 0, p) + 1
    if lang == 'swift':
        for m in re.finditer(r'struct\s+(\w+)\s*(?:<[^>]*>)?\s*:\s*[^{]*\bView\b[^{]*\{', s):
            o = m.end() - 1; e = match_close(s, o); body = s[o + 1:e]
            params = []
            for pm in re.finditer(r'^\s*(?:@\w+(?:\([^)]*\))?\s+)*(?:private\s+|fileprivate\s+)?(let|var)\s+(\w+)\s*:\s*([^={\n]+?)\s*(?:=\s*([^\n]+))?\s*$', body, re.M):
                if pm.group(1) == 'var' and pm.group(4) is None and '{' in body[pm.end():pm.end() + 2]:
                    continue
                if 'some View' in pm.group(3): continue
                if pm.group(0).strip().startswith(('@State ', '@StateObject', '@Environment', '@ObservedObject', '@Binding')) is False or True:
                    params.append((pm.group(2), (pm.group(4) or '').strip() or None))
            bm = re.search(r'var\s+body\s*:\s*some\s+View\s*\{', body)
            if bm:
                bo = o + 1 + bm.end() - 1
                d = Def(m.group(1), path, line(m.start()), params, (bo + 1, match_close(s, bo)), lang, False, src=src)
                defs[m.group(1)] = d
            for vm in re.finditer(r'(?:@ViewBuilder\s+)?(?:private\s+|fileprivate\s+)?var\s+(\w+)\s*:\s*some\s+View\s*\{', body):
                if vm.group(1) == 'body': continue
                vo = o + 1 + vm.end() - 1
                defs[vm.group(1)] = Def(vm.group(1), path, line(o + 1 + vm.start()), [], (vo + 1, match_close(s, vo)), lang, True, owner=m.group(1), src=src)
            for fm in re.finditer(r'(?:@ViewBuilder\s+)?(?:private\s+|fileprivate\s+)?func\s+(\w+)\s*\(([^)]*)\)\s*->\s*some\s+View\s*\{', body):
                fo = o + 1 + fm.end() - 1
                ps = []
                for lab, val, _ in split_args(fm.group(2)):
                    pn = (lab or val).split()[-1] if lab else val.split(':')[0].split()[-1]
                    if lab and ':' in val:
                        pn = val.split(':')[0].strip()
                    dflt = val.split('=', 1)[1].strip() if '=' in val else None
                    ps.append((pn, dflt))
                defs[fm.group(1)] = Def(fm.group(1), path, line(o + 1 + fm.start()), ps, (fo + 1, match_close(s, fo)), lang, False, owner=m.group(1), src=src)
        for fm in re.finditer(r'func\s+(\w+)\s*\(([^)]*)\)\s*->\s*(?:CGFloat|Double|Int)\s*\{\s*(?:return\s+)?([^}\n]+?)\s*\}', s):
            ps = [x.split(':')[0].split()[-1] for x in fm.group(2).split(',') if x.strip()]
            consts['__fn__' + fm.group(1)] = (ps, fm.group(3).strip())
        for cm in re.finditer(r'(?:static\s+)?let\s+(\w+)\s*(?::\s*[\w.]+)?\s*=\s*([-\d.]+)\s*$', s, re.M):
            consts[cm.group(1)] = cm.group(2)
    else:
        for m in re.finditer(r'@Composable\s+(?:(?:private|internal|public)\s+)?fun\s+(?:[\w.]+\.)?(\w+)\s*\(', s):
            po = m.end() - 1; pe = match_close(s, po)
            ps = []
            for lab, val, _ in split_args(s[po + 1:pe]):
                if lab is None and ':' in val:
                    lab, val = val.split(':', 1)
                typ_d = val.split('=', 1)
                lab = re.sub(r'^(?:@[\w.]+(?:\([^)]*\))?\s+)+', '', lab.strip())  # @DrawableRes 같은 표시 떼기
                lab = re.sub(r'^(?:vararg|noinline|crossinline)\s+', '', lab)
                ps.append((lab.strip(), typ_d[1].strip() if len(typ_d) > 1 else None))
            t = pe + 1
            mm = re.compile(r'\s*(?::\s*([\w.<>?, ]+))?\s*(\{|=)').match(s, t)
            if not mm: continue
            if mm.group(1) and mm.group(1).strip() not in ('Unit',):
                continue  # Shadow·TextStyle 따위를 돌려주는 함수는 화면 요소가 아님
            if mm.group(2) == '{':
                bo = mm.end() - 1; span = (bo + 1, match_close(s, bo))
            else:
                bo = mm.end(); span = (bo, s.find('\n\n', bo) if s.find('\n\n', bo) > 0 else len(s))
            defs[m.group(1)] = Def(m.group(1), path, line(m.start()), ps, span, 'kotlin', False, src=src)
        for mm in re.finditer(r'fun\s+Modifier\.(\w+)\s*\(', s):
            po = mm.end() - 1; pe = match_close(s, po)
            ps = [(lab or val.split(':')[0]).strip() for lab, val, _ in split_args(s[po + 1:pe])]
            ps = [x.split(':')[0].strip() for x in ps]
            rest = re.compile(r'\s*:\s*Modifier\s*=\s*').match(s, pe + 1)
            body = None
            if rest:
                b0 = rest.end(); line_end = s.find('\n', b0)
                body = s[b0:line_end].strip()
                if body.startswith(('drawBehind', 'composed', 'this.then(', 'then(')) or body.endswith('{'):
                    body = None
            consts['__mod__' + mm.group(1)] = (ps, body)
        for fm in re.finditer(r'^\s*(?:private\s+|internal\s+)?fun\s+(\w+)\s*\(([^)]*)\)\s*(?::\s*[\w.]+)?\s*=\s*([^\n{]+)$', s, re.M):
            consts['__fn__' + fm.group(1)] = ([x.split(':')[0].strip() for x in fm.group(2).split(',') if x.strip()], fm.group(3).strip())
        for cm in re.finditer(r'(?:private\s+|internal\s+)?(?:const\s+)?val\s+(\w+)\s*(?::\s*[\w.]+)?\s*=\s*([-\d.]+(?:\.dp|\.sp|f)?)\s*$', s, re.M):
            consts[cm.group(1)] = cm.group(2)
    return defs, consts


# ---------- 식 계산 ----------

def norm_expr(t, lang):
    t = t.strip()
    t = re.sub(r'(\d+(?:\.\d+)?)\s*\.(?:dp|sp|em)\b', r'\1', t)
    t = re.sub(r'(\d+(?:\.\d+)?)[fF]\b', r'\1', t)
    t = re.sub(r'CGFloat\(([^()]*)\)', r'(\1)', t)
    t = re.sub(r'\.dp\b|\.sp\b', '', t)
    t = t.replace('.infinity', 'inf').replace('Dp.Infinity', 'inf').replace('Dp.Unspecified', 'nan')
    return t


def evaluate(t, env, lang, depth=0):
    """숫자로 계산되면 float, 아니면 None."""
    if t is None: return None
    if not isinstance(t, str): return float(t) if isinstance(t, (int, float)) else None
    e = norm_expr(t, lang)
    if depth > 6: return None
    for _ in range(5):  # 같은 파일의 한 줄짜리 계산 함수 펼치기
        m = re.search(r'(?<![\w.])(\w+)\s*\(([^()]*)\)', e)
        if not m or '__fn__' + m.group(1) not in env: break
        ps, body = env['__fn__' + m.group(1)]
        av = [a.strip() for a in m.group(2).split(',')] if m.group(2).strip() else []
        b2 = norm_expr(body, lang)
        for p_, a_ in zip(ps, av):
            b2 = re.sub(r'(?<![\w.])' + re.escape(p_) + r'(?!\w)', '(' + norm_expr(a_, lang) + ')', b2)
        e = e[:m.start()] + '(' + b2 + ')' + e[m.end():]

    def rep(m):
        name = m.group(0)
        if name in ('inf', 'nan'): return name
        if name in env and env[name] is not None and not isinstance(env[name], tuple):
            v = env[name]
            if isinstance(v, (int, float)): return repr(float(v))
            r = evaluate(v, env, lang, depth + 1)
            if r is not None: return repr(r)
        return name
    e2 = re.sub(r'(?<![\w.])[A-Za-z_]\w*', rep, e)
    try:
        tree = ast.parse(e2, mode='eval')
    except SyntaxError:
        return None

    def ev(n):
        if isinstance(n, ast.Expression): return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return float(n.value)
        if isinstance(n, ast.Name) and n.id == 'inf': return math.inf
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub): return -ev(n.operand)
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            return {ast.Add: a + b, ast.Sub: a - b, ast.Mult: a * b, ast.Div: a / b if b else math.nan}[type(n.op)]
        raise ValueError
    try:
        return ev(tree)
    except Exception:
        return None
