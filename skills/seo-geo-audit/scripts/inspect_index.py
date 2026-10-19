"""구글 색인 실제 상태 — 서치콘솔 URL 검사 API(서비스 계정이 그 속성의 소유자여야 함).
  python3 inspect_index.py https://site/ [URL ...]      (URL을 안 주면 sitemap 앞 5개)
서비스 계정 키: env GSC_SA_JSON, 없으면 ~/.claude/ai-paper-analytics-sa.json. 소유자 등록은 site-launch의 gsc_register.py.
속성은 URL 접두어(https://site/)와 도메인 속성(sc-domain:host)을 차례로 시도한다."""
import os, re, sys, urllib.parse, urllib.request
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

site = sys.argv[1].rstrip('/') + '/'
key = os.environ.get('GSC_SA_JSON', os.path.expanduser('~/.claude/ai-paper-analytics-sa.json'))
s = AuthorizedSession(service_account.Credentials.from_service_account_file(key, scopes=['https://www.googleapis.com/auth/webmasters']))
urls = sys.argv[2:] or [site] + re.findall(r'<loc>\s*(.*?)\s*</loc>', urllib.request.urlopen(site + 'sitemap.xml', timeout=20).read().decode())[1:5]
props = [site, 'sc-domain:' + urllib.parse.urlsplit(site).netloc]
for u in urls:
    for p in props:
        r = s.post('https://searchconsole.googleapis.com/v1/urlInspection/index:inspect', json={'inspectionUrl': u, 'siteUrl': p})
        if r.status_code == 200: break
    if r.status_code != 200:
        print(u, 'ERROR', r.status_code, r.json().get('error', {}).get('message', '')[:120], '— 서비스 계정이 이 속성 소유자인지 확인'); continue
    ir = r.json()['inspectionResult']['indexStatusResult']
    print(u, '|', ir.get('coverageState'), '| 최근 크롤', ir.get('lastCrawlTime', '-'), '| robots', ir.get('robotsTxtState'), '| 구글 canonical', ir.get('googleCanonical', '-'))
