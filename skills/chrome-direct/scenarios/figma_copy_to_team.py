"""usage: figma_copy_to_team.py <file_key> [--folder <folder_id>] [--profile "Profile 1"]
피그마 파일을 내 팀 프로젝트로 복사한다(보기 권한만 있어도 됨). 새 file key 를 출력한다.
왜: Figma MCP 호출 한도는 파일이 든 팀의 플랜을 따른다. 남의 Starter 팀 파일은 월 6회라,
    내 유료/학생 팀(Full 좌석)으로 복사한 사본을 MCP로 읽는다. 공식 API에 복사가 없어 로그인 탭 안에서 내부 API를 부른다.
사전 조건: 크롬 프로필이 MCP와 같은 Figma 계정으로 로그인돼 있을 것. 노드 id 는 사본에서 바뀐다.
--folder 생략 시 내 첫 팀의 첫 프로젝트. 같은 이름 '(복사)'가 이미 그 폴더에 있으면 새로 만들지 않는다.
"""
import sys, os, time, json, argparse
sys.path.insert(0, os.path.expanduser('~/.claude/skills/chrome-direct')); import chromectl as c

ap = argparse.ArgumentParser(); ap.add_argument('key'); ap.add_argument('--folder'); ap.add_argument('--profile', default='Profile 1')
a = ap.parse_args()
t = c.new_tab('https://www.figma.com/files/recents-and-sharing', profile=a.profile)
def call(js, wait=4):
    c.run_js(t, "window.__fx=null;(async()=>{try{" + js + "}catch(e){window.__fx=JSON.stringify({err:''+e})}})();'ok'")
    for _ in range(40):
        time.sleep(wait / 4); r = c.run_js(t, "window.__fx")
        if r and r != 'missing value': return json.loads(r)
    return {'err': 'timeout'}
try:
    time.sleep(6)
    J = "const g=async u=>{const r=await fetch(u,{credentials:'include'});return r.json()};"
    folder = a.folder
    if not folder:
        st = call(J + "window.__fx=JSON.stringify(await g('/api/user/state'))")
        team = st['meta']['team_users'][0]['team_id']
        fo = call(J + f"window.__fx=JSON.stringify(await g('/api/teams/{team}/folders'))")
        folder = fo['meta']['folder_rows'][0]['id']
    src = call(J + f"window.__fx=JSON.stringify(await g('/api/files/{a.key}/meta'))")['meta']['name']
    fl = call(J + f"window.__fx=JSON.stringify(await g('/api/folders/{folder}/paginated_files?sort_column=touched_at&sort_order=desc&page_size=100'))")
    files = json.dumps(fl, ensure_ascii=False)
    import re
    hit = re.search(r'"key":\s*"(\w+)"[^{}]*?"name":\s*"' + re.escape(src + ' (복사)') + '"', files)
    if hit:
        print(json.dumps({'key': hit.group(1), 'folder': folder, 'exists': True}, ensure_ascii=False)); print('RESULT: EXISTS', hit.group(1)); sys.exit(0)
    r = call(f"const r=await fetch('/api/multiplayer/{a.key}/copy?folder_id={folder}',{{method:'POST',credentials:'include',headers:{{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest','X-Csrf-Bypass':'yes'}}}});window.__fx=JSON.stringify(await r.json())", wait=20)
    m = r.get('meta') or {}
    print(json.dumps({'key': m.get('key'), 'name': m.get('name'), 'team': m.get('team_id'), 'folder': m.get('folder_id')}, ensure_ascii=False))
    print('RESULT:', 'OK ' + m['key'] if m.get('key') else 'FAIL ' + json.dumps(r)[:200])
    sys.exit(0 if m.get('key') else 1)
finally:
    try: c.close_tab(t)
    except Exception: pass
