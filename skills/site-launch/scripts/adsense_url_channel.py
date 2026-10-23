"""애드센스 URL 채널을 만든다(같은 URL이 이미 있으면 건너뜀).
  python3 adsense_url_channel.py kangraemin.github.io/oneul-kkum [--dry-run]
- 왜: 한 도메인에 여러 사이트(개인 블로그 + 하위 경로 서비스)가 섞이면 홈의 사이트별 수입으로는 나눌 수 없다. URL 채널은 접두사 아래 페이지 수입만 따로 센다(코드 변경 없음, 만든 시점부터 집계·소급 안 됨).
- 왜 화면인가: AdSense Management API는 사람 OAuth가 필요하다(서비스 계정 불가). Chrome 'Profile 1'(remin1994).
- 흐름: 보고서 화면 ?ol=url_channels(설정 톱니 > URL 채널 관리) → 목록에 있으면 끝 → '채널 추가' → textarea[aria-label=URL] → '저장'.
"""
import os, sys, time
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

args = [a for a in sys.argv[1:] if not a.startswith('--')]
dry = '--dry-run' in sys.argv
if not args:
    sys.exit(__doc__)
want = args[0].removeprefix('https://').removeprefix('http://').rstrip('/')
B = 'https://adsense.google.com/adsense/u/0/pub-4785237655148075/'
t = c.new_tab(B + 'reporting/?rt=d&ol=url_channels', profile='Profile 1')
try:
    c.google_relogin(t); time.sleep(9); c.shot(t, '/tmp/adsense_urlch.png'); time.sleep(2)
    tx = c.page_text(t)
    if 'URL 채널 관리' not in tx:
        print('RESULT: FAIL URL 채널 관리 화면이 안 열림'); sys.exit(1)
    lst = tx[tx.find('작업'):]
    if want in lst:
        print('RESULT: EXISTS', want); sys.exit(0)
    if dry:
        print('RESULT: DRY_RUN 추가할 채널', want); sys.exit(0)
    ok = c.js_json(t, "const b=[...document.querySelectorAll('material-button,button')].find(e=>e.textContent.trim()==='채널 추가'); b&&b.click(); return !!b")
    time.sleep(3)
    ok = ok and c.js_json(t, """const a=document.querySelector('textarea[aria-label="URL"]'); if(!a) return false;
      a.focus(); Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(a,%s);
      a.dispatchEvent(new Event('input',{bubbles:true})); a.dispatchEvent(new Event('change',{bubbles:true})); return true""" % repr(want).replace("'", '"'))
    time.sleep(1)
    ok = ok and c.js_json(t, "const b=[...document.querySelectorAll('material-button,button')].filter(e=>e.textContent.trim()==='저장').pop(); if(!b||b.hasAttribute('disabled')) return false; b.click(); return true")
    time.sleep(6); c.shot(t, '/tmp/adsense_urlch.png'); time.sleep(1)
    tx = c.page_text(t)
    print('RESULT:', 'CREATED' if ok and want in tx[tx.find('작업'):] else 'FAIL 저장 확인 안 됨', want)
finally:
    c.close_tab(t)
