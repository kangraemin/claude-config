#!/usr/bin/env python3
"""GA 아침 리포트를 웹 한 장으로 만든다(사용자 11/10 "캘린더처럼 별개의 웹으로", "좀 보기 편하게 제발").

사용: python3 build.py [--out DIR]
- 읽는 것: ~/.cache/ga-daily/<날짜>.txt(ga_daily_report.py가 쓰는 텔레그램 본문), live.txt·live.json(갱신 버튼 판).
- 하루 = 0시~다음 날 0시. 아침 리포트는 어제 하루치, '지금' 판은 오늘 0시~갱신 누른 시각.
- 쓰는 것: DIR/index.html, DIR/live.json. 배포는 sync.sh.
"""
import argparse
import datetime as dt
import html
import json
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ga_daily_report as G  # short()·channel(): 리포트와 같은 이름·같은 길 구분

SRC = Path.home() / '.cache/ga-daily'
TAIL = {'전부 0인 곳', '참고', '거의 안 들어온 곳'}


def parse(text):
    """본문을 {title, top:[{t,items}], svcs:[{name, blocks:[{t,items}]}], tail:[{t,items}]}로."""
    L = text.split('\n')
    doc = {'title': L[0].strip(), 'top': [], 'svcs': [], 'tail': []}
    cur, where = None, 'top'
    for l in L[1:]:
        s = l.rstrip()
        if not s:
            continue
        if s.startswith('[') and s.endswith(']'):
            where = 'svc'
            doc['svcs'].append({'name': s[1:-1], 'blocks': []})
            cur = None
        elif s.startswith('- '):
            if cur is None:
                cur = {'t': '', 'items': []}
                (doc['svcs'][-1]['blocks'] if where == 'svc' else doc[where]).append(cur)
            cur['items'].append(s[2:])
        else:
            if s in TAIL:
                where = 'tail'
            cur = {'t': s, 'items': []}
            (doc['svcs'][-1]['blocks'] if where == 'svc' else doc[where]).append(cur)
    return doc


def num(s):
    m = re.search(r'([\d,]+)', s or '')
    return int(m.group(1).replace(',', '')) if m else None


def summary(svc):
    """카드 앞면 숫자: 웹 어제·평소·머문 방문·30일, 토스 어제·30일."""
    b = {x['t']: x['items'] for x in svc['blocks']}
    web, toss = b.get('웹', []), b.get('토스', [])
    out = {}
    for it in web:
        if it.startswith('어제'):
            out['web'] = num(it)
            m = re.search(r'평소 ([\d,]+)', it)
            out['web_usual'] = num(m.group(1)) if m else None
        elif it.startswith('실제로 머문'):
            out['eng'] = num(it)
            m = re.search(r'평소 ([\d,]+)', it)
            out['eng_usual'] = num(m.group(1)) if m else None
        elif it.startswith('최근 30일'):
            out['web30'] = num(it.split('일', 1)[1])
    for it in toss:
        if it.startswith('어제'):
            out['toss'] = num(it)
        elif it.startswith('최근 30일'):
            out['toss30'] = num(it.split('일', 1)[1])
    return out


def sources(key):
    """<날짜>-detail.txt의 '유입:' 줄 → {서비스: {길: 방문수}}. 적힌 것 밖은 '그 밖'(세션 합 - 적힌 합)."""
    f = SRC / f'{key}-detail.txt'
    if not f.exists():
        return {}
    out = {}
    for sec in f.read_text().split('\n\n'):
        L = sec.strip().split('\n')
        if not L or not L[0].startswith('📊 '):
            continue
        name = G.short(L[0][2:].strip())
        tot = next((num(m.group(1)) for l in L if (m := re.search(r'세션 ([\d,]+)', l))), None)
        line = next((l[4:] for l in L if l.startswith('유입: ')), '')
        by = {}
        for part in line.split(', '):
            m = re.match(r'(.+) (\d+)$', part.strip())
            if m:
                c = G.channel(m.group(1))
                by[c] = by.get(c, 0) + int(m.group(2))
        if tot and tot > sum(by.values()):
            by['그 밖'] = tot - sum(by.values())
        if by:
            out[name] = by
    return out


