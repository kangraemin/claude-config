"""Novelmint 책 게시 + Selects 출품 (LLM 없음). 2026-11-24 Novelmint Selects 3 강래민·김은미에 사용.
선행(사람·1회): 해당 Chrome 프로필에서 novelmint.ai Google 로그인, UI 언어 English(헤더 'Change language' → English — 책 원문 언어는 만들 때 UI 언어로 정해지고 못 바꿈).
책·챕터 만들기는 화면 흐름이 길어 수동/REPL로: /import 'Add chapters you wrote elsewhere' → textarea 'Paste your chapter here…' + 제목칸 'Chapter N' → 'Import as-is (free)' 체크 → 'Add chapter'.
표지: 파이프라인 Upload 탭 input[type=file][accept="image/*"] → 'Set as cover'(한 번에 안 먹으면 다시, 체크리스트 ✓ 확인).
  NM_TAB=id:<탭> python3 novelmint_publish_enter.py rate <series> <book> <chapterId...> [--rating PG]   # 챕터마다 등급+Content Review
  NM_TAB=id:<탭> python3 novelmint_publish_enter.py publish <series> <book>   # 책 Public on(+'Also release the imported chapters now'), 챕터 Public 확인
  NM_TAB=id:<탭> python3 novelmint_publish_enter.py enter <issue-slug> "<책 제목>" "Strong Lead|Full Cast"
  python3 novelmint_publish_enter.py check <read URL> <issue-slug>   # 로그아웃 상태로 공개·목록 노출 확인(urllib)
제출 잠금(mkdir <id>.submit.lock)·게이트는 호출자가 먼저 한다.
"""
import sys, os, time, json, re, urllib.request, html as H
sys.path.insert(0, os.path.expanduser('~/.claude/skills/chrome-direct')); import chromectl as c
T = os.environ.get('NM_TAB', 'novelmint.ai')
def js(code, t=30): return c.js_json(T, code, timeout=t)
def go(url, w=8): js('location.href=%s; return 1' % json.dumps(url)); time.sleep(w)
def click_text(txt):
    return js("""const b=[...document.querySelectorAll('button,label,[role=radio]')].filter(e=>e.getBoundingClientRect().width>0&&e.innerText.trim()===%s)[0]; if(!b) return 'NF'; b.click(); return 'ok'""" % json.dumps(txt))
base = lambda s, b: 'https://novelmint.ai/series/%s/book/%s' % (s, b)
cmd = sys.argv[1]
if cmd == 'rate':
    s, b, *chs = sys.argv[2:]; rating = 'PG'
    if '--rating' in chs: i = chs.index('--rating'); rating = chs[i+1]; chs = chs[:i] + chs[i+2:]
    label = {'G': 'G — All Ages', 'PG': 'PG — Teen (13+)', 'M': 'M — Mature (17+)'}[rating]
    for ch in chs:
        go(base(s, b) + '/chapter/%s/publish' % ch, 9); click_text(label); time.sleep(2); click_text('Run Content Review')
        for _ in range(12):
            time.sleep(5); t = js("return document.querySelector('main').innerText")
            m = re.search(r'✓ Reviewed[^\n]*', t)
            if m: print(ch, m.group(0)); break
        else: print(ch, 'REVIEW NOT DONE'); sys.exit(1)
elif cmd == 'publish':
    s, b = sys.argv[2:4]; go(base(s, b) + '/pipeline', 8)
    print(js("""const b=document.querySelector('button[data-tour=book-publish-toggle]'); if(!b) return 'NF'; const rel=[...document.querySelectorAll('label')].find(l=>l.innerText.includes('Also release the imported'))?.querySelector('input')?.checked; if(b.getAttribute('aria-checked')!=='true') b.click(); return 'release='+rel"""))
    time.sleep(8); go(base(s, b) + '/pipeline', 8)
    print(js("return [...document.querySelectorAll('button[role=switch]')].map(b=>b.previousElementSibling?.innerText.trim()+':'+b.getAttribute('aria-checked')).join(' ')"))
elif cmd == 'enter':
    slug, title, cat = sys.argv[2:5]; go('https://novelmint.ai/selects/' + slug, 9)
    setsel = """const s=[...document.querySelectorAll('select')].find(e=>e.getBoundingClientRect().width>0&&e.options[0]?.text===%s); if(!s) return 'NF'; const o=[...s.options].find(o=>o.text===%s); if(!o) return 'NO OPTION'; Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(s,o.value); s.dispatchEvent(new Event('change',{bubbles:true})); return o.value"""
    print('book', js(setsel % (json.dumps('Select a book…'), json.dumps(title)))); time.sleep(2)
    print('cat', js(setsel % (json.dumps('Select a category…'), json.dumps(cat)))); time.sleep(1.5)
    print(click_text('Enter this book')); time.sleep(8)
    t = js("return document.querySelector('main').innerText"); i = t.find('ENTERED IN THIS CYCLE')
    print(t[i:i+200].replace('\n', ' ') if i >= 0 else 'NOT ENTERED'); sys.exit(0 if i >= 0 and title in t[i:i+400] else 1)
elif cmd == 'check':
    url, slug = sys.argv[2:4]
    get = lambda u: H.unescape(re.sub(r'<[^>]+>', '\n', re.sub(r'<script.*?</script>|<style.*?</style>', '', urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})).read().decode(), flags=re.S)))
    bk = get(url); print('competing', 'Competing in Novelmint Selects' in bk)
    for n in (1, 2, 3): print('ch', n, len(get('%s/%d' % (url, n))))
    t = re.sub(r'\n\s*\n+', '\n', get('https://novelmint.ai/selects/' + slug)); ttl = re.search(r'\n([^\n]+) by ', bk); 
    sl, fc = t.find('Strong Lead\n1st'), t.find('Full Cast\n1st'); print('strong lead', sl, 'full cast', fc)
