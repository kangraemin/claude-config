"""사이트 SEO·GEO 자동 점검 — 실제 배포 주소를 자바스크립트 없이(크롤러 시점) 읽는다.
  python3 audit.py https://site [--max 300] [--json]
사이트 단위(robots·sitemap·llms.txt·RSS·파비콘)와 페이지 단위(sitemap의 URL 전부, --max까지)를 본다.
결과: FAIL(고쳐야 함) / WARN(권장) / OK. 종료 코드 1 = FAIL 있음."""
import collections, concurrent.futures as cf, html, json, re, sys, urllib.parse, urllib.request

UA = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
AI_BOTS = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-SearchBot', 'PerplexityBot', 'Google-Extended', 'Yeti', 'Bingbot']
args = [a for a in sys.argv[1:] if not a.startswith('--')]
SITE = args[0].rstrip('/')
MAX = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 300
out = collections.defaultdict(list)  # level -> [(where, msg)]

def note(level, where, msg): out[level].append((where, msg))

def get(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=25)
        return r.status, r.geturl(), r.headers, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e: return e.code, u, e.headers, ''
    except Exception as e: return str(e), u, {}, ''

def text_of(h): return ' '.join(re.sub(r'<script.*?</script>|<style.*?</style>|<[^>]+>', ' ', h, flags=re.S).split())

# ── 사이트 단위 ──
s, _, _, robots = get(SITE + '/robots.txt')
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
        for x in subs[:20]: urls += re.findall(r'<loc>\s*(.*?)\s*</loc>', get(x)[3])
    lm = re.findall(r'<lastmod>\s*(\d{4}-\d{2}-\d{2})', sm)
    if not lm: note('WARN', 'sitemap.xml', 'lastmod 없음')
    else:
        import datetime
        age = (datetime.date.today() - datetime.date.fromisoformat(max(lm))).days
        if age > 30: note('WARN', 'sitemap.xml', f'가장 최근 lastmod가 {age}일 전({max(lm)}) — 갱신이 멈췄거나 lastmod가 틀림(신선도 신호)')
        if len(lm) > 20 and len(set(lm)) == 1: note('WARN', 'sitemap.xml', f'lastmod {len(lm)}개가 전부 {lm[0]} — 페이지별 실제 수정일이 아니면 구글이 무시한다')
    off = [u for u in urls if not u.startswith(SITE)]
    if off: note('FAIL', 'sitemap.xml', f'다른 호스트 URL {len(off)}개 (예: {off[0]})')
