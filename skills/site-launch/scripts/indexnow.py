"""IndexNow 알림(네이버·빙 등). 키 파일 https://<host>/<key>.txt (내용=키)가 먼저 배포돼 있어야 한다.
  python3 indexnow.py <host> <key> <sitemap.xml 경로 또는 URL>
배포 직후 api.indexnow.org는 403일 수 있다(키 파일 전파 대기) — 몇 분 뒤 다시."""
import json, re, sys, urllib.request
host, key, sm = sys.argv[1:4]
xml = urllib.request.urlopen(urllib.request.Request(sm, headers={'User-Agent': 'Mozilla/5.0'})).read().decode() if sm.startswith('http') else open(sm).read()
urls = re.findall(r'<loc>(.*?)</loc>', xml)[:10000]
for ep in ['https://searchadvisor.naver.com/indexnow', 'https://api.indexnow.org/indexnow']:
    try:
        r = urllib.request.urlopen(urllib.request.Request(ep, json.dumps({'host': host, 'key': key, 'keyLocation': f'https://{host}/{key}.txt', 'urlList': urls}).encode(), {'Content-Type': 'application/json; charset=utf-8'}), timeout=30)
        print('indexnow', ep.split('/')[2], r.status, len(urls))
    except urllib.error.HTTPError as e:
        print('indexnow', ep.split('/')[2], e.code)
