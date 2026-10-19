(async()=>{
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function post(u,b){for(let i=0;i<5;i++){try{const r=await fetch('/api/v3/'+u,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(b)});if(r.ok)return await r.json();}catch(e){}await sleep(1500*(i+1));}throw new Error('fail '+u);}
const blocks={};
async function load(ids){ids=ids.filter(i=>!blocks[i]);for(let k=0;k<ids.length;k+=80){const r=await post('syncRecordValues',{requests:ids.slice(k,k+80).map(id=>({pointer:{table:'block',id},version:-1}))});for(const [id,v] of Object.entries(r.recordMap.block||{}))blocks[id]=v.value?.value||v.value;}}
const rt=t=>(t||[]).map(([s,f])=>{if(!f)return s;let o=s;for(const a of f){if(a[0]==='b')o='**'+o+'**';else if(a[0]==='i')o='_'+o+'_';else if(a[0]==='c')o='`'+o+'`';else if(a[0]==='a')o='['+o+']('+a[1]+')';}return o}).join('');
const pages=[];const imgs=[];
async function page(id,parentIdx){await load([id]);const b=blocks[id];const p={id,title:rt(b.properties?.title),parent:parentIdx,lines:[],children:[]};const idx=pages.length;pages.push(p);
async function body(ids,depth){await load(ids);let n=0;for(const c of ids){const x=blocks[c];if(!x)continue;const ind='  '.repeat(depth);const t=rt(x.properties?.title);
 if(x.type==='page'){p.children.push(pages.length);p.lines.push(ind+'- 📄 {{PAGE:'+pages.length+'}}');await page(c,idx);continue;}
 n=x.type==='numbered_list'?n+1:0;
 switch(x.type){case 'header':p.lines.push('# '+t);break;case 'sub_header':p.lines.push('## '+t);break;case 'sub_sub_header':p.lines.push('### '+t);break;
 case 'bulleted_list':p.lines.push(ind+'- '+t);break;case 'numbered_list':p.lines.push(ind+n+'. '+t);break;case 'to_do':p.lines.push(ind+'- ['+(x.properties?.checked?'x':' ')+'] '+t);break;
 case 'quote':p.lines.push(ind+'> '+t);break;case 'callout':p.lines.push(ind+'> '+(x.format?.page_icon||'💡')+' '+t);break;case 'toggle':p.lines.push(ind+'- ▸ '+t);break;
 case 'code':p.lines.push('```\n'+t+'\n```');break;case 'divider':p.lines.push('---');break;
 case 'image':{const src=x.format?.display_source||rt(x.properties?.source);imgs.push({id:x.id,src,space:x.space_id});const cap=rt(x.properties?.caption);p.lines.push(ind+'![]('+'IMG:'+x.id+')'+(cap?'\n'+ind+'_'+cap+'_':''));break;}
 case 'table':{const cols=x.format?.table_block_column_order||[];await load(x.content||[]);(x.content||[]).forEach((r,i)=>{const row=blocks[r];p.lines.push('| '+cols.map(c=>rt(row?.properties?.[c]).replace(/\|/g,'\\|')).join(' | ')+' |');if(i===0)p.lines.push('|'+cols.map(()=>'---').join('|')+'|');});p.lines.push('');continue;}
 default: if(t)p.lines.push(ind+t);}
 if(x.content&&x.type!=='table')await body(x.content,depth+(['bulleted_list','numbered_list','to_do','toggle','quote','callout'].includes(x.type)?1:0));
 if(depth===0)p.lines.push('');}}
if(b.content)await body(b.content,0);}
await page(window.__ROOT,-1);
const signed=[];for(let k=0;k<imgs.length;k+=50){const r=await post('getSignedFileUrls',{urls:imgs.slice(k,k+50).map(i=>({url:i.src,permissionRecord:{table:'block',id:i.id,spaceId:i.space}}))});signed.push(...r.signedUrls);}
imgs.forEach((im,i)=>im.signed=signed[i]);
window.__exp=JSON.stringify({pages,imgs});window.__done=true;})().catch(e=>{window.__err=String(e.stack||e);window.__done=true});