for p, lvl, why in [('/llms.txt', 'WARN', 'AI용 사이트 요약(llms.txt) 없음'), ('/favicon.ico', 'WARN', '검색결과 파비콘용 실파일 없음')]:
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
pages = (urls or [SITE + '/'])[:MAX]
res = list(cf.ThreadPoolExecutor(12).map(lambda u: (u, *get(u)), pages))
titles, descs, types = collections.Counter(), collections.Counter(), collections.Counter()
home_html = ''
for u, st, final, hd, h in res:
    if st != 200: note('FAIL', u, f'상태 {st}'); continue
    if final.rstrip('/') != u.rstrip('/'): note('FAIL', u, f'리다이렉트 → {final} (sitemap엔 최종 주소만)')
    if u.rstrip('/') == SITE: home_html = h
    head = h  # Next.js 등은 title·meta를 </head> 뒤(본문 스트림)에 넣기도 한다 — 구글은 문서 전체에서 읽는다
    m = lambda pat: (lambda x: x and html.unescape(x))((re.search(pat, head, re.I | re.S) or [None, None])[1])  # &lt; 등은 한 글자로 센다
    if re.search(r'<meta[^>]+name="robots"[^>]+noindex', head, re.I) or 'noindex' in str(hd.get('X-Robots-Tag', '')): note('FAIL', u, 'noindex')
    can = m(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"')
    if not can: note('FAIL', u, 'canonical 없음')
    elif can.rstrip('/') != u.rstrip('/'): note('WARN', u, f'canonical이 다른 주소 → {can}')
    t = m(r'<title>(.*?)</title>'); titles[t] += 1
    if not t: note('FAIL', u, 'title 없음')
    elif not 10 <= len(t) <= 70: note('WARN', u, f'title 길이 {len(t)}자(10~70 권장)')
    d = m(r'<meta[^>]+name="description"[^>]+content="([^"]*)"'); descs[d] += 1
    if not d: note('FAIL', u, 'description 없음')
    elif not 40 <= len(d) <= 170: note('WARN', u, f'description 길이 {len(d)}자(40~170 권장)')
    for k in ['og:title', 'og:description', 'og:image', 'og:url']:
        if not re.search(rf'property="{k}"', head): note('WARN', u, f'{k} 없음(공유 미리보기·네이버 점검 항목)')
    if not re.search(r'name="twitter:card"', head): note('WARN', u, 'twitter:card 없음')
    lang = (re.search(r'<html[^>]+lang="([^"]+)"', h) or [None, None])[1]
    body = text_of(h)
    if not lang: note('WARN', u, 'html lang 없음')
    elif len(re.findall(r'[가-힣]', body)) > 0.3 * max(1, len(re.findall(r'[A-Za-z가-힣]', body))) and not lang.lower().startswith('ko'):
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
    words = len(text_of(h).split())
    if words < 80: note('FAIL' if words < 20 else 'WARN', u, f'JS 없이 보이는 본문 {words}단어 — 프리렌더/SSR 필요(AI 크롤러는 JS 안 돌림)')
    links = set(re.findall(r'<a[^>]+href="(/[^"]*|' + re.escape(SITE) + r'[^"]*)"', h))
    if len(links) < 2: note('WARN', u, f'내부 링크 {len(links)}개(2개 이상 권장)')
    noalt = len(re.findall(r'<img(?![^>]*\balt=)[^>]*>', h))
    if noalt: note('WARN', u, f'alt 없는 이미지 {noalt}개')
for t, n in titles.items():
    if t and n > 1: note('WARN', '전체', f'중복 title {n}개: {t[:50]}')
for d, n in descs.items():
    if d and n > 1: note('WARN', '전체', f'중복 description {n}개: {d[:50]}')

# ── GEO(생성형 AI 인용) — 홈 기준 ──
if home_html:
    hs = re.findall(r'<h[23][^>]*>(.*?)</h[23]>', home_html, re.S)
    hs = [text_of(x) for x in hs if text_of(x)]
    q = [x for x in hs if x.rstrip().endswith('?')]
    if hs and not q: note('WARN', 'GEO', f'질문형 소제목 0/{len(hs)} — "~은?" 형태 제목+첫 문장 직답이 인용에 유리')
    if 'FAQPage' not in types: note('WARN', 'GEO', 'FAQ(질문·답) 섹션/FAQPage 없음')
    if not re.search(r'type="application/(rss|atom)\+xml"', home_html): note('WARN', 'GEO', 'RSS/Atom 피드 없음(네이버 RSS 제출·신선도 신호)')
    if not re.search(r'\d', text_of(home_html)[:2000]): note('WARN', 'GEO', '첫 화면에 숫자·통계 없음(인용되는 문장은 수치가 있다)')
    if not re.search(r'(기준|updated|업데이트|갱신)', home_html): note('WARN', 'GEO', '기준일·갱신 시각 표기 없음(신선도)')
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
print(f'점검: {SITE}  페이지 {len(res)}개  스키마 {dict(types)}')
for lvl in ['FAIL', 'WARN']:
    grouped = collections.defaultdict(list)
    for w, msg in out[lvl]: grouped[re.sub(r'\d+', 'N', msg.split(' — ')[0].split('(')[0])].append((w, msg))
    for k, xs in grouped.items():
        print(f'{lvl}  {xs[0][1]}  [{len(xs)}곳, 예: {xs[0][0]}]')
print('결과:', 'FAIL 있음' if out['FAIL'] else ('WARN만' if out['WARN'] else 'OK'))
sys.exit(1 if out['FAIL'] else 0)
