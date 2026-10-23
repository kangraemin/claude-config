"""Bing Webmaster에 사이트 추가 → 소유확인 → sitemap 제출 — 화면 조작 없이 Bing Webmaster API(키)로.
  python3 bing_register.py https://site [--public DIR]   # DIR(배포 루트)에 BingSiteAuth.xml을 써 준다
순서: 1회차에 --public으로 BingSiteAuth.xml 생성 → 배포 → 다시 실행하면 VerifySite·SubmitFeed까지 끝남.
키: ~/.claude/.env BING_WEBMASTER_API_KEY (bing.com/webmasters → 설정 → API access → Generate API Key, remin1994 구글 로그인).
GSC에 URL-prefix로 있는 사이트는 웹 화면 'Import from GSC'로 한 번에 들어간다('Site addition unsuccessful'이 떠도 실제로는 들어감).
멱등: 이미 추가·확인·제출된 건 건너뛴다. 마지막 줄: RESULT <상태>
  python3 bing_register.py https://site/path/ --submit-urls   # 그 사이트의 sitemap.xml 주소를 SubmitUrlBatch로 전부 제출
sitemap 제출(Success·UrlCount)만으로는 빙이 크롤링을 안 할 수 있다(oneul-kkum: 923개 받고 열흘 가까이 홈도 미크롤).
URL 제출 할당량은 GetUrlSubmissionQuota로 본다(github.io 하위 경로: 하루 10,000·월 90,000, 2026-10-23)."""
import json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

for l in (Path.home() / '.claude/.env').read_text().splitlines():
    if l.startswith('BING_WEBMASTER_API_KEY='): KEY = l.split('=', 1)[1].strip()
A = 'https://ssl.bing.com/webmaster/api.svc/json/'
host = urllib.parse.urlsplit(sys.argv[1] if '://' in sys.argv[1] else 'https://' + sys.argv[1]).hostname.encode('idna').decode()
U = f'https://{host}/'  # IDN은 punycode로


def call(m, **kw):
    q = f'{A}{m}?apikey={KEY}'
    if m.startswith('Get'):
        req = urllib.request.Request(q + '&' + urllib.parse.urlencode(kw))
    else:
        req = urllib.request.Request(q, json.dumps(kw).encode(), {'Content-Type': 'application/json; charset=utf-8'})
    return json.load(urllib.request.urlopen(req, timeout=30))['d']


if '--submit-urls' in sys.argv:
    su = sys.argv[1].rstrip('/') + '/'  # 경로 붙은 사이트는 그 주소 그대로 등록돼 있다
    urls = re.findall(r'<loc>([^<]+)</loc>', urllib.request.urlopen(su + 'sitemap.xml', timeout=30).read().decode())
    q = call('GetUrlSubmissionQuota', siteUrl=su)['DailyQuota']
    for i in range(0, min(len(urls), q), 500):
        call('SubmitUrlBatch', siteUrl=su, urlList=urls[i:min(i + 500, q)])
    print(f'RESULT: SUBMITTED {min(len(urls), q)}/{len(urls)} (하루 할당량 {q})'); sys.exit(0)

site = lambda: next((s for s in call('GetUserSites') if s['Url'] == U), None)
s = site()
if not s:
    call('AddSite', siteUrl=U); s = site(); print('added', U)
if not s['IsVerified']:
    if '--public' in sys.argv:
        d = Path(sys.argv[sys.argv.index('--public') + 1])
        (d / 'BingSiteAuth.xml').write_text(f'<?xml version="1.0"?>\n<users>\n\t<user>{s["AuthenticationCode"]}</user>\n</users>\n')
        print('wrote', d / 'BingSiteAuth.xml')
    if not call('VerifySite', siteUrl=U):
        print(f'RESULT: NOT_VERIFIED — {U}BingSiteAuth.xml 배포 후 다시 (또는 meta msvalidate.01={s["AuthenticationCode"]})'); sys.exit(1)
    print('verified')
feeds = {f['Url']: f for f in call('GetFeeds', siteUrl=U)}
sm = U + 'sitemap.xml'
if sm not in feeds:
    call('SubmitFeed', siteUrl=U, feedUrl=sm)  # SubmitSitemap 아님 — 그건 null만 주고 목록에 안 남는다
    feeds = {f['Url']: f for f in call('GetFeeds', siteUrl=U)}
print('RESULT: OK', ' | '.join(f"{u} {f['Status']} {f['UrlCount']}" for u, f in feeds.items()))
