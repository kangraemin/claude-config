#!/usr/bin/env python3
"""AI Hub(aihub.or.kr) 데이터셋: 파일 목록 보기·일부 파일만 API로 받기(브라우저·LLM 없음).
전제: remin1994 AI Hub 가입(11/29), 데이터셋 상세에서 '다운로드' 눌러 승인(경진대회 목적이면 즉시 승인), API 키는 ~/.claude/.env AIHUB_APIKEY.
키 새로 받기: 로그인 뒤 https://www.aihub.or.kr/devsport/apishell/list.do 'API key 발급' → 메일(gmail_search.py "aihub")로 옴.
  python3 aihub_data.py tree 71407 [--grep VS_]
  python3 aihub_data.py get 71407 --keys 487946,487937 --out <빈 폴더>   # 분할(.partN) 합쳐 zip 풀기
주의: 이용정책상 국외 반출(해외 서버·Kaggle 학습) 금지, 재배포 금지.
"""
import argparse, collections, io, os, subprocess, sys, tarfile, zipfile
def key():
    for l in open(os.path.expanduser('~/.claude/.env')):
        if l.startswith('AIHUB_APIKEY='): return l.strip().split('=', 1)[1]
    sys.exit('AIHUB_APIKEY 없음')
ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
t = sp.add_parser('tree'); t.add_argument('dsn'); t.add_argument('--grep', default='')
g = sp.add_parser('get'); g.add_argument('dsn'); g.add_argument('--keys', required=True); g.add_argument('--out', required=True)
a = ap.parse_args()
if a.cmd == 'tree':
    out = subprocess.run(['curl', '-sS', f'https://api.aihub.or.kr/info/{a.dsn}.do'], capture_output=True, text=True).stdout
    print('\n'.join(l for l in out.splitlines() if a.grep in l)); sys.exit(0)
os.makedirs(a.out, exist_ok=True); tp = os.path.join(a.out, '_dl.tar')
r = subprocess.run(['curl', '-sS', '-L', '-o', tp, '-H', 'apikey:' + key(), '-w', '%{http_code}', f'https://api.aihub.or.kr/down/0.6/{a.dsn}.do?fileSn={a.keys}'], capture_output=True, text=True)
if r.stdout.strip() != '200': print('RESULT: FAIL http', r.stdout, open(tp, errors='replace').read()[:300]); sys.exit(1)
tf = tarfile.open(tp); parts = collections.defaultdict(list)
for m in tf.getmembers():
    if m.isfile(): b, _, n = m.name.rpartition('.part'); parts[b].append((int(n), m))
for b, lst in parts.items():
    z = zipfile.ZipFile(io.BytesIO(b''.join(tf.extractfile(m).read() for _, m in sorted(lst, key=lambda x: x[0]))))
    d = os.path.join(a.out, os.path.basename(b)[:-4]); z.extractall(d); print(os.path.basename(d), len(z.namelist()))
tf.close(); os.remove(tp); print('RESULT: OK', len(parts), 'files')
