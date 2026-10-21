"""python3 kakao_share_cache.py https://site [--check]

카카오톡 공유 미리보기(OG) 캐시를 초기화하고 새 메타 정보를 출력한다.
- developers.kakao.com/tool/debugger/sharing 에 URL을 넣고 '캐시 초기화' → '메타 정보 조회'.
- --check 면 초기화 없이 조회만 한다.
- 로그아웃이면 QR 로그인 페이지를 열고 QR을 잘라 텔레그램(CONTEST_TG_TOKEN/CHAT_ID)으로 보낸다.
  QR은 약 4분 40초 유효 → 270초마다 페이지를 새로 열어 새 QR을 보낸다(최대 15분). 사람은 카톡 스캔만 한다.
- 카카오는 이 캐시 초기화를 API로 열어 두지 않아 화면 조작이다. 카카오 계정 비밀번호는 저장하지 않는다(QR 전용).
함정:
- 로그인 판정은 location.hostname 으로 한다. QR 페이지 주소의 continue 파라미터에 developers.kakao.com 이 들어 있어 href로 보면 오판한다.
- 만료되면 '유효 시간이 만료되었습니다' 모달이 QR을 가린다 → 새로고침 버튼 대신 페이지를 다시 연다.
- 이 사이트에선 js_json 이 None 을 돌려준 적이 있어 run_js(IIFE)로 읽는다.
"""
import os, subprocess, sys, time
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

DBG = 'https://developers.kakao.com/tool/debugger/sharing'
QR = 'https://accounts.kakao.com/qr_login/?continue=https%3A%2F%2Fdevelopers.kakao.com%2Flogin%3Fcontinue%3D%252Ftool%252Fdebugger%252Fsharing&lang=ko'
TMP = '/tmp/kakao-share'
site = next((a for a in sys.argv[1:] if a.startswith('http')), None)
if not site: print(__doc__); sys.exit(1)
check_only = '--check' in sys.argv
os.makedirs(TMP, exist_ok=True)


def env():
    e = {}
    for l in open(os.path.expanduser('~/.claude/.env')):
        l = l.strip().removeprefix('export ')
        if '=' in l and not l.startswith('#'):
            k, v = l.split('=', 1); e[k] = v.strip('"\'')
    return e['CONTEST_TG_TOKEN'], e['CONTEST_TG_CHAT_ID']


def send_qr(t):
    from PIL import Image
    c.goto(t, QR); time.sleep(6)
    c.shot(t, f'{TMP}/qr.png')
    im = Image.open(f'{TMP}/qr.png'); w, h = im.size
    im.crop((int(w * .41), int(h * .46), int(w * .59), int(h * .71))).save(f'{TMP}/qr_crop.png')
    tok, chat = env()
    subprocess.run(['curl', '-s', '-o', '/dev/null', '-F', f'chat_id={chat}', '-F', f'photo=@{TMP}/qr_crop.png', '-F',
                    f'caption=카카오 디벨로퍼스 로그인 QR ({site} 공유 캐시) — 카톡 더보기 > 스캔', f'https://api.telegram.org/bot{tok}/sendPhoto'])
    print(f'QR sent {time.strftime("%H:%M:%S")} ({TMP}/qr_crop.png)', flush=True)


def host(t):
    return c.run_js(t, 'location.hostname')


def click(t, label):
    return c.run_js(t, "(()=>{const b=[...document.querySelectorAll('button')].find(b=>b.innerText.trim().startsWith(%r));"
                       "if(!b)return 'NF';setTimeout(()=>b.click(),10);return 'ok'})()" % label)


t = c.new_tab(DBG, profile='Profile 1'); time.sleep(8)
try:
    if host(t) != 'developers.kakao.com':
        send_qr(t); last = time.time()
        for _ in range(300):
            if host(t) == 'developers.kakao.com': break
            if time.time() - last > 270: send_qr(t); last = time.time()
            time.sleep(3)
        else:
            print('RESULT: LOGIN_TIMEOUT'); sys.exit(2)
        time.sleep(6)
    if not c.run_js(t, "!!document.querySelector('input[placeholder*=\"공유할 URL\"]')"):
        c.goto(t, DBG); time.sleep(8)
    c.run_js(t, "(()=>{const i=document.querySelector('input[placeholder*=\"공유할 URL\"]');"
                "Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,%r);"
                "i.dispatchEvent(new Event('input',{bubbles:true}));return 1})()" % site)
    time.sleep(1)
    cleared = ''
    if not check_only:
        if click(t, '캐시 초기화') == 'NF': print('RESULT: FAIL no reset button'); sys.exit(1)
        time.sleep(5)
        x = c.run_js(t, 'document.body.innerText') or ''
        i = x.find('처리 결과'); cleared = x[i + 5:].split('\n')[0].strip() if i >= 0 else '?'
        print('reset:', cleared)
    click(t, '메타 정보 조회'); time.sleep(6)
    x = c.run_js(t, 'document.body.innerText') or ''
    i = x.find('OG(Open Graph)'); print(x[i:i + 700] if i >= 0 else x[:500])
    print('RESULT: OK', cleared or 'checked')
finally:
    c.close_tab(t)
