"""충청남도 공모전 홈페이지(www.chungnam.go.kr/contest.do) 작품접수 — 비회원 폼(로그인 없음).

python3 chungnam_contest_submit.py --pssrp 10016 --info ~/Documents/oguri-works/개인정보.md --pw-env CHUNGNAM_CONTEST_PW_KR \
    --title "작품명" --desc-file desc.txt --zip 충남자경위_<성명>_광고포스터_<YYYYMMDD>.zip [--type P|V] \
    [--profile "Profile 1"] [--submit --contest-id <id>]

순서(2026-11-16 충남 자치경찰 포스터 강래민 pssrpNo=21143로 같은 순서 성공):
1. 접수확인 목록(rcptIdnty/detail.do)에서 작품명 검색 → 있으면 ALREADY_SUBMITTED(exit 2)
2. forInsert.do 폼: registerNm·brthdy(date)·sexdstn(M/F)·ntcrEmad1/2·ntcrTelno1~3·passwd(8~16 영대소+숫자+특수)·applycnTyCd(P=사진,V=영상)·pssrpSj·pssrpCn, 파일 #E1(zip 하나)
3. 페이지 세계 <script>로 checkForm() 검사(dry-run은 여기까지)
4. --submit: <script>에서 FormData(#board) → fetch insert.do (alert '공모전 신청이 완료되었습니다' 응답 HTML 저장)
5. 목록에서 작품명 1건 확인 → 상세는 rcptIdnty/login.do 비밀번호(searchWrd, loginCheck()) → 첨부 fileDown 받아 SHA256을 로컬 zip과 대조
비밀번호는 --pw-env 이름으로 ~/.claude/.env에 둔다(없으면 만들어 넣음). 값은 출력하지 않는다.
김은미: --profile 'Profile 16' --info ~/Documents/oguri-works/개인정보-김은미.md --pw-env CHUNGNAM_CONTEST_PW_EM
"""
import argparse, hashlib, json, os, re, secrets, string, sys, time, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import chromectl as c  # noqa: E402

BASE = "https://www.chungnam.go.kr"
ENV = Path.home() / ".claude/.env"
JOBS = Path("/Users/ram/programming/vibecoding/공모전/_radar/jobs")


def out(status, **kw):
    print(json.dumps(kw, ensure_ascii=False, indent=1))
    print("RESULT:", status, kw.get("msg", ""))
    sys.exit({"OK": 0, "SUBMITTED": 0, "READY": 0, "FAIL": 1}.get(status, 2))


def pw_get(name):
    for l in ENV.read_text().splitlines():
        if l.startswith(name + "="):
            return l.split("=", 1)[1].strip()
    a = string.ascii_letters + string.digits
    p = "".join(secrets.choice(a) for _ in range(10)) + secrets.choice("ABCDEFGH") + secrets.choice("23456789") + secrets.choice("!@#^*+=")
    with ENV.open("a") as f:
        f.write(f"\n{name}={p}\n")
    return p


def info(md):
    t = Path(md).expanduser().read_text()
    g = lambda k: re.search(r"^- " + k + r":?\s*(.+)$", t, re.M).group(1).strip()
    ph = re.search(r"(01\d)-(\d{3,4})-(\d{4})", g("휴대폰")).groups()
    return dict(name=g("이름"), birth=re.search(r"\d{4}-\d{2}-\d{2}", g("생년월일")).group(0),
                sex="M" if g("성별").startswith("남") else "F", ph=ph,
                email=re.search(r"[\w.+-]+@[\w.-]+", g("이메일")).group(0))


def main_js(tid, code):
    c.js_json(tid, "const s=document.createElement('script');s.textContent=" + json.dumps(code) + ";document.head.appendChild(s);return 1")


