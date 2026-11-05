"""사이트 SEO·GEO 자동 점검 — 실제 배포 주소를 자바스크립트 없이(크롤러 시점) 읽는다.
  python3 audit.py https://site [--max 300] [--seed N] [--json]
사이트 단위(robots·sitemap·봇 실제 접속·llms.txt·RSS·파비콘)와 페이지 단위(sitemap URL, --max를 넘으면 무작위 표본)를 본다.
결과: FAIL(고쳐야 함) / WARN(권장) / INFO(참고, 근거가 약하거나 판정 기준 없음). 종료 코드 1 = FAIL 있음."""
import collections, concurrent.futures as cf, hashlib, html, json, random, re, statistics, sys, time, urllib.parse, urllib.request

UA = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
AI_BOTS = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-SearchBot', 'PerplexityBot', 'Google-Extended', 'Yeti', 'Bingbot']
args = [a for a in sys.argv[1:] if not a.startswith('--')]
SITE = args[0].rstrip('/')
MAX = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 300
SEED = int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 20261104
BOT_UA = {'Googlebot': UA, 'Bingbot': 'Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)',
          'Yeti': 'Mozilla/5.0 (compatible; Yeti/1.1; +https://naver.me/spd)', 'GPTBot': 'Mozilla/5.0 (compatible; GPTBot/1.2; +https://openai.com/gptbot)',
          'OAI-SearchBot': 'Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)', 'ChatGPT-User': 'Mozilla/5.0 (compatible; ChatGPT-User/1.0; +https://openai.com/bot)',
          'ClaudeBot': 'Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)', 'PerplexityBot': 'Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)'}
out = collections.defaultdict(list)  # level -> [(where, msg)]

def note(level, where, msg): out[level].append((where, msg))

def get(u):
    for i in range(2):  # 시간 초과·접속 오류는 우리 쪽 일시 장애일 수 있어 한 번 더 본다. 두 번째도 실패해야 FAIL
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=25)
            return r.status, r.geturl(), r.headers, r.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e: return e.code, u, e.headers, ''
        except Exception as e: err = str(e); time.sleep(2)
    return err, u, {}, ''

def get_ua(u, ua):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': ua}), timeout=25)
        return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e: return e.code, ''
    except Exception as e: return type(e).__name__, ''

def tags(h, name):
    """속성 순서·따옴표에 상관없이 <meta>·<link> 속성을 읽는다."""
    out_ = []
    for m_ in re.finditer(rf'<{name}\b([^>]*)>', h, re.I):
        out_.append({k.lower(): html.unescape(v1 or v2) for k, v1, v2 in re.findall(r'([\w:-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', m_.group(1))})
    return out_
def meta(ts, key, val): return next((x.get('content', '') for x in ts if x.get(key, '').lower() == val), None)
def has_noindex(h, hd=None):
    return 'noindex' in (meta(tags(h, 'meta'), 'name', 'robots') or '').lower() or 'noindex' in str((hd or {}).get('X-Robots-Tag', '')).lower()
HREFLANG = re.compile(r'^(x-default|[a-z]{2,3}(-[a-z0-9]{2,8})*)$', re.I)
def blocks(h):
    """머리말·메뉴·꼬리말을 뺀 본문 덩어리. 숫자는 0으로 바꿔 숫자만 다른 틀 문장을 같게 본다."""
    h = re.sub(r'(?is)<(script|style|noscript|svg|head|nav|footer|header)\b.*?</\1>', ' ', h)
    bs = []
    for p in re.split(r'(?i)</?(?:p|div|li|h[1-6]|tr|td|th|ul|ol|section|article|main|br|a|span|button|dd|dt)\b[^>]*>', h):
        x = ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', p)).split())
        if len(x) >= 2: bs.append(re.sub(r'\d+', '0', x))
    return bs

def text_of(h): return ' '.join(re.sub(r'<script.*?</script>|<style.*?</style>|<[^>]+>', ' ', h, flags=re.S).split())