def load():
    days = []
    for f in sorted(SRC.glob('20[0-9][0-9]-[0-9][0-9]-[0-9][0-9].txt'), reverse=True):
        d = dt.date.fromisoformat(f.stem)
        if d >= dt.date.today():  # 오늘 날짜 파일은 갱신 판이 쓴 하루 중간 값이라 '지금'으로만 보인다
            continue
        doc = parse(f.read_text())
        days.append({'key': f.stem, 'label': f'{d.month}/{d.day} ({"월화수목금토일"[d.weekday()]})',
                     'range': f'{d.month}/{d.day} 0시 ~ {(d + dt.timedelta(days=1)).month}/{(d + dt.timedelta(days=1)).day} 0시',
                     'doc': doc, 'sum': [summary(s) for s in doc['svcs']], 'src': sources(f.stem)})
    live = None
    lj, lt = SRC / 'live.json', SRC / 'live.txt'
    if lj.exists() and lt.exists():
        meta = json.loads(lj.read_text())
        at = dt.datetime.fromtimestamp(meta['at'] / 1000)
        doc = parse(lt.read_text().replace('- 어제 ', '- 오늘 '))
        doc['top'] = [b for b in doc['top'] if b['t'] not in ('나빠진 것', '좋아진 것')]  # 하루가 안 끝나 평소와 견주면 다 나빠 보인다
        live = {'key': 'live', 'label': '지금', 'range': f'{at.month}/{at.day} 0시 ~ {at:%H:%M}', 'doc': doc,
                'sum': [summary({'blocks': [{'t': b['t'], 'items': [i.replace('오늘 ', '어제 ', 1) for i in b['items']]} for b in s['blocks']]}) for s in doc['svcs']],
                'at': meta['at']}
    return days, live


