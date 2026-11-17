#!/usr/bin/env python3
# CLAUDE_P_MAX=0 (모델 호출 없음)
"""[제출] 대전사회혁신센터(commonz042.kr) 공모사업 신청 — python requests(OpenSSL)판.
사용: commonz042_apply.py <program_wr> <file1> <file2> [--submit] [--who kim]
- 11/17: macOS curl(LibreSSL)은 write_update.php 업로드가 'SSL bad record mac'으로 끊김(11/09와 같음).
  같은 요청을 python requests(OpenSSL 3)로 보내니 한 번에 '신청이 완료되었습니다.' + lookup exists:true(wr_id=746).
  → 업로드는 이 스크립트를 먼저 쓴다. 끊겨도 글이 안 생겼는지 client_apply wr_id를 훑어 확인한 뒤 다시.
- 기본은 강래민(DJSI_ID/DJSI_PW, 개인정보.md), --who kim 이면 김은미(DJSI_ID_KIM/DJSI_PW_KIM, 개인정보-김은미.md).
- 확인: WHO=kim commonz042_verify_sent.py <wr_id> <out_dir> <sent_dir>
"""
import requests,re,os,html,time,sys,subprocess,shlex,json
env={}
for l in open(os.path.expanduser('~/.claude/.env')):
    if '=' in l and not l.startswith('#'): k,v=l.strip().split('=',1); env[k]=v.strip('"\'')
KIM='--who' in sys.argv and sys.argv[sys.argv.index('--who')+1]=='kim'
SFX='_KIM' if KIM else ''
info={}
for k,v in re.findall(r'^(\w+)=(.*)$', subprocess.run(['python3',os.path.expanduser('~/.claude/skills/chrome-direct/scenarios/commonz042_info.py'),os.path.expanduser('~/Documents/oguri-works/개인정보-김은미.md' if KIM else '~/Documents/oguri-works/개인정보.md')],capture_output=True,text=True).stdout, re.M):
    info[k]=shlex.split(v)[0] if v else ''
WR=sys.argv[1]; F1,F2=sys.argv[2],sys.argv[3]; SUBMIT='--submit' in sys.argv
B='https://www.commonz042.kr/bbs'; s=requests.Session(); s.headers['User-Agent']='Mozilla/5.0 (Macintosh) Chrome/131'
s.get(B+'/login.php'); s.post(B+'/login_check.php',data={'mb_id':env['DJSI_ID'+SFX],'mb_password':env['DJSI_PW'+SFX],'url':'/'})
def lookup(): return s.post(B+'/client_apply_lookup.php',data={'org_name':info['NM'],'tel':info['PH'],'program_bo':'public_apply','program_wr':WR}).text
print('lookup before:',lookup())
if not SUBMIT: sys.exit()
if '"exists":true' in lookup(): print('RESULT: ALREADY_APPLIED'); sys.exit()
wu=f'{B}/write.php?bo_table=client_apply&program_bo=public_apply&program_wr={WR}'
W=s.get(wu).text
def fld(n):
    m=re.search(r'name="%s"[^>]*value="([^"]*)"'%n,W); return html.unescape(m.group(1)) if m else ''
uid=fld('uid'); tok=s.post(B+'/write_token.php',data={'bo_table':'client_apply'}).json()['token']
data={'token':tok,'uid':uid,'w':'','bo_table':'client_apply','wr_id':'0','wr_content':'client_apply','ca_prog_bo':'public_apply','ca_prog_wr':WR,
 'wr_subject':fld('wr_subject'),'bai_1':fld('bai_1'),'bai_2':fld('bai_2'),'bai_3':fld('bai_3'),'wr_name':info['NM'],'wr_extra':'개인','wr_address':info['AG'],
 'channel':'대전사회혁신센터 공식 홈페이지','tel':info['PH'],'sex':info['SX'],'wr_email':info['EM'],'bf_content[0]':'','bf_content[1]':''}
files=[('bf_file[0]',(os.path.basename(F1),open(F1,'rb'),'application/pdf')),('bf_file[1]',(os.path.basename(F2),open(F2,'rb'),'application/zip'))]
try:
    r=s.post(B+'/write_update.php',data=data,files=files,headers={'Referer':wu},timeout=180)
    print('HTTP',r.status_code, re.findall(r'alert\("([^"]*)"\)',r.text)[:2], r.url)
    open(os.path.join(os.environ.get('OUT','/tmp'),'commonz_wu.html'),'w').write(r.text)
except Exception as e: print('ERR',type(e).__name__,str(e)[:200])
time.sleep(2); R=lookup(); print('lookup after:',R)
print('RESULT: OK' if '"exists":true' in R else 'RESULT: FAILED')
