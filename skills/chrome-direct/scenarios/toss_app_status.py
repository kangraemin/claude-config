#!/usr/bin/env python3
"""앱인토스 앱의 버전·검토 상태를 읽기만 한다(클릭 없음).
  python3 toss_app_status.py <appName> [workspace=35273]
로그인된 콘솔 창(이미 workspace 탭이 열린 창)에 새 탭을 열어 읽고 닫는다.
기본 프로필 창은 콘솔 로그아웃 상태라 new_tab(profile 없음)을 쓰면 로그인 화면만 나온다."""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chromectl as c
app = sys.argv[1]; ws = sys.argv[2] if len(sys.argv) > 2 else '35273'
u = f'https://apps-in-toss.toss.im/workspace/{ws}/mini-app/{app}/app-build'
before = {r[4] for r in c.tabs(with_id=True)}
r = c.jxa("var ws=C.windows(); for (var i=0;i<ws.length;i++){var ts=ws[i].tabs(); for(var j=0;j<ts.length;j++){ if(String(ts[j].url()).indexOf('apps-in-toss.toss.im/workspace/')>=0){ ws[i].tabs.push(C.Tab({url:%s})); return 'ok';}}} C.windows[0].tabs.push(C.Tab({url:%s})); return 'first';" % (c.q(u), c.q(u)))
time.sleep(8)
new = [x for x in c.tabs(with_id=True) if x[4] not in before]
if not new: print('STATUS: ERROR tab not opened'); sys.exit(1)
t = 'id:' + new[-1][4]
tx = c.page_text(t)
c.close_tab(t)
if '이메일 로그인' in tx and '버전 내역' not in tx: print('STATUS: LOGIN_REQUIRED'); sys.exit(2)
banner = re.search(r'버전 등록하기\s*\n?\s*([^\n]*)', tx)
print('BANNER:', banner.group(1).strip() if banner else '')
for m in re.finditer(r'(\d{8}-\d+)\s*\t?\s*\|?\s*[\s\S]{0,20}?(\d+\.\d+\.\d+)[\s\S]{0,20}?(검토 필요|검토 중|반려|승인|출시 완료|출시 대기|[가-힣 ]{2,8})\s', tx):
    print('VERSION', m.group(1), m.group(2), m.group(3).strip())