# ── 사이트 단위 ──
# 하위 경로 사이트(github.io/<repo>)는 robots.txt를 호스트 루트에서만 읽는다
ROOT = re.match(r'https?://[^/]+', SITE).group(0)
s, _, _, robots = get(ROOT + '/robots.txt')
if s != 200: note('FAIL', 'robots.txt', f'없음({s})')
else:
    if 'Sitemap:' not in robots: note('WARN', 'robots.txt', 'Sitemap: 줄 없음')
    groups = re.split(r'\n(?=User-agent:)', robots, flags=re.I)
    for b in AI_BOTS + ['*']:
        g = [x for x in groups if re.search(rf'User-agent:\s*{re.escape(b)}\s*$', x, re.I | re.M)]
        if any(re.search(r'^Disallow:\s*/\s*$', x, re.M) for x in g): note('WARN' if b != '*' else 'FAIL', 'robots.txt', f'{b} 전체 차단')
s, _, _, sm = get(SITE + '/sitemap.xml')
urls = re.findall(r'<loc>\s*(.*?)\s*</loc>', sm)
if s != 200 or not urls: note('FAIL', 'sitemap.xml', f'없음/빈 파일({s})')
else:
    if '<sitemapindex' in sm:  # 색인 사이트맵이면 하위 사이트맵을 펼친다
        subs, urls = urls, []
        for x in subs[:50]:
            sub = get(x)[3]; urls += re.findall(r'<loc>\s*(.*?)\s*</loc>', sub); sm += sub  # lastmod도 하위 사이트맵에서 읽는다
    lm = re.findall(r'<lastmod>\s*(\d{4}-\d{2}-\d{2})', sm)
    if not lm: note('WARN', 'sitemap.xml', 'lastmod 없음')
    else:
        import datetime
        age = (datetime.date.today() - datetime.date.fromisoformat(max(lm))).days
        if age > 30: note('WARN', 'sitemap.xml', f'가장 최근 lastmod가 {age}일 전({max(lm)}) — 갱신이 멈췄거나 lastmod가 틀림(신선도 신호)')
        if len(lm) > 20 and len(set(lm)) == 1: note('WARN', 'sitemap.xml', f'lastmod {len(lm)}개가 전부 {lm[0]} — 페이지별 실제 수정일이 아니면 구글이 무시한다')
    off = [u for u in urls if not u.startswith(SITE)]
    if off: note('FAIL', 'sitemap.xml', f'다른 호스트 URL {len(off)}개 (예: {off[0]})')
# robots에 없어도 방화벽이 막을 수 있어 봇 이름으로 직접 접속한다(맥 IP라 진짜 봇 IP 대우까지는 증명 못 함)
s0, b0 = get_ua(SITE + '/', 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/140 Safari/537.36')
def _bot(n):
    st_, b_ = get_ua(SITE + '/', BOT_UA[n])
    if st_ != 200: st_, b_ = get_ua(SITE + '/', BOT_UA[n])  # 한 번 시간 초과는 일시 장애일 수 있어 한 번만 다시 본다
    return n, st_, b_
CHALLENGE = re.compile(r'just a moment|attention required|checking your browser|_cf_chl_opt', re.I)
for n_, st_, b_ in cf.ThreadPoolExecutor(4).map(_bot, BOT_UA):
    if st_ != 200: note('FAIL', f'봇 접속 {n_}', f'{n_} 이름으로 접속하면 {st_} (일반 브라우저 {s0}) — 방화벽·봇 차단 설정 확인')
    elif CHALLENGE.search(b_) and len(text_of(b_)) < 1000: note('FAIL', f'봇 접속 {n_}', f'{n_} 이름으로 접속하면 사람 확인 화면 — 방화벽 설정 확인')
    elif s0 == 200 and len(b_) < 0.5 * len(b0): note('WARN', f'봇 접속 {n_}', f'{n_}가 받는 본문이 브라우저의 절반 미만({len(b_)}/{len(b0)}바이트)')
for p, lvl, why in [('/llms.txt', 'INFO', 'llms.txt 없음(구글은 불필요하다고 밝힘, AI 에이전트 편의용)'), ('/favicon.ico', 'WARN', '검색결과 파비콘용 실파일 없음')]:
    st, fu, _, _ = get(SITE + p)
    if st != 200: note(lvl, p, why + (f' (리다이렉트 → {fu} 에서 {st})' if fu != SITE + p else f' ({st})'))

class NoRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a): return None
def head_status(u):
    try: r = urllib.request.build_opener(NoRedir).open(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=15); return r.status, ''
    except urllib.error.HTTPError as e: return e.code, e.headers.get('Location', '')
    except Exception as e: return str(e), ''
