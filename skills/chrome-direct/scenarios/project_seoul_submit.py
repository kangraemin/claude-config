#!/usr/bin/env python3
"""프로젝트 서울(project.seoul.go.kr) 공모전 작품접수 — 업로드·작품설명·임시저장/제출·서버 해시 대조·증거 캡처.

사용:
  project_seoul_submit.py --cptt 737 --regist 41795 --slot FLT2101=panel.jpg --slot FLT1001=main.jpg \
      --slot FLT2002=img_01.jpg,img_02.jpg --slot FLT1002=PIN_document.zip --desc desc.txt --proof-dir DIR [--submit]
  project_seoul_submit.py --cptt 737 --regist 41795 --status        # 접수 상태·서버 첨부 해시만
기본은 업로드 + 임시저장까지(dry-run). --submit 일 때만 '제출'(제출 후 수정 불가)을 한 번 누른다.

사전 조건: 회원가입·참가등록(PIN)이 끝나 있어야 한다(registMstSeq는 '작품접수하기' onclick fnViewInsertSubmission(<n>)의 n).
  ~/.claude/.env PROJECT_SEOUL_EMAIL / PROJECT_SEOUL_PASSWORD. Chrome Profile 1.
왜 화면 조작: 공개 API 없음. 업로드 위젯 DEXTUploadX5(EXNJ)는 숨은 input이 없어 일반 upload_file이 안 된다.
  → 업로드 팝업 iframe(#ifr_popup iframe, same-origin)에 base64 조각을 textarea로 넣고, iframe에 <script>를 꽂아
    main world에서 File→DataTransfer→dx5.get('dext5').addFileList(dt.files) 후 '파일 전송'(transfer()) 클릭.
  (AppleScript execute는 isolated world라 dx5·fn* 페이지 전역을 못 부른다 — 링크 click이나 <script> 주입으로 우회)
멱등: 이미 '작품접수 완료'면 아무것도 올리지 않고 상태만 출력(RESULT: ALREADY_SUBMITTED). 같은 슬롯에 같은 이름이 서버에 있으면 그 파일은 건너뛴다.
2026-11-08 용산 AI 스마트도시(cptt 737) 제출에서 같은 순서로 성공.
"""
import argparse, base64, hashlib, json, os, re, sys, time
sys.path.insert(0, os.path.expanduser('~/.claude/skills/chrome-direct'))
import chromectl as c

BASE = 'https://project.seoul.go.kr'


def env(k):
    for line in open(os.path.expanduser('~/.claude/.env'), encoding='utf-8'):
        m = re.match(rf"^{k}=['\"]?(.*?)['\"]?\s*$", line)
        if m:
            return m.group(1)
    raise SystemExit(f'RESULT: BLOCKED no {k} in ~/.claude/.env')


def J(t, body, to=60):
    return c.js_json(t, body, to)


def main_world(t, code, doc="document", to=60):
    """페이지(main world)에서 code(함수 본문, return 값 JSON)를 돌려 결과를 받는다."""
    s = "(function(){try{document.body.dataset.mw=JSON.stringify((function(){" + code + "})());}catch(e){document.body.dataset.mw=JSON.stringify('ERR '+e)}})();"
    r = J(t, f"const d={doc}; delete d.body.dataset.mw; const s=d.createElement('script'); s.textContent={json.dumps(s)}; d.body.appendChild(s); return d.body.dataset.mw", to)
    return json.loads(r) if r else None