PAGE = r'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>방문 리포트</title>
<style>
:root{--bg:#fff;--ink:#16181d;--sub:#555b66;--line:#eceef1;--soft:#f4f5f7;--bar:#c9ced6;--up:#d6302a;--down:#2860d8;--avg:#e5322d}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#121417;--ink:#eef0f3;--sub:#9aa2ad;--line:#262a30;--soft:#1c1f24;--bar:#454b55;--up:#ff6b5f;--down:#6d97ff;--avg:#ff6b5f}}
:root[data-theme=dark]{--bg:#121417;--ink:#eef0f3;--sub:#9aa2ad;--line:#262a30;--soft:#1c1f24;--bar:#454b55;--up:#ff6b5f;--down:#6d97ff;--avg:#ff6b5f}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Pretendard",sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:640px;margin:0 auto;padding:12px 16px 48px}
button{font:inherit;color:inherit;background:none;border:0;cursor:pointer;min-height:44px}
.head{display:flex;justify-content:space-between;align-items:center}
h1{font-size:20px;font-weight:700;margin:0}
.ref{border:1px solid var(--line);border-radius:10px;padding:0 12px;font-size:13px;color:var(--sub)}
.ref:disabled{opacity:.5}
.seg{display:flex;background:var(--soft);border-radius:10px;padding:3px;margin:10px 0 4px}
.seg button{flex:1;min-height:38px;border-radius:8px;font-size:13px;color:var(--sub)}
.seg button.on{background:var(--bg);color:var(--ink);font-weight:600;box-shadow:0 0 0 1px var(--line)}
.nav{display:flex;align-items:center;justify-content:space-between}
.nav button{width:44px;font-size:20px;color:var(--sub)}.nav button:disabled{opacity:.25}
.nav span{font-size:15px;font-weight:600;text-align:center}
.pk{position:relative;flex:1;display:flex;justify-content:center;cursor:pointer}.pk span{border-bottom:1px dashed var(--sub)}.pk input{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;border:0;padding:0}
.msg{font-size:13px;color:var(--sub);margin:0;min-height:0}
.sum{padding:8px 0 4px}
.sum .lb{font-size:13px;color:var(--sub)}
.sum .big{font-size:28px;font-weight:700;line-height:1.2}
.chg{font-size:13px;color:var(--sub)}.up{color:var(--up)}.down{color:var(--down)}
.chart{display:block;width:100%;height:auto;margin:8px 0 0}
.chart text{font-size:13px;fill:var(--sub)}
.leg{display:flex;align-items:center;justify-content:flex-end;gap:6px;font-size:13px;font-weight:600;color:var(--avg);margin:10px 0 -2px}
.src{margin:18px 0 4px}.src h2{font-size:15px;font-weight:600;margin:0 0 2px}.src .lb{font-size:13px;color:var(--sub);margin-bottom:6px}
.sr{display:grid;grid-template-columns:96px 1fr 92px;align-items:center;gap:10px;min-height:30px}
.sr .k{font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.sr .b{height:12px;border-radius:3px;background:var(--soft)}
.sr .b i{display:block;height:100%;border-radius:3px;background:var(--ink)}.sr .n{text-align:right;font-size:14px;white-space:nowrap}.sr .n b{font-weight:600}.sr .n span{color:var(--sub);font-size:13px;margin-left:4px}
.sort{display:flex;gap:6px;margin:14px 0 2px}
.sort button{min-height:34px;padding:0 12px;border-radius:17px;border:1px solid var(--line);font-size:13px;color:var(--sub)}
.sort button.on{border-color:var(--ink);color:var(--ink);font-weight:600}
.list{margin:0;padding:0;list-style:none}
.row{display:grid;grid-template-columns:1fr 64px 76px 12px;align-items:center;gap:10px;min-height:56px;padding:6px 8px;margin:0 -8px;border-bottom:1px solid var(--line);border-radius:10px;cursor:pointer;-webkit-tap-highlight-color:transparent}
.row:hover,.row:active{background:var(--soft)}
.row .go{color:var(--sub);font-size:20px;line-height:1;text-align:right}
.cw{position:relative;padding-top:30px}.cw .chart{touch-action:pan-y;cursor:crosshair}.chart .cur{stroke:var(--sub);stroke-width:1;stroke-dasharray:2 2}
.tt{position:absolute;top:0;background:var(--ink);color:var(--bg);font-size:14px;font-weight:600;padding:4px 10px;border-radius:8px;white-space:nowrap;pointer-events:none}
.tip{font-size:13px;color:var(--sub);margin:4px 0 2px}
.row .nm{font-size:15px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row .ds{font-size:13px;color:var(--sub);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row .v{text-align:right;font-size:17px;font-weight:600;line-height:1.2}
.row .c{text-align:right;font-size:13px}
.spark{width:64px;height:24px;display:block}
.spark polyline{fill:none;stroke:var(--sub);stroke-width:1.5}
.spark circle{fill:var(--ink)}
.notes{margin:16px 0 0}
.notes h2,.det h2{font-size:15px;font-weight:600;margin:16px 0 4px}
.notes ul,.det ul{margin:0;padding-left:18px;font-size:15px}.notes li,.det li{margin:2px 0}
details{margin:12px 0 0;border-top:1px solid var(--line);padding-top:8px}
summary{cursor:pointer;font-size:15px;font-weight:600;min-height:32px;padding-top:6px}
details ul{margin:6px 0;padding-left:18px}
.back{font-size:15px;color:var(--sub);padding:0}
table{width:100%;border-collapse:collapse;font-size:13px;margin-top:4px}
td,th{text-align:right;padding:7px 2px;border-bottom:1px solid var(--line)}td:first-child,th:first-child{text-align:left}th{color:var(--sub);font-weight:400}
</style></head><body><div class="wrap">
<div class="head"><h1>방문 리포트</h1><button class="ref" id="refresh">지금 숫자로 갱신</button></div>
<p class="msg" id="msg"></p>
<div id="main">
<div class="seg" id="mode"><button data-m="d" class="on">하루</button><button data-m="7">7일</button><button data-m="30">30일</button></div>
<div class="nav" id="nav"><button id="prev" aria-label="이전">‹</button><label class="pk"><span id="when"></span><input type="date" id="pick" aria-label="날짜 고르기"></label><button id="next" aria-label="다음">›</button></div>
<div class="sum" id="sum"></div>
<div class="sort" id="sort"><button data-s="v" class="on">방문 많은 순</button><button data-s="up">늘어난 순</button><button data-s="down">줄어든 순</button></div>
<p class="tip">서비스를 누르면 날짜별 방문·유입 경로를 볼 수 있어요</p>
<ul class="list" id="list"></ul>
<div id="notes" class="notes"></div><div id="zero"></div>
</div>
<div id="det" class="det" hidden></div>
</div>
<script>
const D=__DATA__;const LIVE_AT=__LIVEAT__;
const $=s=>document.getElementById(s);const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'})[c]);
const f=n=>n==null?'-':Math.round(n).toLocaleString('ko-KR');
const fa=n=>n!=null&&n<10&&n%1?(Math.round(n*10)/10).toString():f(n);
const days=(D.live?[D.live]:[]).concat(D.days);           // 최근 → 예전, 하루 탐색용
const full=D.days.slice().reverse();
const today=(()=>{const t=new Date(Date.now()+9*3600e3);return t.toISOString().slice(0,10)})();  // 한국 날짜                       // 예전 → 최근, 하루가 다 끝난 날만
const S={},order=[];
days.slice().reverse().forEach(k=>k.doc.svcs.forEach((sv,j)=>{const m=k.sum[j];if(!S[sv.name]){S[sv.name]={};order.push(sv.name)}S[sv.name][k.key]={web:m.web||0,eng:m.eng,toss:m.toss||0}}));
const useWeb={};order.forEach(n=>useWeb[n]=Object.values(S[n]).some(v=>v.web>0));
const val=(n,key)=>{const v=S[n][key];return v?(useWeb[n]?v.web:v.toss):null};
const webTot=key=>order.reduce((t,n)=>t+(useWeb[n]?(val(n,key)||0):0),0);
const sum=a=>{a=a.filter(x=>x!=null);return a.length?a.reduce((x,y)=>x+y,0):null};
const avg=a=>{a=a.filter(x=>x!=null);return a.length?a.reduce((x,y)=>x+y,0)/a.length:null};
function pc(a,b){if(a==null||b==null)return{t:'-',c:'',r:0};if(!b)return a?{t:'새로',c:'up',r:1e9}:{t:'-',c:'',r:0};const r=Math.round((a-b)/b*100);return{t:(r>0?'▲ ':r<0?'▼ ':'')+Math.abs(r)+'%',c:r>0?'up':r<0?'down':'',r}}
function spark(vs){const w=64,h=24,m=Math.max(...vs.map(v=>v||0),1),n=vs.length;if(n<2)return'';const pt=(v,i)=>[(i/(n-1)*(w-4)+2).toFixed(1),(h-3-(v||0)/m*(h-6)).toFixed(1)];
  const p=vs.map((v,i)=>pt(v,i).join(',')).join(' ');const [x,y]=pt(vs[n-1],n-1);return`<svg class="spark" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${p}"/><circle cx="${x}" cy="${y}" r="2"/></svg>`}
function chart(keys,vals,hi){const W=340,H=150,L=34,B=20,n=vals.length,m=Math.max(...vals.map(v=>v||0),1);const top=Math.ceil(m/(m>100?50:10))*(m>100?50:10);
  const bw=(W-L)/n;let g='',leg='';[0,.5,1].forEach(t=>{const y=(H-B)-(H-B-6)*t;g+=`<line x1="${L}" x2="${W}" y1="${y}" y2="${y}" stroke="var(--line)"/><text x="${L-6}" y="${y+4}" text-anchor="end">${f(top*t)}</text>`});
  vals.forEach((v,i)=>{const bh=Math.max((v||0)/top*(H-B-6),v?2:0);g+=`<rect x="${(L+i*bw+bw*.15).toFixed(1)}" y="${(H-B-bh).toFixed(1)}" width="${(bw*.7).toFixed(1)}" height="${bh.toFixed(1)}" rx="1.5" fill="${hi.includes(i)?'var(--ink)':'var(--bar)'}"/>`});
  {const ok=vals.filter((v,i)=>v!=null&&keys[i]!='live');if(ok.length>1){const av=ok.reduce((a,b)=>a+b,0)/ok.length,y=((H-B)-av/top*(H-B-6)).toFixed(1);  // 사용자 11/10 "평균 빨간선 가로로"
    g+=`<line x1="${L}" x2="${W}" y1="${y}" y2="${y}" stroke="var(--avg)" stroke-width="1.5" stroke-dasharray="5 3"/>`;leg=`<div class="leg"><svg width="22" height="8"><line x1="0" x2="22" y1="4" y2="4" stroke="var(--avg)" stroke-width="2" stroke-dasharray="5 3"/></svg>평균 ${f(Math.round(av))}명</div>`}}  // 11/10 "글자가 안 보여": 막대 위에 겹치던 글자를 차트 위 범례로
  [0,Math.floor((n-1)/2),n-1].filter((x,i,a)=>a.indexOf(x)==i).forEach(i=>{g+=`<text x="${(i==0?L:i==n-1?W:L+i*bw+bw/2).toFixed(1)}" y="${H-4}" text-anchor="${i==0?'start':i==n-1?'end':'middle'}">${esc(lab(keys[i]))}</text>`});
  const c=CH.push({k:keys,v:vals})-1;  // 사용자 11/11 "봉을 클릭하면 몇명인지 주식차트처럼"
  return`${leg}<div class="cw" data-c="${c}"><svg class="chart" viewBox="0 0 ${W} ${H}" role="img">${g}<line class="cur" y1="0" y2="${H-B}" style="display:none"/></svg><div class="tt" hidden></div></div>`}
const CH=[];
function chTap(e){const w=e.target.closest&&e.target.closest('.cw');if(!w)return;const c=CH[w.dataset.c],sv=w.querySelector('svg'),r=sv.getBoundingClientRect();
  const n=c.v.length,bw=(340-34)/n,x=(e.clientX-r.left)/r.width*340;const i=Math.max(0,Math.min(n-1,Math.floor((x-34)/bw)));
  const cx=34+i*bw+bw/2,cur=w.querySelector('.cur'),t=w.querySelector('.tt');cur.setAttribute('x1',cx);cur.setAttribute('x2',cx);cur.style.display='';
  t.hidden=false;t.textContent=`${lab(c.k[i])}  ${c.v[i]==null?'기록 없음':f(c.v[i])+'명'}`;const px=cx/340*r.width;t.style.left=Math.max(0,Math.min(r.width-t.offsetWidth,px-t.offsetWidth/2))+'px'}
document.addEventListener('pointerdown',chTap);document.addEventListener('pointermove',e=>{if(e.pointerType=='mouse'||e.buttons)chTap(e)});
const byKey={};days.forEach(k=>byKey[k.key]=k);
const lab=key=>key=='live'?'지금':(d=>`${+d[1]}/${+d[2]}`)(key.split('-'));
let MODE='d',IDX=0,SORT='v',OPEN=null,SH=0;
try{MODE=localStorage.getItem('ga-mode')||'d';const j=days.findIndex(k=>k.key==localStorage.getItem('ga-day'));if(j>=0)IDX=j}catch(e){}
function ctx(){ // 지금 보는 기간: keys(차트·스파크라인 줄), 값, 비교값
  if(MODE=='d'){const k=days[IDX],live=k.key=='live';const fi=live?full.length:full.findIndex(x=>x.key==k.key);
    // 사용자 11/11 "날짜가 바뀌면 미래 값이 왜 없어져, 하이라이트만 바뀌면 되잖아" — 차트 칸은 최근 14칸 고정, 고른 날만 진하게
    const all=full.map(x=>x.key).concat(D.live?['live']:[]),pos=live?all.length-1:fi;
    const st=Math.max(0,pos>=all.length-14?all.length-14:pos-13),keys=all.slice(st,st+14);
    const prev=full[fi-1]||null;
    return{keys,hi:[pos-st],when:k.label+(live?' '+k.range.split('~ ')[1]+'까지':''),live,
      cur:n=>val(n,k.key),prev:n=>prev?val(n,prev.key):null,cmp:live?'어제 하루':'전날 대비',lbl:live?'오늘 지금까지 웹 방문':'웹 방문 합계',
      tot:webTot(k.key),ptot:prev?webTot(prev.key):null,doc:k.doc}}
  // 사용자 11/11 "7일·30일은 왜 전후 클릭이 안 돼" — SH일만큼 끝을 앞당긴 기간
  const n=+MODE;SH=Math.max(0,Math.min(SH,full.length-n));const e=full.length-SH,c=full.slice(Math.max(0,e-n),e),p=full.slice(Math.max(0,e-2*n),e-n);const pv=p.length==n?p:null;
  return{keys:c.map(x=>x.key),hi:c.map((x,i)=>i),when:`${c[0].label} ~ ${c[c.length-1].label}`,live:false,
    cur:nm=>sum(c.map(x=>val(nm,x.key))),prev:nm=>pv?sum(pv.map(x=>val(nm,x.key))):null,cmp:`앞 ${n}일 대비`,lbl:`${n}일 동안 웹 방문 합계`,
    tot:sum(c.map(x=>webTot(x.key))),ptot:pv?sum(pv.map(x=>webTot(x.key))):null,days:c.length,doc:null}}
function srcBox(keys,names){ // 사용자 11/10 "방문 경로별로 비율도 숫자도, 한눈에" — 방문 횟수 기준, 많은 순 6개 + 나머지
  const by={};keys.forEach(k=>{const d=byKey[k];if(!d||!d.src)return;names.forEach(n=>{const x=d.src[n];if(x)Object.entries(x).forEach(([c,v])=>by[c]=(by[c]||0)+v)})});
  let e=Object.entries(by).filter(x=>x[1]>0).sort((a,b)=>(a[0]=='그 밖')-(b[0]=='그 밖')||b[1]-a[1]);const tot=e.reduce((t,x)=>t+x[1],0);if(!tot)return'';
  if(e.length>7){const r=e.slice(6).reduce((t,x)=>t+x[1],0);e=e.slice(0,6).concat([['그 밖',r]])}
  const mx=Math.max(...e.map(x=>x[1]));
  return`<div class="src"><h2>어디서 들어왔나</h2><div class="lb">방문 ${f(tot)}번 기준</div>${e.map(([c,v])=>`<div class="sr"><div class="k">${esc(c)}</div><div class="b"><i style="width:${(v/mx*100).toFixed(1)}%${c=='그 밖'?';background:var(--bar)':''}"></i></div><div class="n"><b>${f(v)}번</b><span>${Math.round(v/tot*100)}%</span></div></div>`).join('')}</div>`}
function render(){
  try{localStorage.setItem('ga-mode',MODE);localStorage.setItem('ga-day',days[IDX].key)}catch(e){}
  document.querySelectorAll('#mode button').forEach(b=>b.classList.toggle('on',b.dataset.m==MODE));
  document.querySelectorAll('#sort button').forEach(b=>b.classList.toggle('on',b.dataset.s==SORT));
  const C=ctx();$('when').textContent=C.when;$('prev').disabled=MODE=='d'?IDX>=days.length-1:SH>=full.length-+MODE;$('next').disabled=MODE=='d'?IDX<=0:SH<=0;
  const pk=$('pick');pk.min=full[0].key;pk.max=days[0].key=='live'?today:full[full.length-1].key;pk.value=MODE=='d'?(days[IDX].key=='live'?today:days[IDX].key):C.keys[C.keys.length-1];
  const tp=C.live?{t:'',c:''}:pc(C.tot,C.ptot);
  $('sum').innerHTML=`<div class="lb">${C.lbl}</div><div class="big">${f(C.tot)}명</div>${MODE!='d'?`<div class="lb">하루 평균 ${f(C.tot/C.days)}명</div>`:''}<div class="chg ${tp.c}">${C.live?`어제 하루 ${f(C.ptot)}명`:(C.ptot==null?'비교할 앞 기간 없음':`${C.cmp} ${tp.t}`)}</div>${chart(C.keys,C.keys.map(webTot),C.hi)}`+srcBox(C.keys.filter((k,i)=>C.hi.includes(i)),order.filter(n=>useWeb[n]));
  const rows=[],zero=[];
  order.forEach(n=>{const v=C.cur(n);if(v==null)return;const sv=C.keys.map(k=>val(n,k));if(!v&&!sv.some(x=>x)){zero.push(n);return}
    const p=pc(v,C.prev(n));const e=MODE=='d'&&S[n][days[IDX].key]?S[n][days[IDX].key].eng:null;
    rows.push({n,v,p,h:`<li class="row" data-n="${esc(n)}"><div><div class="nm">${esc(n)}</div><div class="ds">${useWeb[n]?'웹':'토스'}${MODE!='d'?` · 하루 평균 ${fa(v/C.days)}`:e!=null?` · 그중 10초 넘게 본 방문 ${f(e)}번`:''}</div></div>${spark(sv)}<div><div class="v">${f(v)}명</div><div class="c ${C.live?'':p.c}">${C.live?(C.prev(n)==null?'-':'어제 '+f(C.prev(n))):p.t}</div></div><div class="go" aria-hidden="true">›</div></li>`})});
  rows.sort(SORT=='v'?(a,b)=>b.v-a.v:SORT=='up'?(a,b)=>b.p.r-a.p.r||b.v-a.v:(a,b)=>a.p.r-b.p.r||b.v-a.v);
  $('list').innerHTML=rows.map(r=>r.h).join('');
  document.querySelectorAll('#list .row').forEach(r=>r.onclick=()=>detail(r.dataset.n));
  const top=C.doc?C.doc.top.filter(b=>b.t&&b.items.length&&!(b.items.length==1&&b.items[0]=='없음')):[];
  $('notes').innerHTML=top.length?`<details><summary>리포트 메모 ${top.reduce((t,b)=>t+b.items.length,0)}개</summary>${top.map(b=>`<h2>${esc(b.t)}</h2><ul>${b.items.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`).join('')}</details>`:'';
  $('zero').innerHTML=zero.length?`<details><summary>방문 0인 곳 ${zero.length}개</summary><ul>${zero.map(z=>`<li>${esc(z)}</li>`).join('')}</ul></details>`:'';
}
function detail(n){OPEN=n;const C=ctx();const keys=full.slice(-30).map(x=>x.key).concat(D.live?['live']:[]);const vs=keys.map(k=>val(n,k));
  const hi=keys.map((k,i)=>C.keys.includes(k)?i:-1).filter(i=>i>=0);const v=C.cur(n),pv=C.prev(n),p=pc(v,pv);
  const rows=keys.map((k,i)=>{const x=vs[i],b=i?vs[i-1]:null,d=x!=null&&b!=null&&k!='live'?x-b:null;const e=S[n][k]?S[n][k].eng:null;
    return`<tr><td>${esc(byKey[k]?byKey[k].label:k)}</td><td>${f(x)}</td><td class="${d>0?'up':d<0?'down':''}">${d==null?'-':(d>0?'+':'')+f(d)}</td><td>${useWeb[n]&&e!=null?f(e):'-'}</td></tr>`}).reverse().join('');
  const k=MODE=='d'?days[IDX]:null;const svc=k?k.doc.svcs.find(s=>s.name==n):null;
  const raw=svc?svc.blocks.filter(b=>!(b.items.length==1&&b.items[0]=='없음')):[];
  $('det').innerHTML=`<button class="back" id="back">‹ 목록으로</button><div class="sum"><div class="lb">${esc(n)} · ${MODE=='d'?esc(C.when):esc(C.when)+' 합계, 하루 평균 '+fa(v/C.days)+'명'}</div><div class="big">${f(v)}명</div>
    <div class="chg ${C.live?'':p.c}">${C.live?`어제 하루 ${f(pv)}명`:(pv==null?'비교할 앞 기간 없음':`${C.cmp} ${p.t}, ${MODE=='d'?'전날':'앞 기간'} ${f(pv)}명`)}</div>
    ${chart(keys,vs,hi)}</div>${srcBox(C.keys.filter((k,i)=>C.hi.includes(i)),[n])}<h2>날짜별 ${useWeb[n]?'웹':'토스'} 방문</h2><table><tr><th>날짜</th><th>방문</th><th>전날 대비</th><th>10초 넘게 본 방문</th></tr>${rows}</table>
    ${raw.length?`<details><summary>그날 리포트 원문</summary>${raw.map(b=>`${b.t?`<h2>${esc(b.t)}</h2>`:''}<ul>${b.items.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`).join('')}</details>`:''}`;
  $('main').hidden=true;$('det').hidden=false;window.scrollTo(0,0);$('back').onclick=()=>{OPEN=null;$('det').hidden=true;$('main').hidden=false}}
document.querySelectorAll('#mode button').forEach(b=>b.onclick=()=>{MODE=b.dataset.m;SH=0;BK.length=0;render()});
document.querySelectorAll('#sort button').forEach(b=>b.onclick=()=>{SORT=b.dataset.s;render()});
const BK=[];  // 30일 끝에서 덜 밀린 경우에도 › 가 원래 자리로 돌아오게
$('prev').onclick=()=>{if(MODE=='d')IDX++;else{BK.push(SH);SH+=+MODE}render()};$('next').onclick=()=>{if(MODE=='d')IDX--;else SH=BK.length?BK.pop():Math.max(0,SH-MODE);render()};
// 사용자 11/11 "가운데 날짜 누르면 캘린더" — 하루는 그날로, 7일·30일은 그날로 끝나는 기간으로
$('pick').onclick=e=>{try{e.target.showPicker()}catch(_){}};
$('pick').onchange=e=>{const v=e.target.value;if(!v)return;if(MODE=='d'){const j=days.findIndex(k=>(k.key=='live'?today:k.key)==v);if(j>=0)IDX=j}
  else{const j=full.findIndex(x=>x.key==v);SH=j<0?0:full.length-1-j;BK.length=0}render()};
render();
async function poll(req){for(let n=0;n<60;n++){await new Promise(r=>setTimeout(r,10000));
  try{const l=await (await fetch('live.json?'+Date.now(),{cache:'no-store'})).json();if(l.at>=req){try{localStorage.setItem('ga-day','live');localStorage.setItem('ga-mode','d')}catch(e){};location.reload();return}}catch(e){}
  $('msg').textContent=`갱신 중이에요. 보통 4~5분 걸려요 (${(n+1)*10}초 지남)`}
  $('msg').textContent='10분이 지나도 안 끝났어요. 맥이 꺼져 있거나 막혔을 수 있어요';$('refresh').disabled=false}
$('refresh').onclick=async()=>{$('refresh').disabled=true;$('msg').textContent='갱신을 요청했어요';
  try{const r=await (await fetch('api/refresh',{method:'POST'})).json();poll(r.req)}catch(e){$('msg').textContent='요청 실패: '+e;$('refresh').disabled=false}};
(async()=>{try{const s=await (await fetch('api/state',{cache:'no-store'})).json();if(s.req>LIVE_AT&&Date.now()-s.req<600000){$('refresh').disabled=true;$('msg').textContent='갱신 중이에요';poll(s.req)}}catch(e){}})();
</script></body></html>'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(Path.home() / '.cache/ga-site'))
    a = ap.parse_args()
    days, live = load()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data = json.dumps({'days': days, 'live': live}, ensure_ascii=False).replace('</', '<\\/')
    page = PAGE.replace('__DATA__', data).replace('__LIVEAT__', str(live['at'] if live else 0))
    (out / 'index.html').write_text(page)
    (out / 'live.json').write_text(json.dumps({'at': live['at'] if live else 0}))
    print(f'RESULT: OK days={len(days)} live={"yes" if live else "no"}')


if __name__ == '__main__':
    main()