st, loc = head_status(SITE + '/')
if st in (302, 303, 307): note('WARN', '/', f'루트가 임시 리다이렉트({st}) → {loc} — 대표 주소면 308/301, 아니면 루트에 본문')
# 없는 주소가 200이면 soft 404(구글 서치콘솔 경고). 사이트맵의 경로 패턴(/c/xxx/ 등) 아래도 찔러 본다
probes = {SITE + '/__seo-audit-404-check__/'}
for u in urls[:50]:
    segs = urllib.parse.urlsplit(u).path.strip('/').split('/')
    if len(segs) >= 2: probes.add(f"{SITE}/{'/'.join(segs[:-1])}/__seo-audit-404__/")
for u in list(probes)[:5]:
    st, fu, _, h = get(u)
    if st == 200 and not re.search(r'<meta[^>]+name="robots"[^>]+noindex', h, re.I):
        note('FAIL', u, '없는 주소가 200(soft 404) — 404를 돌려주거나 noindex')
host = urllib.parse.urlsplit(SITE).netloc
alt = host[4:] if host.startswith('www.') else 'www.' + host
PLATFORM = ('github.io', 'vercel.app', 'netlify.app', 'pages.dev', 'web.app', 'firebaseapp.com', 'herokuapp.com')
st, fu = (200, f'https://{host}/') if host.endswith(PLATFORM) else get(f'https://{alt}/')[:2]  # 플랫폼 하위 주소엔 www가 없다
if st != 200: note('WARN', alt, f'www/비www 다른 쪽이 안 열림({st}) — DNS 추가 후 대표 주소로 301/308')
elif urllib.parse.urlsplit(fu).netloc != host: note('WARN', alt, f'{alt}가 대표 주소로 안 넘어감(→ {fu}) — 중복 사이트')

# ── 페이지 단위 ──
total_urls = len(urls)
pages = urls or [SITE + '/']
if len(pages) > MAX:  # 앞에서 자르면 한 종류만 보게 된다. 무작위로 뽑고 홈은 꼭 넣는다
    pool = [u for u in pages if u.rstrip('/') != SITE]
    pages = [SITE + '/'] + random.Random(SEED).sample(pool, MAX - 1)
    note('INFO', '표본', f'sitemap {total_urls}개 중 무작위 {len(pages)}개만 봤다. 아래 곳 수는 표본 기준')