def main_world_async(t, code, wait=180):
    """code는 async 본문, 끝에 결과를 return. 결과는 dataset으로 폴링."""
    s = "(function(){document.body.dataset.mwa='run';(async()=>{" + code + "})().then(r=>document.body.dataset.mwa=JSON.stringify(r)).catch(e=>document.body.dataset.mwa=JSON.stringify('ERR '+e));})();"
    J(t, f"const s=document.createElement('script'); s.textContent={json.dumps(s)}; document.body.appendChild(s); return 1")
    for _ in range(wait // 3):
        time.sleep(3)
        r = J(t, "return document.body.dataset.mwa")
        if r != 'run':
            return json.loads(r)
    return 'TIMEOUT'


def click_onclick(t, sub, scope='document'):
    return J(t, f"const a=[...{scope}.querySelectorAll('a,button')].find(a=>(a.getAttribute('onclick')||'').includes({json.dumps(sub)})); if(!a) return 'none'; a.click(); return 'ok'")


def jconfirm(t):
    return J(t, "return [...document.querySelectorAll('.jconfirm')].map(j=>j.innerText.replace(/\\s+/g,' ').slice(0,200))") or []


def ok_jconfirm(t):
    J(t, "const b=[...document.querySelectorAll('.jconfirm button')].find(b=>b.textContent.trim()=='OK'); if(b) b.click(); return 1")


def login(t, cptt):
    J(t, f"location.href='{BASE}/view/viewDetailCptt.do?cpttMstSeq={cptt}'; return 1"); time.sleep(5)
    if J(t, "return !![...document.querySelectorAll('a')].find(a=>a.textContent.trim()=='로그아웃')"):
        return True
    click_onclick(t, 'fnViewLogin()'); time.sleep(3)
    code = """const vs=[...document.querySelectorAll('input')].filter(i=>i.offsetParent);
const em=vs.find(i=>i.type==='text'||i.type==='email'), p=vs.find(i=>i.type==='password');
const S=(e,v)=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,v);e.dispatchEvent(new Event('input',{bubbles:true}));};
S(em,%s);S(p,%s);
const b=[...document.querySelectorAll('a,button')].filter(x=>x.offsetParent&&x.innerText.trim()==='로그인').pop(); b.click(); return 1""" % (
        json.dumps(env('PROJECT_SEOUL_EMAIL')), json.dumps(env('PROJECT_SEOUL_PASSWORD')))
    J(t, code); time.sleep(6)
    J(t, f"location.href='{BASE}/view/viewDetailCptt.do?cpttMstSeq={cptt}'; return 1"); time.sleep(5)
    return bool(J(t, "return !![...document.querySelectorAll('a')].find(a=>a.textContent.trim()=='로그아웃')"))


def page_state(t):
    return J(t, "const t=document.body.innerText; const m=t.match(/작품접수\\s*(\\d+)\\s*건/); return {count:m&&+m[1], done:!![...document.querySelectorAll('a')].find(a=>a.textContent.trim()=='작품접수 완료'), open:!![...document.querySelectorAll('a')].find(a=>a.textContent.trim()=='작품접수하기')}")


def server_files(t, regist):
    code = """const types=['FLT2101','FLT1001','FLT2002','FLT1002','FLT2201']; const out=[];
const lst=ty=>new Promise((res,rej)=>$.ajax({type:'POST',url:'/view/getAttachFileList.json',dataType:'json',contentType:'application/json; charset=UTF-8',data:JSON.stringify({mappingSeq:'%s',fileTypeCd:ty}),success:res,error:(r,s)=>rej(s+' '+r.status)}));
for(const ty of types){const j=await lst(ty); const vs=(j&&j.attachFileListVO&&j.attachFileListVO.attachFileVOs)||[];
 for(const v of vs){const b=await (await fetch('/downloadFile.do?fileSeq='+v.fileSeq+'&orgSizeYn=Y',{credentials:'include'})).arrayBuffer();
  const h=[...new Uint8Array(await crypto.subtle.digest('SHA-256',b))].map(x=>x.toString(16).padStart(2,'0')).join('');
  out.push({t:ty,seq:v.fileSeq,name:v.orgFileNm,size:b.byteLength,h});}} return out;""" % regist
    return main_world_async(t, code, 300)


def open_modal(t, regist):
    click_onclick(t, f'fnViewInsertSubmission({regist})'); time.sleep(4)
    J(t, "const a=[...document.querySelectorAll('.modal-footer a')].find(a=>a.textContent=='다음'); if(a) a.click(); return 1"); time.sleep(3)
    return J(t, "return !!document.querySelector('#insertModal.in')")


IF = "const f=document.querySelector('#ifr_popup iframe'); const d=f&&f.contentDocument;"


def upload_slot(t, code, paths):
    if click_onclick(t, f"'{code}'", "document.getElementById('insertModal')") != 'ok':
        return f'{code}: no link'
    for _ in range(15):
        time.sleep(2)
        if J(t, IF + f"return !!(f&&f.src.includes('{code}')&&d&&d.getElementById('btn-upload-auto'))"):
            break
    else:
        return f'{code}: popup not ready'
    time.sleep(2)
    for p in paths:
        b = base64.b64encode(open(p, 'rb').read()).decode()
        J(t, IF + f"const ta=d.createElement('textarea'); ta.className='__chunkset'; ta.dataset.name={json.dumps(os.path.basename(p))}; ta.style.display='none'; d.body.appendChild(ta); return 1")
        for i in range(0, len(b), 400000):
            J(t, IF + f"const tas=d.querySelectorAll('textarea.__chunkset'); tas[tas.length-1].value += {json.dumps(b[i:i+400000])}; return 1", 90)
    add = """const tas=[...document.querySelectorAll('textarea.__chunkset')]; const dt=new DataTransfer();
for(const ta of tas){const s=atob(ta.value); const u=new Uint8Array(s.length); for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);
 const n=ta.dataset.name; dt.items.add(new File([u], n, {type: n.endsWith('.zip')?'application/zip':(n.endsWith('.png')?'image/png':(n.endsWith('.pdf')?'application/pdf':'image/jpeg'))})); ta.remove();}
const dx=dx5.get('dext5'); dx.addFileList(dt.files); return dx.getTotalItemCount();"""
    n = main_world(t, add, "document.querySelector('#ifr_popup iframe').contentDocument", 120)
    if n != len(paths):
        return f'{code}: added {n} != {len(paths)}'
    J(t, IF + "d.getElementById('btn-upload-auto').click(); return 1")
    for _ in range(100):
        time.sleep(3)
        if not J(t, "return !!document.querySelector('#ifr_popup.in')"):
            al = [x for x in jconfirm(t)]
            return f'{code}: uploaded {n}' + (f' alert={al}' if al else '')
    return f'{code}: upload timeout'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cptt', required=True); ap.add_argument('--regist', required=True)
    ap.add_argument('--slot', action='append', default=[], help='FLTxxxx=file1,file2')
    ap.add_argument('--desc'); ap.add_argument('--proof-dir'); ap.add_argument('--status', action='store_true')
    ap.add_argument('--submit', action='store_true')
    a = ap.parse_args()
    t = c.new_tab(f'{BASE}/view/viewDetailCptt.do?cpttMstSeq={a.cptt}', profile='Profile 1')
    try:
        if not login(t, a.cptt):
            print('RESULT: BLOCKED login failed'); return
        st = page_state(t); print('state', st)
        if a.status or st.get('done'):
            print(json.dumps(server_files(t, a.regist), ensure_ascii=False))
            print('RESULT: ALREADY_SUBMITTED' if st.get('done') else 'RESULT: STATUS'); return
        if not open_modal(t, a.regist):
            print('RESULT: BLOCKED modal not open'); return
        have = {f['name'] for f in (server_files(t, a.regist) or []) if isinstance(f, dict)}
        for s in a.slot:
            code, files = s.split('=', 1)
            paths = [p for p in files.split(',') if os.path.basename(p) not in have]
            print(upload_slot(t, code, paths) if paths else f'{code}: already on server')
        if a.desc:
            txt = open(a.desc, encoding='utf-8').read().strip()
            J(t, f"const ta=document.querySelector('#insertModal textarea'); ta.value={json.dumps(txt)}; ['input','keyup','change'].forEach(e=>ta.dispatchEvent(new Event(e,{{bubbles:true}}))); return 1")
        print('modal files', J(t, "return [...document.querySelectorAll('#insertModal [id$=_ul] li')].map(l=>l.textContent.trim())"))
        click_onclick(t, 'fnSubmitClick' if a.submit else 'fnTempClick', 'document.querySelector(".modal-footer")'); time.sleep(4)
        print('confirm', jconfirm(t)); ok_jconfirm(t); time.sleep(8)
        res = jconfirm(t); print('result', res)
        if a.proof_dir:
            os.makedirs(a.proof_dir, exist_ok=True); c.shot(t, os.path.join(a.proof_dir, '01_alert.png'))
        ok_jconfirm(t)
        J(t, f"location.href='{BASE}/view/viewDetailCptt.do?cpttMstSeq={a.cptt}'; return 1"); time.sleep(6)
        st2 = page_state(t); print('state after', st2)
        if a.proof_dir:
            c.shot(t, os.path.join(a.proof_dir, '02_detail.png'))
        sf = server_files(t, a.regist); print(json.dumps(sf, ensure_ascii=False))
        if a.submit:
            print('RESULT: SUBMITTED' if st2.get('done') else 'RESULT: UNCERTAIN — 다시 누르지 말고 내 프로젝트·메일 확인')
        else:
            print('RESULT: SAVED_DRAFT' if any('저장' in x for x in res) else 'RESULT: UNCERTAIN')
    finally:
        c.close_tab(t)


if __name__ == '__main__':
    main()
