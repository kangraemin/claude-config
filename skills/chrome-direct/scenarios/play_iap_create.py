#!/usr/bin/env python3
"""Usage: play_iap_create.py --dev <개발자ID> --app <앱ID> --prefix <상품ID 접두사> --items <items.json> [--only k1,k2] [--submit]

Play Console 일회성 제품(비소모품)을 하나씩 만들고 구매 옵션 'buy' + 전 지역 KRW 일괄 가격 + '활성화'까지 한다(2026-11-06 골골냥 10개 검증).
items.json: {"frog_hat": {"name": "개구리 모자", "desc": "50자(영문 기준) 이상 설명", "price": 1100}, ...}
멱등: /one-time-products/sku/<id>가 이미 '활성'이면 건너뛴다. --submit 없으면 목록만 출력.
Gotchas(전부 실측):
- 이름·설명은 SETV(value setter)로 넣으면 화면엔 보여도 모델이 비어 '변경사항을 저장할 수 없습니다.' → focus+select+execCommand('insertText').
  탭이 앞에 없으면 execCommand가 안 먹는다 → 넣기 전 c.front, 설명은 한 번 더 지우고 다시 넣는다. 설명 50자(영문 기준) 미만은 경고.
- 가격표 행 체크박스는 'Set prices' → '가격 일괄 수정'(숨은 material-select-item, MC)을 연 뒤에야 생긴다.
  'Set prices' 버튼은 실제 클릭(rclick)만 먹는다. 탭이 뒤에 있으면 표가 안 그려지므로 c.front + 스크롤.
- 하단 바 '계속'은 네이티브 click 먼저, 안 되면 rclick. 'Play Console 개선 설문' 팝업이 오른쪽 아래 '계속'을 덮는다.
- KRW는 100원 단위로 반올림된다(990→1,000, 1980→2,000) → items 가격을 100원 단위로 둔다.
- 실행 래퍼로 인자를 넘길 때 띄어쓰기에서 잘리면 '개구리 모자'가 이름·설명으로 갈라진다 → 값은 JSON 파일로 넘긴다.
RESULT: ACTIVATED k | ALREADY_ACTIVE k | DESC_FAIL k | SELECT_FAIL k | PRICE_FAIL k | FAIL k
"""
import json,re,sys,time
from _common import c, parser
ap=parser("Play one-time products create+price+activate",submit=True)
ap.add_argument("--dev",required=True); ap.add_argument("--app",required=True)
ap.add_argument("--prefix",required=True); ap.add_argument("--items",required=True); ap.add_argument("--only")
a=ap.parse_args()
BASE=f"https://play.google.com/console/u/0/developers/{a.dev}/app/{a.app}/"
PRE=("const MC=b=>{['pointerdown','mousedown','pointerup','mouseup','click'].forEach(n=>b.dispatchEvent(new MouseEvent(n,{bubbles:true,cancelable:true,view:window})))};"
     "const SETV=(el,v)=>{el.focus();const p=Object.getOwnPropertyDescriptor(el.tagName=='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value');p.set.call(el,v);for(const n of ['input','change','blur'])el.dispatchEvent(new Event(n,{bubbles:true}));};"
     "const VIS=e=>e&&e.offsetParent!==null;")
T=None
def J(code,wait=0):
    for k in range(4):
        try: r=c.js_json(T,PRE+code); break
        except RuntimeError:
            if k==3: raise
            time.sleep(3)
    if wait: time.sleep(wait)
    return r
def go(path,wait=10): J("location.href="+json.dumps(BASE+path)+";return 1"); time.sleep(wait)
def rc(js):
    J("document.querySelectorAll('[data-gs]').forEach(x=>x.removeAttribute('data-gs'));const x=("+js+");x.scrollIntoView({block:'center'});x.setAttribute('data-gs','1');return 1")
    time.sleep(0.5); c.front(T); time.sleep(0.3); c.rclick(T,sel="[data-gs='1']")