res = list(cf.ThreadPoolExecutor(8).map(lambda u: (u, *get(u)), pages))
titles, descs, types = collections.Counter(), collections.Counter(), collections.Counter()
home_html = ''
noindexed, alts, pagehtml = 0, {}, {}
for u, st, final, hd, h in res:
    if st != 200: note('FAIL', u, f'상태 {st}'); continue
    if final.rstrip('/') != u.rstrip('/'): note('FAIL', u, f'리다이렉트 → {final} (sitemap엔 최종 주소만)')
    if u.rstrip('/') == SITE: home_html = h
    pagehtml[u] = h
    head = h  # Next.js 등은 title·meta를 </head> 뒤(본문 스트림)에 넣기도 한다 — 구글은 문서 전체에서 읽는다
    m = lambda pat: (lambda x: x and html.unescape(x))((re.search(pat, head, re.I | re.S) or [None, None])[1])  # &lt; 등은 한 글자로 센다
    mt, lk = tags(head, 'meta'), tags(head, 'link')
    if has_noindex(head, hd): noindexed += 1; note('FAIL', u, 'sitemap에 있는데 noindex — sitemap에서 빼거나 noindex를 푼다')
    can = next((x.get('href') for x in lk if x.get('rel', '').lower() == 'canonical'), None)
    al = {x.get('hreflang'): urllib.parse.urljoin(u, x.get('href', '')) for x in lk if x.get('rel', '').lower() == 'alternate' and x.get('hreflang')}
    if al:
        alts[u] = al
        for c in al:
            if not HREFLANG.match(c): note('WARN', u, f'hreflang 언어 코드 이상: {c}')
        if u.rstrip('/') not in {v.rstrip('/') for v in al.values()}: note('WARN', u, 'hreflang에 자기 자신이 없음(구글: 자기 자신도 적어야 함)')
    if not can: note('FAIL', u, 'canonical 없음')
    elif can.rstrip('/') != u.rstrip('/'): note('WARN', u, f'canonical이 다른 주소 → {can}')
    t = m(r'<title>(.*?)</title>'); titles[t] += 1
    if not t: note('FAIL', u, 'title 없음')
    elif not 10 <= len(t) <= 70: note('WARN', u, f'title 길이 {len(t)}자(10~70 권장)')
    d = meta(mt, 'name', 'description'); descs[d] += 1
    if not d: note('FAIL', u, 'description 없음')
    elif not 40 <= len(d) <= 170: note('WARN', u, f'description 길이 {len(d)}자(40~170 권장)')
    for k in ['og:title', 'og:description', 'og:image', 'og:url']:
        if meta(mt, 'property', k) is None: note('WARN', u, f'{k} 없음(공유 미리보기·네이버 점검 항목)')
    if meta(mt, 'name', 'twitter:card') is None: note('WARN', u, 'twitter:card 없음')
    lang = (re.search(r'<html[^>]+lang="([^"]+)"', h) or [None, None])[1]
    body = text_of(h)
    if not lang: note('WARN', u, 'html lang 없음')
    elif len(re.findall(r'[가-힣]', body)) > 0.3 * max(1, len(re.findall(r'[A-Za-z가-힣\u3040-\u30ff\u4e00-\u9fff]', body))) and not lang.lower().startswith('ko'):
        note('WARN', u, f'본문은 한국어인데 html lang="{lang}" — ko로(og:locale도 ko_KR)')
    if t:
        parts = [x.strip() for x in re.split(r'[|—–-]', t) if x.strip()]
        if len(parts) != len(set(parts)): note('WARN', u, 'title에 같은 이름 반복(예: "글 | 사이트 | 사이트")')
    h1 = len(re.findall(r'<h1[\s>]', h))
    if h1 != 1: note('WARN', u, f'h1 {h1}개(1개 권장)')
    lds = re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', h, re.S)
    micro = re.findall(r'itemtype="https?://schema\.org/(\w+)"', h)
    for t_ in micro: types[t_ + '(microdata)'] += 1
    if not lds and not micro: note('WARN', u, '구조화 데이터 없음(JSON-LD·microdata 모두)')
    for b in lds:
        try:
            j = json.loads(b)
            for x in (j if isinstance(j, list) else j.get('@graph', [j])): types[x.get('@type')] += 1
        except Exception as e: note('FAIL', u, f'JSON-LD 파싱 오류 {e}')
    tx = text_of(h)  # 띄어쓰기 없는 일본어·중국어는 2자를 1단어로 센다
    cjk = len(re.findall(r'[\u3040-\u30ff\u4e00-\u9fff]', tx))
    words = len(re.sub(r'[\u3040-\u30ff\u4e00-\u9fff]', ' ', tx).split()) + cjk // 2
    if words < 80: note('FAIL' if words < 20 else 'WARN', u, f'JS 없이 보이는 본문 {words}단어 — 프리렌더/SSR 필요(AI 크롤러는 JS 안 돌림)')
    # 상대 경로(d/x.html, ../)도 내부 링크로 센다
    links = {l for l in re.findall(r'<a[^>]+href="([^"#]+)"', h) if urllib.parse.urljoin(u, l).startswith(SITE)}
    if len(links) < 2: note('WARN', u, f'내부 링크 {len(links)}개(2개 이상 권장)')
    noalt = len(re.findall(r'<img(?![^>]*\balt=)[^>]*>', h))
    if noalt: note('WARN', u, f'alt 없는 이미지 {noalt}개')
