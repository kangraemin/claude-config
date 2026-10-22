"""애드센스 홈 화면의 예상 수입·잔고·지급 단계 경고를 읽는다(읽기 전용).
  python3 adsense_earnings.py   → EARN 오늘/어제/지난7일/이번달, BALANCE, ALERT 줄, 사이트별 지난 7일, RESULT
- 왜 화면인가: AdSense Management API는 사람 OAuth가 필요하다(서비스 계정 불가). Chrome 'Profile 1'(remin1994)로 연다.
"""
import os, re, sys, time
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c
t = c.new_tab('https://www.google.com/adsense/new/u/0/pub-4785237655148075/home', profile='Profile 1')
try:
    c.google_relogin(t); time.sleep(8); c.shot(t, '/tmp/adsense_home.png'); time.sleep(3)
    tx = c.page_text(t)
    for label in ['오늘 현재까지', '어제', '지난 7일', '이번 달']:
        m = re.search(re.escape(label) + r'\s*\n\s*(US\$[\d.,]+)', tx)
        print('EARN', label, m and m[1])
    m = re.search(r'잔고\s*\n(?:more_vert\s*\n)?\s*(\$[\d.,]+)', tx); print('BALANCE', m and m[1])
    for a in re.findall(r'조치 필요: [^\n]+', tx): print('ALERT', a)
    if '은행 세부정보 추가' in tx: print('ALERT 지급 수단(은행 세부정보) 미등록')
    for host, v in re.findall(r'\n\t?\s*([a-z0-9.\-]+\.[a-z]{2,})\s*\n\t?\s*(US\$[\d.,]+)', tx): print('SITE', host, v)
    print('RESULT: OK')
finally:
    c.close_tab(t)
