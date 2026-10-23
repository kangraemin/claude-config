"""빙 웹마스터에 sitemap 주소를 하루 한도(보통 100개)만큼 나눠 낸다. 크론으로 매일 돌린다.
  python3 bing_daily_submit.py https://site/ [--first URL ...] [--dry-run]
- 빙이 아직 안 가져간 새 사이트는 sitemap만 내면 몇 주씩 안 온다. SubmitUrlBatch로 직접 넣으면 바로 가져간다.
- 낸 주소는 ~/.cache/bing-submit/<host>.json에 적어 두고 다음 날 그다음 것을 낸다. 다 내면 처음부터 다시 돈다(갱신 알림).
- --first: 매번 먼저 낼 주소(홈 등). 키: BING_WEBMASTER_API_KEY(~/.claude/.env).
"""
import argparse, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('site')
ap.add_argument('--first', nargs='*', default=[])
ap.add_argument('--dry-run', action='store_true')
a = ap.parse_args()
site = a.site.rstrip('/') + '/'
host = urllib.parse.urlparse(site).netloc

def env_key():
    k = os.environ.get('BING_WEBMASTER_API_KEY')
    if k: return k
    for line in Path('~/.claude/.env').expanduser().read_text().splitlines():
        if line.startswith('BING_WEBMASTER_API_KEY='): return line.split('=', 1)[1].strip().strip('"\'')
    sys.exit('BING_WEBMASTER_API_KEY 없음')

KEY = env_key()
API = 'https://ssl.bing.com/webmaster/api.svc/json/'

def call(method, body=None, **q):
    q.update(apikey=KEY)
    url = API + method + '?' + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={'Content-Type': 'application/json; charset=utf-8'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read() or b'{}')

def locs(url, depth=0):
    xml = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'bing-daily-submit'}), timeout=60).read().decode()
    out = re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', xml)
    if '<sitemapindex' in xml and depth < 2:
        return [u for s in out for u in locs(s, depth + 1)]
    return out

quota = call('GetUrlSubmissionQuota', siteUrl=site)['d']['DailyQuota']
state_f = Path.home() / '.cache/bing-submit' / f'{host}.json'
state_f.parent.mkdir(parents=True, exist_ok=True)
sent = set(json.loads(state_f.read_text())) if state_f.exists() else set()
all_urls = locs(site + 'sitemap.xml')
todo = [u for u in all_urls if u not in sent]
if not todo:  # 한 바퀴 다 냈으면 처음부터
    sent, todo = set(), all_urls
batch = list(dict.fromkeys(a.first + todo))[:quota]
print(f'sitemap {len(all_urls)} · 이미 낸 것 {len(sent)} · 오늘 한도 {quota} · 낼 것 {len(batch)}')
if not batch or a.dry_run:
    print('RESULT: SKIP'); sys.exit(0)
# 한 번에 너무 많이 넣으면 400(2026-10-23 2,836건). 500건씩 나눠 내고, 실패하면 거기까지 저장하고 멈춘다
done = []
for i in range(0, len(batch), 500):
    part = batch[i:i + 500]
    try:
        call('SubmitUrlBatch', {'siteUrl': site, 'urlList': part})
    except Exception as e:
        print(f'STOP {i}건 뒤 실패: {e}')
        break
    done += part
batch = done
sent.update(batch)
state_f.write_text(json.dumps(sorted(sent)))
print(f'RESULT: OK {len(batch)}건 제출, 남은 {len(all_urls) - len(sent & set(all_urls))}')
