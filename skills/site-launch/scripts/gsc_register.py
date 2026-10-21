"""구글 서치콘솔 등록 — 로그인 없이 서비스 계정만으로.
  python3 gsc_register.py token  https://site/            → <meta google-site-verification> 출력(사이트 head에 넣고 배포)
  python3 gsc_register.py verify https://site/ [sitemap.xml|전체 URL] → 소유확인 + 사람 계정 소유자 추가 + 서치콘솔 추가 + 사이트맵 제출
  python3 gsc_register.py status https://site/            → 제출된 사이트맵 처리 상태(pending/read)
"""
import sys, urllib.parse
from _sa import sess
OWNERS = ['remin1994@gmail.com', 'kangaiai1994@gmail.com']
s = sess('https://www.googleapis.com/auth/siteverification', 'https://www.googleapis.com/auth/webmasters')
cmd, site = sys.argv[1], sys.argv[2].rstrip('/') + '/'
SV = 'https://www.googleapis.com/siteVerification/v1'
if cmd == 'token':
    r = s.post(SV + '/token', json={'site': {'type': 'SITE', 'identifier': site}, 'verificationMethod': 'META'})
    print(r.json().get('token') or r.text); sys.exit(0 if r.ok else 1)
r = s.post(SV + '/webResource?verificationMethod=META', json={'site': {'type': 'SITE', 'identifier': site}})
print('verify', r.status_code, r.text[:200] if not r.ok else '')
if not r.ok: sys.exit(1)
j = r.json()
r = s.put(SV + '/webResource/' + urllib.parse.quote(j['id'], safe=''),
          json={'site': j['site'], 'owners': sorted(set(j['owners'] + OWNERS))})
print('owners', r.status_code)
e = urllib.parse.quote(site, safe='')
print('add', s.put(f'https://www.googleapis.com/webmasters/v3/sites/{e}').status_code)
sm = sys.argv[3] if len(sys.argv) > 3 else 'sitemap.xml'
if not sm.startswith('http'): sm = site + sm  # 전체 주소도 받는다
if cmd == 'status':
    for x in s.get(f'https://www.googleapis.com/webmasters/v3/sites/{e}/sitemaps').json().get('sitemap', []):
        print('SITEMAP', x['path'], 'pending' if x.get('isPending') else 'read', x.get('lastDownloaded', '-'), x.get('contents', ''), x.get('errors', 0))
    sys.exit(0)
print('sitemap', s.put(f'https://www.googleapis.com/webmasters/v3/sites/{e}/sitemaps/{urllib.parse.quote(sm, safe="")}').status_code, sm)