def search(tid, pssrp, title):
    c.goto(tid, f"{BASE}/contest/competition/rcptIdnty/detail.do?menuNo=2600006&pssrpDspyCd={pssrp}&pageIndex=1&searchCnd=1&searchWrd=" + urllib.parse.quote(title))
    time.sleep(4)
    return c.js_json(tid, r"""return [...document.querySelectorAll('table tbody tr')].filter(tr=>tr.querySelector('a')).map(tr=>({t:tr.innerText.replace(/\s+/g,' ').trim(),href:tr.querySelector('a').getAttribute('href')}))""") or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pssrp", required=True); ap.add_argument("--info", required=True); ap.add_argument("--pw-env", required=True)
    ap.add_argument("--title", required=True); ap.add_argument("--desc-file", required=True); ap.add_argument("--zip", required=True)
    ap.add_argument("--type", default="P"); ap.add_argument("--profile", default="Profile 1")
    ap.add_argument("--submit", action="store_true"); ap.add_argument("--contest-id"); ap.add_argument("--keep-tab", action="store_true")
    a = ap.parse_args()
    I = info(a.info); pw = pw_get(a.pw_env); desc = Path(a.desc_file).read_text().strip()
    zpath = Path(a.zip).resolve(); zsha = hashlib.sha256(zpath.read_bytes()).hexdigest()
    tid = c.new_tab(f"{BASE}/contest/competition/contest/forInsert.do?menuNo=2600005&pssrpDspyCd={a.pssrp}", a.profile)
    try:
        rows = search(tid, a.pssrp, a.title)
        if rows:
            out("ALREADY_SUBMITTED", rows=rows, msg="접수확인 목록에 같은 작품명 있음")
        if a.submit and a.contest_id:
            try:
                os.mkdir(JOBS / f"{a.contest_id}.submit.lock")
            except FileExistsError:
                if not (JOBS / f"{a.contest_id}.submit.lock").is_dir():
                    raise
                # 지휘·job이 이미 잠갔으면 그대로 쓴다(.pressed 있으면 다시 안 누름)
                if (JOBS / f"{a.contest_id}.submit.pressed").exists():
                    out("BLOCKED", msg="이미 누른 기록(.pressed) — 목록에 안 보이면 사람이 확인")
        c.goto(tid, f"{BASE}/contest/competition/contest/forInsert.do?menuNo=2600005&pssrpDspyCd={a.pssrp}")
        time.sleep(4)
        e1, e2 = I["email"].split("@")
        V = dict(registerNm=I["name"], brthdy=I["birth"], ntcrEmad1=e1, ntcrEmad2=e2, ntcrTelno2=I["ph"][1], ntcrTelno3=I["ph"][2],
                 passwd=pw, pssrpSj=a.title, pssrpCn=desc)
        S = dict(ntcrTelno1=I["ph"][0], applycnTyCd=a.type, emailSelect=e2)
        chk = c.js_json(tid, "const V=" + json.dumps(V) + ";const S=" + json.dumps(S) + ";const sex=" + json.dumps(I["sex"]) + r""";
const set=(el,v)=>{el.value=v;el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));};
for(const k in V)set(document.getElementById(k),V[k]);
for(const k in S){const el=document.getElementById(k);if([...el.options].some(o=>o.value===S[k]))set(el,S[k]);}
document.getElementById(sex).checked=true;
const o={};for(const k in V)o[k]=document.getElementById(k).value===V[k];for(const k in S)o[k]=document.getElementById(k).value===S[k];o.sex=document.getElementById(sex).checked;return o;""")
        if not all(chk.values()):
            out("FAIL", fields=chk, msg="칸 값이 안 들어감")
        up = c.upload_file(tid, str(zpath), selector="#E1")
        if not up.startswith("ok"):
            out("FAIL", msg="파일 칸 없음 " + up)
        code = r"""(function(){const d=document.documentElement;d.dataset.al='';window.alert=m=>{d.dataset.al+=String(m)+'||'};window.confirm=()=>true;
let ok=false;try{ok=checkForm()===true}catch(e){d.dataset.al+='ERR '+e}d.dataset.chk=String(ok);
if(ok&&REAL){const fm=document.getElementById('board');fetch(new URL('insert.do',location.href).href,{method:'POST',body:new FormData(fm),credentials:'same-origin'})
.then(async r=>{d.dataset.st=r.status+'';const t=await r.text();const ta=document.createElement('textarea');ta.id='__resp';ta.style.display='none';ta.value=t;document.body.appendChild(ta);d.dataset.done='1'})
.catch(e=>{d.dataset.st='ERR '+e;d.dataset.done='1'})}else d.dataset.done='1'})();""".replace("REAL", "true" if a.submit else "false")
        if a.submit and a.contest_id:
            (JOBS / f"{a.contest_id}.submit.pressed").touch()
        main_js(tid, code)
        r = None
        for _ in range(120):
            r = c.js_json(tid, "const d=document.documentElement.dataset;return d.done?{chk:d.chk,al:d.al,st:d.st||''}:null")
            if r:
                break
            time.sleep(2)
        if not r or r["chk"] != "true":
            out("FAIL", check=r, msg="checkForm 실패")
        if not a.submit:
            out("READY", fields=chk, upload=up, msg="dry-run — 값·파일 들어감, checkForm 통과")
        resp = c.js_json(tid, "return (document.getElementById('__resp')||{}).value||''") or ""
        alerts = re.findall(r"alert\(['\"]([^'\"]+)", resp)
        rows = search(tid, a.pssrp, a.title)
        if len(rows) != 1:
            out("UNCONFIRMED", alerts=alerts, rows=rows, msg="목록에서 1건 확인 안 됨 — 다시 누르지 말 것")
        no = re.search(r"pssrpNo=(\d+)", rows[0]["href"]).group(1)
        c.goto(tid, f"{BASE}/contest/competition/rcptIdnty/login.do?menuNo=2600006&pssrpNo={no}&pssrpDspyCd={a.pssrp}&pageIndex=1")
        time.sleep(4)
        c.js_json(tid, "document.querySelector('#frm input[name=searchWrd]').value=" + json.dumps(pw) + ";return 1")
        main_js(tid, "loginCheck();")
        time.sleep(5)
        href = c.js_json(tid, r"""const a=[...document.querySelectorAll('a')].find(x=>/fileDown/.test(x.getAttribute('href')||''));return a?a.getAttribute('href'):null""")
        c.js_json(tid, r"""const d=document.documentElement;delete d.dataset.h;fetch(""" + json.dumps(href or "") + r""",{credentials:'same-origin'}).then(r=>r.arrayBuffer()).then(b=>crypto.subtle.digest('SHA-256',b).then(h=>{d.dataset.h=[...new Uint8Array(h)].map(x=>x.toString(16).padStart(2,'0')).join('')})).catch(e=>d.dataset.h='ERR');return 1""")
        h = None
        for _ in range(40):
            h = c.js_json(tid, "return document.documentElement.dataset.h||null")
            if h:
                break
            time.sleep(1)
        st = "SUBMITTED" if h == zsha else "UNCONFIRMED"
        out(st, pssrpNo=no, alerts=alerts, server_sha256=h, local_sha256=zsha, at=time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
            msg=f"pssrpNo={no} 서버 첨부 해시 {'일치' if st == 'SUBMITTED' else '불일치/확인 못 함'}")
    finally:
        if not a.keep_tab:
            try:
                c.close_tab(tid)
            except Exception:
                pass


if __name__ == "__main__":
    main()
