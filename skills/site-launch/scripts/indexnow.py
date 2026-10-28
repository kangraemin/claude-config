"""IndexNow 알림(네이버·빙 등). 키 파일 https://<host>/<key>.txt (내용=키)가 먼저 배포돼 있어야 한다.
  python3 indexnow.py <host> <key> <sitemap.xml 경로 또는 URL>
배포 직후 api.indexnow.org는 403일 수 있다(키 파일 전파 대기) — 몇 분 뒤 다시."""
import json, re, sys, urllib.request
host, key, sm = sys.argv[1:4]
xml = urllib.request.urlopen(urllib.request.Request(sm, headers={'User-Agent': 'Mozilla/5.0'})).read().decode() if sm.startswith('http') else open(sm).read()
all_urls = re.findall(r'<loc>(.*?)</loc>', xml)
# 한 번에 1만 개까지만 받는다. 나눠서 다 보낸다(먹맵 3.7만 개가 앞 1만 개만 가던 일, 2026-10-28)
for i in range(0, len(all_urls), 10000):
    urls = all_urls[i:i + 10000]
    for ep in ['https://searchadvisor.naver.com/indexnow', 'https://api.indexnow.org/indexnow']:
        try:
            r = urllib.request.urlopen(urllib.request.Request(ep, json.dumps({'host': host, 'key': key, 'keyLocation': f'https://{host}/{key}.txt', 'urlList': urls}).encode(), {'Content-Type': 'application/json; charset=utf-8'}), timeout=60)
            print('indexnow', ep.split('/')[2], r.status, i + len(urls))
        except urllib.error.HTTPError as e:
            print('indexnow', ep.split('/')[2], e.code, i + len(urls))
