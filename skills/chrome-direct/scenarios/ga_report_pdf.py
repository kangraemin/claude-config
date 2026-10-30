#!/usr/bin/env python3
"""GA4 표준 보고서를 기간·표 검색어·국가 비교를 걸어 열고, GA 자체 '공유 → 파일 다운로드 → PDF 다운로드'로 내보낸다.

  ga_report_pdf.py --report all-pages-and-screens --search jeju-stay --start 20261010 --end 20261029 --country KR --out a.pdf
  ga_report_pdf.py --report top-events --search stay_ --start 20261010 --end 20261029 --country KR --out b.pdf
- --report: GA 보고서 r= 값(all-pages-and-screens, top-events 등). 이벤트 상세 같은 대시보드 화면은 PDF 버튼이 먹지 않는다(10/30) → --shot 캡처로 대신.
- 왜 화면 조작인가: 공모전 주최 측 등 제3자에게 'GA에서 직접 뽑은' 증빙을 줄 때. 숫자만 필요하면 Data API(서비스 계정)가 낫다.
- 함정(10/30): 비교 칩은 URL에 넣어도 꺼진 채로 열린다 → mat-slide-toggle을 켠다. 메뉴 항목은 .click()이 안 먹고 __press(chromectl.press)만 먹는다.
  공유 버튼은 토글이라 메뉴가 열린 상태에서 다시 누르면 닫힌다. Chrome Apple 이벤트라 tmux -L gh에서 돌린다.
마지막 줄 RESULT: OK <경로> | FAIL <이유>
"""
import argparse, glob, json, os, shutil, sys, time, urllib.parse
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

ap = argparse.ArgumentParser()
ap.add_argument('--account', default='a136249894p364443214')
ap.add_argument('--report', required=True)
ap.add_argument('--search', default='')
ap.add_argument('--start', required=True)
ap.add_argument('--end', required=True)
ap.add_argument('--country', help='비교로 붙일 국가 ID (예: KR)')
ap.add_argument('--label', default='국내')
ap.add_argument('--out', required=True)
ap.add_argument('--profile', default='Profile 1')
a = ap.parse_args()

p = f'_u.date00={a.start}&_u.date01={a.end}'
if a.search:
    p += f'&_r.explorerCard..filterTerm={a.search}'
if a.country:
    p += '&_u..comparisons=' + json.dumps([{"name": a.label, "filters": [{"fieldName": "countryId", "expressionList": [a.country], "isCaseSensitive": True}]}], ensure_ascii=False)
url = f'https://analytics.google.com/analytics/web/#/{a.account}/reports/explorer?params={urllib.parse.quote(p, safe="")}&r={a.report}'
DL = os.path.expanduser('~/Downloads')
MENU = "return [...document.querySelectorAll('*')].filter(e=>e.offsetParent&&e.children.length==0&&/다운로드/.test(e.innerText||'')).map(e=>e.innerText.trim()).join('|')"

t = c.new_tab(url, a.profile)
try:
    c.google_relogin(t)
    time.sleep(12)
    c.shot(t, '/tmp/ga_report_pdf.png')  # 앞으로 띄워야 Angular 화면이 그려진다
    if a.country:
        c.js_json(t, "document.querySelectorAll('mat-slide-toggle button[aria-checked=false]').forEach(b=>b.click()); return 1")
        time.sleep(6)
    before = set(glob.glob(DL + '/*.pdf'))
    c.js_json(t, "const b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.getAttribute('aria-label')=='이 보고서 공유'); b.click(); return 1")
    time.sleep(3)
    if '파일 다운로드' not in c.js_json(t, MENU):
        print('RESULT: FAIL 공유 메뉴 안 열림'); sys.exit(1)
    c.press(t, text='파일 다운로드'); time.sleep(3)
    c.press(t, text='PDF 다운로드')
    for _ in range(30):
        time.sleep(2)
        new = [f for f in set(glob.glob(DL + '/*.pdf')) - before if not f.endswith('.crdownload')]
        if new:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            shutil.move(new[0], a.out)
            print('RESULT: OK', a.out); sys.exit(0)
    print('RESULT: FAIL PDF가 받아지지 않음(대시보드형 화면이면 캡처로)'); sys.exit(1)
finally:
    c.close_tab(t)
