"""DAKER ELO 상호평가 투표 (LLM 없음, 판정은 호출자가 PDF 텍스트를 읽고 내림).
선행: 실제 Chrome Profile 1에서 dacon.io 로그인(구글) → DAKER 로그인(SSO) → arena 페이지 열고 NDA 동의.
  DAKER_SID=<stage id> DAKER_TAB=id:<tab>  CAP=2000 python3 daker_elo_vote.py next   # 대결 받아 두 PDF 텍스트 출력(이미지 PDF는 OCR)
  python3 daker_elo_vote.py vote a|b "이유"   # 투표, ELO_DIR/votes.log에 기록
  python3 daker_elo_vote.py stats              # myMatches·minMatchReached
OCR 바이너리: ELO_DIR/ocr (scenarios/daker_elo_ocr.swift를 swiftc로 컴파일). 2026-11-18 KIC 공모전에서 20회 투표에 사용.
2026-11-24 제주 AI Agent 챌린지 김은미(Profile 16) 12회: DAKER_TAB=id:<Profile 16 탭>. 구글 계정 선택·비밀번호 '다음'은 합성 클릭이 안 먹어
chromectl.rclick으로 누름, 2단계는 폰 '예'(사람 몫). 경기장 첫 진입 시 NDA 체크박스([role=checkbox])도 rclick. 완료 화면 숫자는 0부터 올라가는 애니메이션이라 stats로 확인.
"""
import sys,os,time,json,base64,subprocess,re
sys.path.insert(0, os.path.expanduser('~/.claude/skills/chrome-direct')); import chromectl as c
T=os.environ.get('DAKER_TAB','daker.ai'); SID=os.environ['DAKER_SID']  # ELO stage id (URL .../arena/<SID>)
D=os.environ.get('ELO_DIR',os.path.expanduser('~/.cache/daker-elo')); os.makedirs(D,exist_ok=True); ST=os.path.join(D,'state.json'); CAP=int(os.environ.get('CAP','3800'))
def api(method,path,body=None,wait=4):
    c.js_json(T,"window.__r=null; fetch(%s,{method:%s,credentials:'include',headers:{'Content-Type':'application/json'},body:%s}).then(async r=>window.__r=r.status+'\\n'+await r.text()).catch(e=>window.__r='ERR '+e); return 1"%(json.dumps(path),json.dumps(method),json.dumps(json.dumps(body)) if body else 'undefined'))
    for _ in range(30):
        time.sleep(0.5); r=c.js_json(T,"return window.__r")
        if r: return r
def pdf(url,out):
    c.js_json(T,"window.__p=null; fetch(%s).then(r=>r.arrayBuffer()).then(b=>{let s='';const u=new Uint8Array(b);for(let i=0;i<u.length;i+=32768)s+=String.fromCharCode.apply(null,u.subarray(i,i+32768));window.__p=btoa(s)}).catch(e=>window.__p='ERR'); return 1"%json.dumps(url))
    for _ in range(60):
        time.sleep(0.5); p=c.js_json(T,"return window.__p",timeout=60)
        if p: break
    open(out,'wb').write(base64.b64decode(p))
    txt=subprocess.run(['pdftotext','-layout',out,'-'],capture_output=True,text=True).stdout
    if len(txt.strip())<200:
        pd=out[:-4]+'-pg'; os.makedirs(pd,exist_ok=True); subprocess.run(['pdftoppm','-r','110','-png',out,pd+'/p']); txt=subprocess.run([os.path.join(D,'ocr')]+sorted(os.path.join(pd,f) for f in os.listdir(pd)),capture_output=True,text=True).stdout; txt='[OCR] '+txt
    pages=txt.split('\f'); txt=re.sub(r'[ \t]+',' ',txt); txt=re.sub(r'\n\s*\n+','\n',txt)
    return len([p for p in pages if p.strip()]), txt
cmd=sys.argv[1]
if cmd=='next':
    r=api('GET','/api/hackathons/stages/%s/elo/matchup'%SID); st,body=r.split('\n',1); j=json.loads(body)
    a,b=j['submissionA'],j['submissionB']; json.dump({'a':a['id'],'b':b['id'],'ta':a['title'],'tb':b['title']},open(ST,'w'),ensure_ascii=False)
    for k,s in (('A',a),('B',b)):
        n,txt=pdf(s['pdfUrl'],os.path.join(D,'%s-%s.pdf'%(k,s['id'][:8])))
        open(os.path.join(D,'%s-%s.txt'%(k,s['id'][:8])),'w').write(txt)
        print('==== %s: %s | %d쪽 텍스트 %d자'%(k,s['title'],n,len(txt)))
        print(txt[:CAP])
elif cmd=='vote':
    s=json.load(open(ST)); w=sys.argv[2]
    r=api('POST','/api/hackathons/stages/%s/elo/vote'%SID,{'submissionAId':s['a'],'submissionBId':s['b'],'winner':w})
    print(r[:300])
    with open(os.path.join(D,'votes.log'),'a') as f: f.write(json.dumps({**s,'winner':w,'why':sys.argv[3] if len(sys.argv)>3 else '','resp':r[:200]},ensure_ascii=False)+'\n')
elif cmd=='stats':
    print(api('GET','/api/hackathons/stages/%s/elo/stats'%SID))