# ── sitemap 대부분이 noindex면 배포 사고일 수 있다 ──
if len(res) >= 10 and noindexed >= 0.8 * len(res): note('FAIL', '전체', f'표본 {len(res)}개 중 {noindexed}개가 noindex — 사이트 전체 noindex 사고인지 먼저 확인')
# ── hreflang 양방향(구글: 서로 가리키지 않으면 무시) ──
if alts:
    targets = {v for a in alts.values() for k, v in a.items() if v not in pagehtml}
    extra = sorted(targets); random.Random(SEED).shuffle(extra); extra = extra[:80]
    for v, (st_, _, hd_, h_) in zip(extra, ((r[0], r[1], r[2], r[3]) for r in cf.ThreadPoolExecutor(12).map(get, extra))):
        if st_ == 200: pagehtml[v] = h_
        else: note('FAIL', v, f'hreflang이 가리키는 주소가 상태 {st_}')
    checked = 0
    for u, a in alts.items():
        for c, v in a.items():
            if v.rstrip('/') == u.rstrip('/') or v not in pagehtml: continue
            checked += 1
            back = {urllib.parse.urljoin(v, x.get('href', '')).rstrip('/') for x in tags(pagehtml[v], 'link') if x.get('rel', '').lower() == 'alternate' and x.get('hreflang')}
            if u.rstrip('/') not in back: note('WARN', u, f'hreflang 한쪽만 가리킴: {c} → {v} (돌아오는 링크 없음, 구글이 무시)')
            if has_noindex(pagehtml[v]): note('WARN', u, f'hreflang이 noindex 페이지를 가리킴: {c} → {v}')
    note('INFO', 'hreflang', f'언어 짝 {checked}개 확인(가리키는 주소 표본 {len(extra)}개까지)')
# ── 얇은 틀 페이지·근접 중복: 구글은 기준 숫자를 공개하지 않는다. 판정이 아니라 측정값이다 ──
live = {u: blocks(h) for u, h in pagehtml.items() if u in {x[0] for x in res}}
if len(live) >= 20:
    df = collections.Counter(k for bs in live.values() for k in set(bs))
    by = collections.defaultdict(list); bodyhash = collections.defaultdict(list); shing = {}
    for u, bs in live.items():
        total = sum(map(len, bs)); uniq = sum(len(k) for k in set(bs) if df[k] == 1)
        seg = [x for x in urllib.parse.urlsplit(u).path.split('/') if x]
        sect = '/'.join(seg[:2]) if seg and len(seg[0]) <= 5 and len(seg) > 2 else (seg[0] if seg else 'home')  # /en/restaurant/1 은 언어까지 묶는다
        by[sect].append((total, uniq, sum(1 for k in set(bs) if df[k] == 1 and len(k) >= 30)))
        joined = ''.join(bs); bodyhash[hashlib.md5(joined.encode()).hexdigest()].append(u)
        shing[u] = (sect, {joined[i:i + 5] for i in range(0, max(0, len(joined) - 4), 3)})
    for k, v in sorted(by.items(), key=lambda x: -len(x[1])):
        if len(v) >= 3: note('INFO', f'본문 측정 /{k}', f'{len(v)}쪽 전체 {int(statistics.median(x[0] for x in v))}자, 고유 {int(statistics.median(x[1] for x in v))}자, 고유 문장 {statistics.median(x[2] for x in v)}개(중앙값, 표본 안에서만 비교)')
    for us in bodyhash.values():
        if len(us) > 1: note('WARN', us[0], f'본문이 완전히 같은 페이지 {len(us)}개(숫자만 다른 경우 포함), 예: {us[1]}')
    near, items = 0, list(shing.items())
    ex = None
    for i, (a, (sa, xa)) in enumerate(items):
        for b, (sb, xb) in items[i + 1:]:
            if sa != sb or not xa or not xb: continue
            mn, mx = sorted((len(xa), len(xb)))
            if mn < 0.9 * mx: continue
            if len(xa & xb) >= 0.9 * len(xa | xb): near += 1; ex = ex or (a, b)
    if near: note('WARN', ex[0], f'본문 90% 이상 겹치는 쌍 {near}개, 예: {ex[1]} (90%는 임의 기준)')
