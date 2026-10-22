"""구글 서치콘솔 '색인 생성 요청' 버튼을 URL마다 누른다.
  python3 gsc_request_index.py <속성 https://host/> URL [URL ...]   → URL마다 RESULT 줄, 마지막 RESULT: <요청 n건>/<할당량 초과 여부>

- 하는 일: 속성 개요 화면 → 상단 'URL 검사' 입력칸에 URL → Enter → '색인 생성 요청' → '색인 생성 요청됨' 대기.
- 왜 화면 조작인가: URL Inspection API는 상태 조회만 되고 색인 요청은 없다. Indexing API는 채용공고·라이브 방송 페이지 전용.
- 사전 조건: Chrome 'Profile 1'(remin1994) 계정이 속성 소유자. API로만 소유자에 넣은 속성은 GSC 화면이 'not-verified'로 가므로
  그 화면의 '소유권 확인'을 한 번 누르면 '자동으로 확인됨'으로 풀린다(아래 코드가 자동 처리). 하위 경로 속성(https://host/path/)은 inspect 화면이 404가 나므로
  루트 속성(https://host/)으로 연다. 하루 할당량(약 10건)을 넘으면 '할당량 초과'가 떠서 거기서 멈춘다.
- 이미 색인됐거나 대기열에 있는 URL을 다시 요청해도 순위는 안 바뀐다(구글 안내). 그래서 '이미 등록됨'이면 버튼을 누르지 않는다.
"""
import os, re, sys, time, urllib.parse as u
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

prop, urls = sys.argv[1].rstrip('/') + '/', sys.argv[2:]
SEL = 'input[aria-label$="에 있는 모든 URL 검사"]'  # 라벨 앞 주소 표기가 속성마다 달라(한글 도메인 등) 끝부분만 맞춘다
t = c.new_tab('https://search.google.com/search-console?resource_id=' + u.quote(prop, safe=''), profile='Profile 1')
done, quota = 0, False
try:
    c.google_relogin(t)
    time.sleep(6)
    if 'not-verified' in c.js_json(t, 'return location.href'):  # API로만 소유자인 속성
        c.js_json(t, "const b=[...document.querySelectorAll('[role=button],button,a')].find(e=>e.innerText&&e.innerText.trim()==='소유권 확인');b&&b.click();return 1")
        time.sleep(10)
    for url in urls:
        c.goto(t, 'https://search.google.com/search-console?resource_id=' + u.quote(prop, safe=''))
        time.sleep(3)  # goto 직후엔 이전 화면 입력칸이 잠깐 보였다 사라진다
        for k in range(8):  # 새 화면이 그려질 때까지 넣기를 다시 시도
            try:
                c.wait(t, sel=SEL, timeout=40); c.fill(t, SEL, url); break
            except RuntimeError:
                if k == 7: raise
                time.sleep(3)
        c.js_json(t, f"const i=document.querySelector('{SEL}');i.focus();"
                     "for(const ty of ['keydown','keypress','keyup'])i.dispatchEvent(new KeyboardEvent(ty,{key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true}));return 1")
        for _ in range(12):
            time.sleep(5)
            tx = c.page_text(t)
            if '색인 생성 요청' in tx and ('URL이 Google에 등록' in tx or 'Google에 등록되어 있지 않음' in tx or 'URL이 Google에 등록되어 있음' in tx):
                break
        if 'URL이 Google에 등록되어 있음' in tx:
            print('RESULT', url, '이미 등록됨'); continue
        c.js_json(t, "const b=[...document.querySelectorAll('[role=button],button,span')].filter(e=>e.innerText&&e.innerText.trim()==='색인 생성 요청');"
                     "const el=b[b.length-1];(el.closest('[role=button]')||el).click();return b.length")
        st = '시간 초과'
        for _ in range(18):
            time.sleep(10)
            tx = c.page_text(t)
            if '색인 생성 요청됨' in tx: st = '요청됨'; break
            if '할당량' in tx: st = '할당량 초과'; break
        print('RESULT', url, st)
        if st == '요청됨': done += 1
        if st == '할당량 초과': quota = True; break
finally:
    c.close_tab(t)
print(f'RESULT: 요청 {done}건' + (' / 할당량 초과' if quota else ''))
