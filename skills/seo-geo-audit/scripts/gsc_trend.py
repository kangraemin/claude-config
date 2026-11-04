"""서치콘솔 노출 추세와 급락 진단 재료. 읽기 전용, 유료 키 불필요.
  python3 gsc_trend.py https://site/ [--days 28] [--json 결과.json]
보는 것: 날짜별 노출(완료 전 자료 포함), 최근 7일 대 그 앞 7일, 노출이 가장 많이 준 페이지·구역, 평균 순위 변화,
순위 8~20 페이지, 노출 많고 클릭률 낮은 페이지, 한 검색어에 여러 페이지가 나오는 경우.
읽는 법: 노출이 줄었는데 평균 순위가 그대로면 순위 하락보다 페이지 탈락을 먼저 의심한다 → index_sample.py로 확인.
임계값(8~20위, 클릭률 2%, 노출 30% 감소)은 오픈소스들이 쓰는 값으로 구글 공식 값이 아니다."""
import collections, datetime as dt, json, os, sys, urllib.parse
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

def opt(n, d): return type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
SITE = sys.argv[1].rstrip('/') + '/'; DAYS = opt('--days', 28); OUT = opt('--json', '')
key = os.environ.get('GSC_SA_JSON', os.path.expanduser('~/.claude/ai-paper-analytics-sa.json'))
s = AuthorizedSession(service_account.Credentials.from_service_account_file(key, scopes=['https://www.googleapis.com/auth/webmasters.readonly']))
today = dt.date.today(); end = today - dt.timedelta(days=1)  # 오늘 값은 비어 있다
def q(prop, a, b, dims, limit=5000):
    return s.post(f'https://www.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(prop, safe="")}/searchAnalytics/query',
                  json={'startDate': str(a), 'endDate': str(b), 'dimensions': dims, 'rowLimit': limit, 'dataState': 'all'})
PROP = next((p for p in (SITE, 'sc-domain:' + urllib.parse.urlsplit(SITE).netloc) if q(p, end, end, ['date']).status_code == 200), None)
if not PROP: sys.exit(f'RESULT: 조회 실패 — 서비스 계정이 {SITE} 속성 권한을 갖고 있는지 확인')
daily = q(PROP, end - dt.timedelta(days=DAYS - 1), end, ['date']).json().get('rows', [])
print(f'{SITE} 날짜별 노출/클릭')
for r in daily: print(f"  {r['keys'][0][5:]}  {int(r['impressions']):6d}  {int(r['clicks']):4d}  순위 {r['position']:.1f}")
cur = (end - dt.timedelta(days=6), end); prev = (end - dt.timedelta(days=13), end - dt.timedelta(days=7))
def agg(rng):
    rows = q(PROP, *rng, ['page']).json().get('rows', [])
    return {r['keys'][0]: r for r in rows}
C, P = agg(cur), agg(prev)
imp = lambda d: sum(r['impressions'] for r in d.values()); wpos = lambda d: sum(r['position'] * r['impressions'] for r in d.values()) / max(1, imp(d))
ci, pi = imp(C), imp(P)
print(f'최근 7일 {int(ci)} / 그 앞 7일 {int(pi)} ({(ci - pi) / pi:+.0%}), 평균 순위 {wpos(P):.1f} → {wpos(C):.1f}, 노출된 페이지 {len(P)} → {len(C)}' if pi else f'최근 7일 {int(ci)} / 그 앞 7일 0')
def sect(u):
    seg = [x for x in urllib.parse.urlsplit(u).path.split('/') if x]
    return '/'.join(seg[:2]) if len(seg) > 2 and len(seg[0]) <= 5 else (seg[0] if seg else 'home')
sc = collections.Counter(); 
for u in set(C) | set(P): sc[sect(u)] += C.get(u, {}).get('impressions', 0) - P.get(u, {}).get('impressions', 0)
print('구역별 노출 증감'); [print(f'  {int(v):+6d}  {k}') for k, v in sc.most_common()[::-1][:8]]
loss = sorted(((C.get(u, {}).get('impressions', 0) - P[u]['impressions'], u) for u in P), key=lambda x: x[0])[:10]
print('노출이 가장 많이 준 페이지'); [print(f'  {int(d):+6d}  {"사라짐" if u not in C else ""} {urllib.parse.unquote(u)}') for d, u in loss if d < 0]
m28 = q(PROP, end - dt.timedelta(days=27), end, ['page']).json().get('rows', [])
near = sorted((r for r in m28 if 8 <= r['position'] <= 20), key=lambda r: -r['impressions'])[:10]
print('순위 8~20 (조금만 오르면 첫 쪽)'); [print(f"  노출 {int(r['impressions']):5d} 순위 {r['position']:.1f}  {urllib.parse.unquote(r['keys'][0])}") for r in near]
ctr = sorted((r for r in m28 if r['position'] <= 5 and r['ctr'] < 0.02), key=lambda r: -r['impressions'])[:10]
print('5위 안인데 클릭률 2% 미만 (제목·설명 후보)'); [print(f"  노출 {int(r['impressions']):5d} 클릭률 {r['ctr']:.1%}  {urllib.parse.unquote(r['keys'][0])}") for r in ctr]
qp = collections.defaultdict(list)
for r in q(PROP, end - dt.timedelta(days=27), end, ['query', 'page'], 10000).json().get('rows', []):
    if r['impressions'] >= 5: qp[r['keys'][0]].append(r)
can = sorted(((k, v) for k, v in qp.items() if len(v) > 1), key=lambda x: -sum(r['impressions'] for r in x[1]))[:10]
print('한 검색어에 여러 페이지'); [print(f"  {k}: {len(v)}쪽, 노출 {int(sum(r['impressions'] for r in v))}") for k, v in can]
if OUT: json.dump({'daily': daily, 'cur': list(C.values()), 'prev': list(P.values())}, open(OUT, 'w'), ensure_ascii=False)
print('RESULT: OK')