for t, n in titles.items():
    if t and n > 1: note('WARN', '전체', f'중복 title {n}개: {t[:50]}')
for d, n in descs.items():
    if d and n > 1: note('WARN', '전체', f'중복 description {n}개: {d[:50]}')

# ── GEO(생성형 AI 인용) — 홈 기준 ──
if home_html:
    hs = re.findall(r'<h[23][^>]*>(.*?)</h[23]>', home_html, re.S)
    hs = [text_of(x) for x in hs if text_of(x)]
    q = [x for x in hs if x.rstrip().endswith(('?', '？'))]
    if hs and not q: note('INFO', 'GEO', f'질문형 소제목 0/{len(hs)} — "~은?" 제목+첫 문장 직답(근거: 관찰 연구, 구글은 별도 작업 불필요라고 밝힘)')
    if 'FAQPage' not in types: note('INFO', 'GEO', 'FAQ 섹션/FAQPage 없음(근거 약함, 구글은 AI 전용 마크업 불필요라고 밝힘)')
    if not re.search(r'type="application/(rss|atom)\+xml"', home_html): note('WARN', 'GEO', 'RSS/Atom 피드 없음(네이버 RSS 제출·신선도 신호)')
    if not re.search(r'\d', text_of(home_html)[:2000]): note('INFO', 'GEO', '첫 화면에 숫자·통계 없음(근거: GEO 논문 등 관찰 연구)')
    if not re.search(r'(기준|updated|업데이트|갱신|時点|更新|現在)', home_html): note('WARN', 'GEO', '기준일·갱신 시각 표기 없음(신선도)')
if not any(t in types for t in ['Organization', 'WebSite']): note('WARN', '전체', 'Organization/WebSite 스키마 없음(엔티티 인식)')

# ── Bing Webmaster 등록 (ChatGPT 검색·Copilot이 Bing 색인을 쓴다) ──
import os
bkey = next((l.split('=', 1)[1].strip() for l in open(os.path.expanduser('~/.claude/.env')) if l.startswith('BING_WEBMASTER_API_KEY=')), None)
if not bkey: note('WARN', 'Bing', 'BING_WEBMASTER_API_KEY 없음 — 등록 여부 확인 못 함')
else:
    try:
        bs = json.load(urllib.request.urlopen(f'https://ssl.bing.com/webmaster/api.svc/json/GetUserSites?apikey={bkey}', timeout=25))['d']
        hit = [b for b in bs if (SITE + '/').startswith(b['Url'])]
        if not hit: note('FAIL', 'Bing', '빙 웹마스터 미등록 — site-launch bing_register.py')
        elif not any(b['IsVerified'] for b in hit): note('FAIL', 'Bing', '빙 웹마스터 소유확인 안 됨 — bing_register.py 다시 실행')
    except Exception as e: note('WARN', 'Bing', f'빙 API 조회 실패 {e}')

if '--json' in sys.argv:
    print(json.dumps({k: v for k, v in out.items()}, ensure_ascii=False, indent=1)); sys.exit(1 if out['FAIL'] else 0)
print(f'점검: {SITE}  sitemap {total_urls}개 중 {len(res)}개  스키마 {dict(types)}')
for lvl in ['FAIL', 'WARN', 'INFO']:
    grouped = collections.defaultdict(list)
    for w, msg in out[lvl]: grouped[w if lvl == 'INFO' and w.startswith('본문 측정') else re.sub(r'\d+', 'N', msg.split(' — ')[0].split('(')[0])].append((w, msg))
    for k, xs in grouped.items():
        print(f'{lvl}  {xs[0][1]}  [{len(xs)}곳, 예: {xs[0][0]}]')
print('결과:', 'FAIL 있음' if out['FAIL'] else ('WARN만' if out['WARN'] else 'OK'))
sys.exit(1 if out['FAIL'] else 0)
