import json,re,os,sys
d=json.load(open(sys.argv[1]));OUT=sys.argv[2];P=d['pages']
def slug(s): return re.sub(r'[\\/:*?"<>|]','',s).replace(' ','-').strip('-')[:60]
img_of={}  # img id -> rel path from OUT
path={}    # page idx -> rel md path
parts=P[0]['children']
for pi,pidx in enumerate(parts,1):
    pd=f"part{pi}"
    path[pidx]=f"{pd}/README.md"
    for li,c in enumerate(P[pidx]['children'],1):
        path[c]=f"{pd}/{li:02d}-{slug(re.sub(r'^\d+\.\s*','',P[c]['title']))}.md"
path[0]="INDEX.md"
def summary(p):
    m=re.search(r'## 한 문장으로\n+(.+)','\n'.join(p['lines']));return m.group(1).strip().replace('**','') if m else ''
for idx,rel in path.items():
    p=P[idx];folder=os.path.dirname(rel);n=0;lines=[]
    for ln in p['lines']:
        def pg(m):
            c=int(m.group(1));r=os.path.relpath(path[c],folder or '.');return f"[{P[c]['title']}]({r})"
        ln=re.sub(r'\{\{PAGE:(\d+)\}\}',pg,ln)
        def im(m):
            global n
            iid=m.group(1);rel_img=f"{folder}/img/{os.path.splitext(rel)[0].split('/')[-1][:2]}-{len(img_of)}.jpg"
            img_of[iid]=rel_img;return os.path.relpath(rel_img,folder or '.')
        ln=re.sub(r'IMG:([0-9a-f-]+)',im,ln)
        lines.append(ln)
    if idx!=0:
        head=f"# {p['title']}\n\n"
        os.makedirs(os.path.join(OUT,folder),exist_ok=True)
        open(os.path.join(OUT,rel),'w').write(head+'\n'.join(lines).strip()+'\n')
# INDEX
out=["# 🎨 카카오 이모티콘 만들기 — 강의 정리 (목차)","",*P[0]['lines'][:5],"",
"사용법","- 이 목차에서 주제를 찾고, 해당 강의 파일만 연다.","- 이미지는 각 파트의 `img/` 폴더에 있다. 본문에서 필요한 장면만 연다.","- `grep -rn 키워드 lecture/` 로 본문 검색.",""]
for pi,pidx in enumerate(parts,1):
    out.append(f"## {P[pidx]['title']}  → `{path[pidx]}`")
    for c in P[pidx]['children']:
        ni=sum(ln.count('IMG:') for ln in P[c]['lines'])
        out.append(f"- [{P[c]['title']}]({path[c]}) — {summary(P[c])} _(이미지 {ni})_")
    out.append("")
open(os.path.join(OUT,'INDEX.md'),'w').write('\n'.join(out))
json.dump(img_of,open(os.path.join(sys.argv[3]),'w'),ensure_ascii=False)
print(len(path),'md',len(img_of),'imgs')
