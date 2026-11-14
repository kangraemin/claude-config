"""에어-비트 시티 공모전(airbeatcity.com/contest) 참가등록 → 접수번호 → 마이페이지 4종 업로드 → 제출 완료.
11/15 김은미 안(ABC26-C-0027)을 이 순서로 손으로 성공한 것을 옮긴 것(통째 실행은 미검증).
사용:
  python3 airbeat_submit.py register --profile "Profile 16" --info ~/Documents/oguri-works/개인정보-김은미.md \
      --email X --pw-env AIRBEAT_EM_PW --scale C --title "세 잎 돔" [--submit]
  python3 airbeat_submit.py upload --profile "Profile 16" --app a.pdf --panel p.pdf --hero h.jpg --desc d.pdf [--submit]
요점: 동의 3개는 '전문 보기'를 펼치고 스크롤 상자를 끝까지 내려야 풀린다. 업로드 input[type=file] 순서 0 참가신청서·1 판넬·2 대표이미지·3 설명서·4 모형도면.
대표이미지는 처음 한 번 무시될 때가 있어 진행률을 보고 다시 넣는다. 개인정보·비밀번호는 출력하지 않는다.
upload는 이미 로그인된 탭이 필요(register 직후 같은 탭, 또는 사이트에서 로그인)."""
import argparse, os, re, sys, time, json
sys.path.insert(0, os.path.expanduser('~/.claude/skills/chrome-direct')); import chromectl as c

def info(path):
    d = {}
    for ln in open(os.path.expanduser(path), encoding='utf-8'):
        m = re.match(r"-\s*([^:]+):\s*(.*)", ln.strip())
        if m: d[m.group(1).strip()] = m.group(2).strip()
    return d

def register(a, t):
    I = info(a.info); pw = c.secret(a.pw_env)
    b = re.sub(r"\D", "", I['생년월일']); ph = re.sub(r"\D", "", I['휴대폰'])
    V = dict(email=a.email, pw=pw, name=re.sub(r"\s*\(.*?\)", "", I['이름']).strip(), phone=f"{ph[:3]}-{ph[3:7]}-{ph[7:]}",
             birth=f"{b[:4]}-{b[4:6]}-{b[6:8]}", aff=re.sub(r"\s*\(.*?\)", "", I.get('소속', '')).strip(), title=a.title, scale=a.scale)
    c.js_json(t, "[...document.querySelectorAll('button')].filter(e=>e.innerText.trim()=='참가신청')[0].click(); return 1"); time.sleep(2)
    c.js_json(t, """const V=%s;
const set=(el,v)=>{Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el),'value').set.call(el,v);['input','change','blur'].forEach(x=>el.dispatchEvent(new Event(x,{bubbles:true})))};
const vis=[...document.querySelectorAll('input')].filter(e=>e.offsetParent);
const byLabel=t=>{const l=[...document.querySelectorAll('label')].filter(e=>e.offsetParent&&e.innerText.trim().startsWith(t))[0]; let n=l.nextElementSibling; while(n&&n.tagName!='INPUT'){const i=n.querySelector&&n.querySelector('input'); if(i) return i; n=n.nextElementSibling;} return n};
set(vis.filter(e=>e.type=='email').pop(),V.email); const pws=vis.filter(e=>e.type=='password'); set(pws[pws.length-2],V.pw); set(pws[pws.length-1],V.pw);
set(byLabel('대표자 성명'),V.name); set(byLabel('연락처'),V.phone); set(byLabel('생년월일'),V.birth); if(V.aff) set(byLabel('소속'),V.aff); set(byLabel('작품명'),V.title);
const btn=t=>[...document.querySelectorAll('button')].filter(e=>e.offsetParent&&e.innerText.trim().startsWith(t));
btn('개인')[0].click(); btn(V.scale+String.fromCharCode(10))[0].click(); return 1""" % json.dumps(V, ensure_ascii=False))
    sc = "const s=[...document.querySelectorAll('*')].filter(e=>e.offsetParent&&e.scrollHeight>e.clientHeight+20&&getComputedStyle(e).overflowY!='visible'); s.forEach(e=>{e.scrollTop=e.scrollHeight;e.dispatchEvent(new Event('scroll',{bubbles:true}))}); return s.length"
    for _ in range(4):
        c.js_json(t, "const v=[...document.querySelectorAll('button')].filter(e=>e.offsetParent&&e.innerText.trim()=='전문 보기'); if(v[0]) v[0].click(); return v.length"); time.sleep(1.2)
        c.js_json(t, sc); time.sleep(0.8)
    c.js_json(t, "document.querySelector('button[data-act=agree-all]').click(); return 1"); time.sleep(1)
    ok = c.js_json(t, "return [...document.querySelectorAll('button[data-act=agree-set]')].filter(e=>e.dataset.arg.endsWith(':1')).every(e=>e.getAttribute('aria-checked')=='true')")
    print(json.dumps({'agreed': ok}))
    if not ok: print('RESULT: FAILED 동의 칸이 안 풀림'); return 1
    if not a.submit: print('RESULT: DRYRUN 채움(접수번호 발급 안 누름)'); return 0
    c.js_json(t, "document.querySelector('button[data-act=submit-apply]').click(); return 1"); time.sleep(10)
    reg = re.findall(r'ABC26-[A-Z]-\d+', c.page_text(t))
    print(f"RESULT: {'OK '+reg[0] if reg else 'UNCONFIRMED 접수번호 안 보임 — 다시 누르지 말고 로그인해 마이페이지 확인'}"); return 0 if reg else 2

def upload(a, t):
    if 'contest/my' not in c.js_json(t, "return location.href"):
        c.js_json(t, "const b=document.querySelector('button[data-act=go-my]'); if(b) b.click(); return 1"); time.sleep(4)
    for i, f in enumerate([a.app, a.panel, a.hero, a.desc]):
        for k in range(2):
            before = c.page_text(t).count('UPLOAD')
            print(i, os.path.basename(f), c.upload_file(t, f, idx=i)); time.sleep(8)
            if c.page_text(t).count('UPLOAD') > before: break
    tx = c.page_text(t); pct = re.findall(r'진행률\s*(\d+)%', tx)
    print(json.dumps({'progress': pct}))
    if not pct or pct[0] != '100': print('RESULT: FAILED 진행률 100% 아님'); return 1
    if not a.submit: print('RESULT: DRYRUN 업로드만(제출 완료 안 누름)'); return 0
    c.js_json(t, "document.querySelector('button[data-act=final-submit]').click(); return 1"); time.sleep(4)
    ok = 'SUBMITTED' in c.page_text(t)
    print('RESULT:', 'OK SUBMITTED' if ok else 'UNCONFIRMED'); return 0 if ok else 2

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('cmd', choices=['register', 'upload'])
    p.add_argument('--profile', default='Profile 16'); p.add_argument('--info'); p.add_argument('--email'); p.add_argument('--pw-env')
    p.add_argument('--scale', default='C'); p.add_argument('--title')
    for k in ('app', 'panel', 'hero', 'desc'): p.add_argument('--' + k)
    p.add_argument('--tab'); p.add_argument('--submit', action='store_true'); a = p.parse_args()
    t = a.tab or c.new_tab('https://airbeatcity.com/contest', profile=a.profile); time.sleep(5)
    sys.exit(register(a, t) if a.cmd == 'register' else upload(a, t))