def one(key,it):
    pid=a.prefix+key
    PUT="const put=(e,v)=>{e.focus();e.select();document.execCommand('insertText',false,v);e.dispatchEvent(new Event('blur',{bubbles:true}));};"
    # idempotent: exists?
    go("one-time-products/sku/"+pid,10)
    t=J("return document.body.innerText")
    if "check_circle\n활성" in t or re.search(r"\n활성\n",t):
        print("RESULT: ALREADY_ACTIVE",key); return 0
    go("one-time-products/create",12)
    c.front(T); time.sleep(0.5)
    print(J(PUT+"const i=[...document.querySelectorAll('input')].filter(x=>x.getClientRects().length);const ta=[...document.querySelectorAll('textarea')].find(x=>x.getClientRects().length);put(i[0],%s);put(i[2],%s);put(ta,%s);return i[0].value+'|'+i[2].value+'|'+ta.value.length"%(json.dumps(pid),json.dumps(it['name']),json.dumps(it['desc'])),2))
    c.front(T)
    J("const ta=[...document.querySelectorAll('textarea')].find(x=>x.getClientRects().length);ta.focus();ta.select();document.execCommand('delete');document.execCommand('insertText',false,%s);ta.dispatchEvent(new Event('blur',{bubbles:true}));return 1"%json.dumps(it['desc']),2)
    inv=J("return [...document.querySelectorAll('textarea')].find(x=>x.getClientRects().length).getAttribute('aria-invalid')")
    t=J("return document.body.innerText")
    i_=t.find("설명 *"); print("desc",inv,t[i_:i_+40].replace("\n"," "))
    if inv=="true": print("RESULT: DESC_FAIL",key); return 2
    J("const b=[...document.querySelectorAll('button')].find(x=>x.getClientRects().length&&x.innerText.trim()=='다음');b.click();return 1",5)
    print(J(PUT+"const i=[...document.querySelectorAll('input[type=text]')].filter(x=>x.getClientRects().length)[0];put(i,'buy');return i.value",2))
    CNT="return [...document.querySelectorAll('material-select-item')].filter(e=>e.innerText.trim()=='가격 일괄 수정').length"
    for k in range(3):
        if J(CNT): break
        rc("(()=>{const x=[...document.querySelectorAll('*')].filter(e=>VIS(e)&&e.children.length==0&&e.textContent.trim()=='Set prices')[0];let p=x;while(p&&p.tagName!='BUTTON')p=p.parentElement;return p})()"); time.sleep(2)
    J("const o=[...document.querySelectorAll('material-select-item')].find(e=>e.innerText.trim()=='가격 일괄 수정');MC(o);return 1",4)
    SA="document.querySelector(\"mat-checkbox[aria-label='모든 행 선택']\")"
    J("const b=[...document.querySelectorAll('button')].find(e=>e.offsetParent&&e.innerText.trim()=='나중에');if(b)b.click();return 1",1)
    for k in range(15):
        c.front(T)
        J("const x=[...document.querySelectorAll('*')].filter(e=>VIS(e)&&e.children.length==0&&e.textContent.trim()=='Set prices')[0];if(x){x.scrollIntoView({block:'start'});window.scrollBy(0,-250)}return 1",1)
        if J("return !!"+SA): break
        time.sleep(2)
    time.sleep(2)
    if J("return "+SA+".getAttribute('aria-checked')")!="true":
        J("MC("+SA+".querySelector('.mat-checkbox-container'));return 1",3)
    al=J("return "+SA+".getAttribute('aria-checked')"); print("all",al)
    if al!="true": print("RESULT: SELECT_FAIL",key); return 2
    J("const b=[...document.querySelectorAll('button')].find(e=>e.offsetParent&&e.innerText.trim()=='나중에');if(b)b.click();return 1",1)
    for k in range(4):
        c.front(T)
        J("const x=[...document.querySelectorAll('*')].filter(e=>e.children.length==0&&e.textContent.trim()=='가격을 설정할 국가 및 지역 선택')[0];let p=x;for(let k=0;k<4;k++)p=p.parentElement;[...p.querySelectorAll('button')].find(b=>b.innerText.trim()=='계속').click();return 1",4)
        if J("return !![...document.querySelectorAll('input')].find(e=>e.getClientRects().length&&(e.getAttribute('aria-label')||'').includes('새로운 가격'))"): break
        rc("(()=>{const x=[...document.querySelectorAll('*')].filter(e=>e.children.length==0&&e.textContent.trim()=='가격을 설정할 국가 및 지역 선택')[0];let p=x;for(let k=0;k<4;k++)p=p.parentElement;return [...p.querySelectorAll('button')].find(b=>b.innerText.trim()=='계속')})()"); time.sleep(4)
    print("price",J("const i=[...document.querySelectorAll('input')].find(e=>e.getClientRects().length&&(e.getAttribute('aria-label')||'').includes('새로운 가격'));SETV(i,"+json.dumps(str(it['price']))+");return i.value",2))
    J("const b=[...document.querySelectorAll('button')].find(e=>e.getClientRects().length&&e.innerText.trim()=='적용');b.click();return 1",6)
    c.front(T); J("const x=[...document.querySelectorAll('*')].filter(e=>VIS(e)&&e.children.length==0&&e.textContent.trim()=='Set prices')[0];if(x){x.scrollIntoView({block:'start'})}return 1",3)
    t=J("return document.body.innerText"); i=t.find('대한민국'); kr=t[i:i+30].replace('\n',' '); print("KR",kr)
    if f"{it['price']:,}" not in kr: print("RESULT: PRICE_FAIL",key); return 2
    J("const b=[...document.querySelectorAll('button')].find(x=>x.getClientRects().length&&x.innerText.trim()=='활성화');b.click();return 1",9)
    u=J("return location.href"); t=J("return document.body.innerText")
    ok="/sku/" in u and "활성" in t and "저장할 수 없" not in t
    print("RESULT:", "ACTIVATED" if ok else "FAIL", key, u)
    return 0 if ok else 1
items=json.load(open(a.items))
keys=a.only.split(",") if a.only else list(items)
if not a.submit:
    for k in keys: print(a.prefix+k, items[k]); 
    print("RESULT: DRY_RUN", len(keys)); sys.exit(0)
T=c.new_tab(BASE+"one-time-products","Profile 1"); time.sleep(10)
bad=0
try:
    for k in keys: bad+= one(k,items[k])!=0
finally:
    if not a.keep_tab: c.close_tab(T)
sys.exit(1 if bad else 0)
