"""크몽 판매자 세팅 헬퍼 (2026-10-23 실제로 돈 순서).
순서: 이메일 가입(seller) → signup-seller 휴대폰 인증(pass_sms_verify.py --match teledit, 다날 보안문자 img#captcha 5자리)
→ 약관 체크 + "전문가 등록 완료" → 프로필(소개 textarea·전문분야 react-select·보유기술 label 체크)
→ /my_profile/seller/certifications 사업자 인증(biz) → 승인 후 /my-gigs/new.
주의: react-select 상세분야는 전문분야를 다시 고른 뒤에야 메뉴가 열린다. 파일 업로드 뒤 input이 다시 그려지므로 두 번째 파일은 index 0으로 올린다.
사용: python3 kmong_seller.py biz   (개인정보.md에서 값을 읽어 채우고 값은 출력 안 함; 통장사본·사업자등록증 경로는 아래 상수)
"""
import sys,time,json,re,os
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))))
import chromectl as c
T='kmong.com'
def js(code): return c.run_js(T,'(()=>{try{'+code+'}catch(e){return "ERR "+e}})()')
def btn(text):
    return js('const b=[...document.querySelectorAll("button,a")].find(b=>b.innerText.trim()==%s);if(!b)return "NF";b.click();return "ok"'%json.dumps(text))
def dialog():
    return js('const d=[...document.querySelectorAll("[role=dialog]")].pop();if(!d)return "NODIALOG";return d.innerText.slice(0,1500)+" INPUTS:"+[...d.querySelectorAll("input,textarea,select")].map(e=>e.tagName+"/"+e.type+"/"+(e.name||e.id)+"/"+(e.placeholder||"")+"/max"+e.maxLength).join(" ;; ")')
def setv(sel, val, scope='document'):
    return js('const e=%s.querySelector(%s);if(!e)return "NF";const p=Object.getPrototypeOf(e);Object.getOwnPropertyDescriptor(p,"value").set.call(e,%s);e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}));return "ok "+e.value.length'%(scope,json.dumps(sel),json.dumps(val)))
D='[...document.querySelectorAll("[role=dialog]")].pop()'
def rs_open(i):
    return js('const inp=document.getElementById("react-select-%d-input");const ctl=inp.closest("[class*=control]")||inp.parentElement.parentElement.parentElement;ctl.dispatchEvent(new MouseEvent("mousedown",{bubbles:true}));inp.focus();return "ok"'%i)
def rs_opts():
    return js('return [...document.querySelectorAll("[id*=-option-]")].map(o=>o.id+"="+o.innerText).join(" | ")')
def rs_pick(text):
    return js('const o=[...document.querySelectorAll("[id*=-option-]")].find(o=>o.innerText.trim()==%s);if(!o)return "NF";o.click();return "ok"'%json.dumps(text))
def upload(idx, path, mime):
    import base64,os
    b=base64.b64encode(open(os.path.expanduser(path),'rb').read()).decode()
    name=os.path.basename(path)
    return js('const f=[...document.querySelectorAll("input[type=file]")][%d];const bin=atob(%s);const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);const dt=new DataTransfer();dt.items.add(new File([u],%s,{type:%s}));f.files=dt.files;f.dispatchEvent(new Event("change",{bubbles:true}));return "ok "+f.files.length'%(idx,json.dumps(b),json.dumps(name),json.dumps(mime)))

def biz():
    P=open(os.path.expanduser('~/Documents/oguri-works/개인정보.md')).read()
    def g(k):
        m=re.search(r'^- '+re.escape(k)+r':\s*(.+)$',P,re.M); return m.group(1).strip() if m else ''
    name=re.sub(r'[*`(].*','',g('이름')).strip()
    shop=re.sub(r'[*`(].*','',g('상호')).strip()
    bizno=re.sub(r'\D','',re.search(r'[\d-]{10,12}',g('사업자번호')).group(0))
    addr=re.sub(r'\s*\(.*','',g('사업장')).strip()
    phone=re.sub(r'\D','',re.search(r'[\d-]{10,13}',g('휴대폰')).group(0))
    email=re.search(r'[\w.+-]+@[\w.-]+',g('이메일')).group(0)
    vals={'company_name':shop,'company_number':bizno,'representative_name':name,'company_type':'정보통신업','company_kind':'응용 소프트웨어 개발 및 공급업','company_address':addr,'company_email':email,'company_contact_username':name,'company_contact_number':phone,'company_depositor':name}
    for k,v in vals.items():
        r=setv('input[name=%s]'%k,v); print(k,'len',len(v),r.split(' ')[0])
    m=re.match(r'[^()]*\([^)]*\)',re.search(r'^- 사업장:\s*(.+)$',P,re.M).group(1)); vals['company_address']=m.group(0).strip() if m else vals['company_address']
    vals['company_name']=shop.split('/')[0].strip()
    for k,v in vals.items(): print(k,'len',len(v),str(setv('input[name=%s]'%k,v)).split(' ')[0])
    print(upload(0,'~/Downloads/oguri-biz/사업자등록증.pdf','application/pdf')); time.sleep(3)
    print(upload(0,'~/Downloads/oguri-biz/통장사본.jpg','image/jpeg'))
    print('은행 선택·계좌번호는 통장사본을 보고 넣은 뒤 btn("저장")')

if __name__=='__main__' and sys.argv[1:]==['biz']:
    biz()
