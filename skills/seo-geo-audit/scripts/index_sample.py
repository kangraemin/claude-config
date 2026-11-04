"""사이트 전체가 구글에 얼마나 색인됐는지 무작위 표본으로 어림한다. 읽기 전용(URL 검사 API + 페이지 읽기).
  python3 index_sample.py https://site [--n 100] [--seed N] [--json 결과.json]
sitemap 앞쪽이나 조회 많은 페이지만 보면 전체 비율을 크게 틀린다(2026-11-04 상위 30쪽 조사와 표본 조사 비교). 그래서 무작위로 뽑는다.
출력: 상태별 수, 색인 비율과 95% 범위, 전체 추정 수, 구역별 상태, 상태별 본문 측정값(전체 글자·고유 글자·고유 문장).
고유 값은 표본 안에서만 비교한 값이라 표본이 작으면 크게 나온다. URL 검사 API 한도는 속성당 하루 2,000건·분당 600건."""
import collections, concurrent.futures as cf, html, json, math, os, random, re, statistics as st, sys, urllib.parse, urllib.request
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

def opt(name, d): return type(d)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else d
SITE = sys.argv[1].rstrip('/') + '/'
N, SEED, OUT = opt('--n', 100), opt('--seed', 20261104), opt('--json', '')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/140 Safari/537.36'
LANGS = {'en', 'ja', 'zh', 'zh-tw', 'zh-cn', 'th', 'vi', 'es', 'fr', 'id', 'de', 'ko'}
key = os.environ.get('GSC_SA_JSON', os.path.expanduser('~/.claude/ai-paper-analytics-sa.json'))
s = AuthorizedSession(service_account.Credentials.from_service_account_file(key, scopes=['https://www.googleapis.com/auth/webmasters']))

def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=40).read().decode('utf-8', 'replace')
def locs():
    x = get(SITE + 'sitemap.xml'); L = re.findall(r'<loc>\s*(.*?)\s*</loc>', x)
    return [v for u in L for v in re.findall(r'<loc>\s*(.*?)\s*</loc>', get(u))] if '<sitemapindex' in x else L
def sect(u):
    seg = [x for x in urllib.parse.unquote(urllib.parse.urlsplit(u).path).split('/') if x]
    if not seg: return 'home'
    return seg[0] + '/' + (seg[1] if len(seg) > 1 else '') if seg[0] in LANGS else seg[0]
def blocks(h):
    h = re.sub(r'(?is)<(script|style|noscript|svg|head|nav|footer|header)\b.*?</\1>', ' ', h)
    out = []
    for p in re.split(r'(?i)</?(?:p|div|li|h[1-6]|tr|td|th|ul|ol|section|article|main|br|a|span|button|dd|dt)\b[^>]*>', h):
        t = ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', p)).split())
        if len(t) >= 2: out.append(re.sub(r'\d+', '0', t))
    return out
def inspect(u):
    for p in (SITE, 'sc-domain:' + urllib.parse.urlsplit(SITE).netloc):
        r = s.post('https://searchconsole.googleapis.com/v1/urlInspection/index:inspect', json={'inspectionUrl': u, 'siteUrl': p})
        if r.status_code == 200: return r.json()['inspectionResult']['indexStatusResult']
    return {'coverageState': f'API 오류 {r.status_code}'}
def wilson(k, n, z=1.96):
    if not n: return 0, 0
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - w) / d, (c + w) / d

allu = locs()
samp = random.Random(SEED).sample(allu, min(N, len(allu)))
print(f'{SITE} sitemap {len(allu)}개, 표본 {len(samp)}개 (seed {SEED})', flush=True)
def fetch(u):
    try: return u, blocks(get(u))
    except Exception as e: return u, None
rows = []
for u, b in cf.ThreadPoolExecutor(6).map(fetch, samp): rows.append({'u': u, 'b': b, 'sect': sect(u)})
df = collections.Counter(k for r in rows if r['b'] for k in set(r['b']))
for r in rows:
    if r['b'] is not None:
        r['total'] = sum(map(len, r['b'])); r['uniq'] = sum(len(k) for k in set(r['b']) if df[k] == 1); r['nb'] = sum(1 for k in set(r['b']) if df[k] == 1 and len(k) >= 30)
    del r['b']
    ir = inspect(r['u']); r['state'] = ir.get('coverageState', '?'); r['crawl'] = (ir.get('lastCrawlTime') or '')[:10]
    r['verdict'] = ir.get('verdict'); r['canon_self'] = (ir.get('googleCanonical') or '').rstrip('/') == r['u'].rstrip('/')
cnt = collections.Counter(r['state'] for r in rows)
ok = sum(v for k, v in cnt.items() if k.startswith('Submitted and indexed') or k.startswith('Indexed'))
lo, hi = wilson(ok, len(rows))
print(f'색인됨 {ok}/{len(rows)}쪽. 전체 비율 95% 범위 {lo:.0%}~{hi:.0%}, 전체 추정 {int(lo * len(allu))}~{int(hi * len(allu))}쪽')
for k, v in cnt.most_common(): print(f'  {v:4d}  {k}')
print('구역별')
by = collections.defaultdict(collections.Counter)
for r in rows: by[r['sect']]['색인' if r['state'].startswith(('Submitted and indexed', 'Indexed')) else '안 됨'] += 1
for k, v in sorted(by.items(), key=lambda x: -sum(x[1].values())): print(f'  {k}: 색인 {v["색인"]} / 안 됨 {v["안 됨"]}')
print('상태별 본문 측정(중앙값, 고유는 표본 안에서만 비교)')
g = collections.defaultdict(list)
for r in rows:
    if 'total' in r: g[r['state']].append(r)
for k, v in g.items(): print(f'  {k[:38]}: {len(v)}쪽 전체 {int(st.median(x["total"] for x in v))}자, 고유 {int(st.median(x["uniq"] for x in v))}자, 고유 문장 {st.median(x["nb"] for x in v)}개')
if OUT: json.dump({'site': SITE, 'sitemap': len(allu), 'rows': rows}, open(OUT, 'w'), ensure_ascii=False, indent=0)
