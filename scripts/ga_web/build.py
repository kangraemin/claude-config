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


def load():
    days = []
    for f in sorted(SRC.glob('20[0-9][0-9]-[0-9][0-9]-[0-9][0-9].txt'), reverse=True):
        d = dt.date.fromisoformat(f.stem)
        if d >= dt.date.today():  # 오늘 날짜 파일은 갱신 판이 쓴 하루 중간 값이라 '지금'으로만 보인다
            continue
        doc = parse(f.read_text())
        days.append({'key': f.stem, 'label': f'{d.month}/{d.day} ({"월화수목금토일"[d.weekday()]})',
                     'range': f'{d.month}/{d.day} 0시 ~ {(d + dt.timedelta(days=1)).month}/{(d + dt.timedelta(days=1)).day} 0시',
                     'doc': doc, 'sum': [summary(s) for s in doc['svcs']]})
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
:root{--bg:#f6f7f9;--card:#fff;--ink:#16181d;--sub:#5d6470;--line:#e4e7ec;--acc:#2b62e3;--up:#137a3f;--down:#c0352b}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#111316;--card:#1b1e23;--ink:#eef0f3;--sub:#9aa2ad;--line:#2b3038;--acc:#6d97ff;--up:#4cc27a;--down:#ff7a6e}}
:root[data-theme=dark]{--bg:#111316;--card:#1b1e23;--ink:#eef0f3;--sub:#9aa2ad;--line:#2b3038;--acc:#6d97ff;--up:#4cc27a;--down:#ff7a6e}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Pretendard",sans-serif}
.wrap{max-width:760px;margin:0 auto;padding:16px 16px 60px}
h1{font-size:22px;margin:4px 0 2px}.range{color:var(--sub);font-size:14px;margin:0 0 14px}
.bar{display:flex;gap:8px;align-items:center;margin:0 0 10px}
select{flex:1;font:inherit;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);min-height:44px}
button{font:inherit;min-height:44px;padding:0 14px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
button.go{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
button:disabled{opacity:.5}
.msg{color:var(--sub);font-size:14px;min-height:20px;margin:0 0 12px}
.top{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:0 0 14px}
.top h3{font-size:15px;margin:8px 0 2px}.top ul{margin:0;padding-left:18px}.top li{margin:2px 0}
.top .down li{color:var(--down)}.top .up li{color:var(--up)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
@media (max-width:520px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;cursor:pointer}
.card .nm{font-weight:600;font-size:16px}
.card .big{font-size:28px;font-weight:700;margin:2px 0 0}
.card .ln{color:var(--sub);font-size:14px}
.card .chg{font-size:14px;font-weight:600}.chg.up{color:var(--up)}.chg.down{color:var(--down)}
.card .more{display:none;border-top:1px solid var(--line);margin-top:10px;padding-top:8px}
.card.open .more{display:block}
.more h4{font-size:14px;margin:8px 0 2px;color:var(--sub)}.more ul{margin:0;padding-left:18px;font-size:15px}
.seg{display:flex;gap:6px;margin:0 0 12px}.seg button{flex:1}.seg button.on{background:var(--ink);border-color:var(--ink);color:var(--bg);font-weight:600}
.bars{display:flex;align-items:flex-end;gap:2px;height:56px;margin:10px 0 2px}.bars i{flex:1;background:var(--line);border-radius:2px 2px 0 0;min-height:2px}.bars i.last{background:var(--sub)}
.axis{display:flex;justify-content:space-between;color:var(--sub);font-size:13px}
table{width:100%;border-collapse:collapse;font-size:14px;margin-top:6px}td,th{text-align:right;padding:4px 2px;border-bottom:1px solid var(--line)}td:first-child,th:first-child{text-align:left}th{color:var(--sub);font-weight:400}
.up,.card .ln.up{color:var(--up)}.down,.card .ln.down{color:var(--down)}
details{margin:16px 0 0;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 16px}
summary{cursor:pointer;font-weight:600;min-height:28px}details ul{margin:6px 0;padding-left:18px}
</style></head><body><div class="wrap">
<h1>방문 리포트</h1><p class="range" id="range"></p>
<div class="seg"><button id="vDay" class="on">하루씩</button><button id="vTrend">흐름·증감</button></div>
<div id="dayView">
<div class="bar"><button id="prev" aria-label="이전 날">‹</button><select id="day"></select><button id="next" aria-label="다음 날">›</button></div>
<div class="bar"><button class="go" id="refresh">지금 숫자로 갱신</button></div>
<p class="msg" id="msg"></p>
<div id="top"></div><div class="grid" id="grid"></div><div id="tail"></div>
</div>
<div id="trendView" hidden>
<div class="seg" id="per"><button data-n="7" class="on">최근 7일</button><button data-n="14">14일</button><button data-n="30">30일</button></div>
<p class="range" id="trange"></p>
<div class="top" id="tsum"></div><div class="grid" id="tgrid"></div><div id="ttail"></div>
</div>
</div>
<script>
const D=__DATA__;const LIVE_AT=__LIVEAT__;
const days=(D.live?[D.live]:[]).concat(D.days);
const $=s=>document.getElementById(s);const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'})[c]);
const f=n=>n==null?'-':n.toLocaleString('ko-KR');
function chg(a,b){if(a==null||!b)return'';const r=a/b;if(r>=1.3)return`<span class="chg up">평소의 ${r.toFixed(1)}배</span>`;if(r<=0.7)return`<span class="chg down">평소보다 ${Math.round((1-r)*100)}% 적음</span>`;return'<span class="ln">평소와 비슷</span>'}
function show(i){
  let k=days[i];try{localStorage.setItem('ga-day',k.key)}catch(e){}
  $('day').value=i;$('range').textContent=k.range+(k.key=='live'?' (하루가 안 끝난 숫자)':'');
  $('top').innerHTML=k.doc.top.filter(b=>b.items.length&&!(b.items.length==1&&b.items[0]=='없음')).map(b=>`<div class="top ${b.t=='나빠진 것'?'down':b.t=='좋아진 것'?'up':''}"><h3>${esc(b.t)}</h3><ul>${b.items.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`).join('')||'';
  const live=k.key=='live';const cards=[],zero=[];
  k.doc.svcs.forEach((s,j)=>{const m=k.sum[j];const web=m.web||0,toss=m.toss||0;
    if(!web&&!toss&&!m.web30&&!m.toss30){zero.push(s.name);return}
    const main=web?`<div class="big">${f(web)}명</div><div class="ln">웹 방문${m.web_usual!=null&&!live?` · 평소 ${f(m.web_usual)}명`:''}</div>`:`<div class="big">${f(toss)}명</div><div class="ln">토스 방문</div>`;
    const lines=[];if(web&&!live)lines.push(chg(m.eng??web,m.eng_usual??m.web_usual));
    const pd=live?null:days[i+1];if(pd&&pd.key!='live'){const pj=pd.doc.svcs.findIndex(x=>x.name==s.name);const pv=pj>=0?(web?pd.sum[pj].web:pd.sum[pj].toss):null;if(pv!=null){const dv=(web||toss)-pv;lines.push(`<div class="ln ${dv>0?'up':dv<0?'down':''}">전날보다 ${dv>0?'+':''}${f(dv)}명</div>`)}}
    if(m.eng!=null)lines.push(`<div class="ln">실제로 머문 방문 ${f(m.eng)}회${m.eng_usual!=null&&!live?` · 평소 ${f(m.eng_usual)}회`:''}</div>`);
    if(web&&m.toss!=null)lines.push(`<div class="ln">토스 ${f(m.toss)}명</div>`);
    const blocks=s.blocks.filter(b=>!(b.items.length==1&&b.items[0]=='없음'));
    cards.push(`<div class="card"><div class="nm">${esc(s.name)}</div>${main}${lines.join('')}<div class="more">${blocks.map(b=>`<h4>${esc(b.t)}</h4><ul>${b.items.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`).join('')}</div></div>`)});
  $('grid').innerHTML=cards.join('');
  $('tail').innerHTML=(zero.length?`<details><summary>방문 0인 곳 ${zero.length}개</summary><ul>${zero.map(z=>`<li>${esc(z)}</li>`).join('')}</ul></details>`:'')+k.doc.tail.filter(b=>b.t!='전부 0인 곳').map(b=>`<details><summary>${esc(b.t)}</summary><ul>${b.items.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></details>`).join('');
  document.querySelectorAll('#grid .card').forEach(c=>c.onclick=()=>c.classList.toggle('open'));
  $('prev').disabled=i>=days.length-1;$('next').disabled=i<=0;
}
const full=D.days.slice().reverse();// 오래된 날 → 최근 날, 하루 다 끝난 날만
const series={};full.forEach((k,di)=>k.doc.svcs.forEach((sv,j)=>{const m=k.sum[j];(series[sv.name]=series[sv.name]||{})[k.key]={web:m.web||0,eng:m.eng,toss:m.toss||0}}));
const avg=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:null;
const pct=(a,b)=>{if(a==null||b==null)return'<span class="ln">앞 기간 자료 없음</span>';if(!b)return a?'<span class="up">새로 생김</span>':'';const r=Math.round((a-b)/b*100);return`<span class="${r>0?'up':r<0?'down':''}">앞 기간보다 ${r>0?'+':''}${r}%</span>`};
let PER=7;
function trend(){
  const n=Math.min(PER,full.length),cur=full.slice(-n),prev=full.slice(-2*n,-n);const pv=prev.length==n?prev:null;
  $('trange').textContent=`${cur[0].label} ~ ${cur[n-1].label}, 하루 평균으로 봐요`+(pv?` (앞 기간 ${pv[0].label} ~ ${pv[n-1].label})`:'');
  const val=(nm,k,f2)=>{const v=(series[nm]||{})[k.key];return v?f2(v):0};
  let T=0,TP=0;const cards=[],zero=[];
  Object.keys(series).forEach(nm=>{
    const useWeb=cur.some(k=>val(nm,k,v=>v.web)>0);const g=v=>useWeb?v.web:v.toss;
    const vals=cur.map(k=>val(nm,k,g)),pvals=pv?pv.map(k=>val(nm,k,g)):null;
    const a=avg(vals),b=pvals?avg(pvals):null;if(useWeb){T+=a;TP+=b||0}
    if(!vals.some(x=>x)){zero.push(nm);return}
    const mx=Math.max(...vals,1);
    const rows=cur.map((k,ii)=>{const v=vals[ii],p0=ii?vals[ii-1]:(pvals?pvals[n-1]:null),d=p0==null?'':v-p0;const e=val(nm,k,v=>v.eng);
      return`<tr><td>${esc(k.label)}</td><td>${f(v)}</td><td class="${d>0?'up':d<0?'down':''}">${d===''?'-':(d>0?'+':'')+f(d)}</td><td>${useWeb&&e!=null?f(e):'-'}</td></tr>`}).reverse().join('');
    cards.push({a,html:`<div class="card"><div class="nm">${esc(nm)}</div><div class="big">${f(Math.round(a))}명</div><div class="ln">하루 평균 ${useWeb?'웹':'토스'} 방문</div><div class="chg">${pct(a,b)}</div>
      <div class="bars">${vals.map((v,ii)=>`<i class="${ii==n-1?'last':''}" style="height:${Math.max(4,Math.round(v/mx*100))}%"></i>`).join('')}</div><div class="axis"><span>${esc(cur[0].label)}</span><span>${esc(cur[n-1].label)}</span></div>
      <div class="more"><table><tr><th>날짜</th><th>방문</th><th>전날 대비</th><th>머문 방문</th></tr>${rows}</table></div></div>`})});
  cards.sort((x,y)=>y.a-x.a);
  $('tsum').innerHTML=`<h3>전체 웹 방문 하루 평균 ${f(Math.round(T))}명</h3><ul><li>${pv?pct(T,TP):'앞 기간 자료가 아직 없어요'}</li><li>카드를 누르면 날짜별 숫자와 전날 대비가 나와요</li></ul>`;
  $('tgrid').innerHTML=cards.map(c=>c.html).join('');
  $('ttail').innerHTML=zero.length?`<details><summary>이 기간 방문 0인 곳 ${zero.length}개</summary><ul>${zero.map(z=>`<li>${esc(z)}</li>`).join('')}</ul></details>`:'';
  document.querySelectorAll('#tgrid .card').forEach(c=>c.onclick=()=>c.classList.toggle('open'));
}
document.querySelectorAll('#per button').forEach(b=>b.onclick=()=>{PER=+b.dataset.n;document.querySelectorAll('#per button').forEach(x=>x.classList.toggle('on',x==b));trend()});
function view(t){$('dayView').hidden=t;$('range').hidden=t;$('trendView').hidden=!t;$('vDay').classList.toggle('on',!t);$('vTrend').classList.toggle('on',t);try{localStorage.setItem('ga-view',t?'t':'d')}catch(e){};if(t)trend()}
$('vDay').onclick=()=>view(false);$('vTrend').onclick=()=>view(true);
$('day').innerHTML=days.map((k,i)=>`<option value="${i}">${esc(k.label)}${k.key=='live'?' '+esc(k.range.split('~ ')[1]):''}</option>`).join('');
$('day').onchange=e=>show(+e.target.value);$('prev').onclick=()=>show(+$('day').value+1);$('next').onclick=()=>show(+$('day').value-1);
let start=0;try{const s=localStorage.getItem('ga-day');const j=days.findIndex(k=>k.key==s);if(j>=0)start=j}catch(e){}
show(start);try{if(localStorage.getItem('ga-view')=='t')view(true)}catch(e){}
async function poll(req){for(let n=0;n<60;n++){await new Promise(r=>setTimeout(r,10000));
  try{const l=await (await fetch('live.json?'+Date.now(),{cache:'no-store'})).json();if(l.at>=req){try{localStorage.setItem('ga-day','live')}catch(e){};location.reload();return}}catch(e){}
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
