"""신월곡1구역 상업시설&공동주택 네이밍 공모전 응모폼(그누보드 guest 게시판) 입력·제출 — 2026-11-10 실제로 돈 순서.

사용:
  python3 sinwolgok_naming_submit.py --shop "문라운드 (MoonRound)" --apt "루나베일 (LunaVale)" \
      --intent-file intent.txt --dong-file dong_sel.txt --out-dir <증거 폴더> [--submit --contest-id sinwolgok1-naming --held]
  --submit 없으면 칸을 채우고 사이트 검사함수(fwrite_submit)까지 통과하는지만 보고 멈춘다(dry-run).

순서(함정 포함):
  1. 폼 주소 https://xn--1-xb6eo69cxtd.com/board/bbs/write.php?bo_table=guest (신월곡1.com 첫 화면 iframe과 같은 문서). 로그인·인증 없음.
  2. 주소 선택칸은 sojaeji.js 행정동 목록(법정동 아님). 시도 '서울' → onchange → 구군 → onchange → 동. 행정동은 도로명 주소를
     카카오 로컬 coord2regioncode(H)로 구해 --dong-file로 넘긴다(개인정보.md엔 동 이름이 없음).
  3. 전송은 form target="proc"(숨은 iframe)이라 응답의 alert가 iframe 안에서 떠 AppleScript가 멈춘다 → alert를 기록용으로
     바꾸고, fwrite_submit 검사를 그대로 돌린 뒤 form.submit 대신 같은 FormData를 fetch로 action에 보내 응답 본문·최종 URL을 받는다.
  4. 목록(board.php?bo_table=guest)은 '목록을 볼 권한이 없습니다' — 이미 낸 글 확인 불가. 로컬 기록(guard_and_lock)으로만 중복 확인.
개인정보는 출력하지 않는다(값 대조 결과는 True/False만).
"""
import json, os, re, sys, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as cm  # noqa: E402
from _common import c  # noqa: E402

URL = "https://xn--1-xb6eo69cxtd.com/board/bbs/write.php?bo_table=guest"


def main():
    ap = cm.parser("신월곡1구역 네이밍 응모폼", submit=True)
    ap.add_argument("--shop", required=True)
    ap.add_argument("--apt", required=True)
    ap.add_argument("--intent-file", required=True)
    ap.add_argument("--dong-file", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--held", action="store_true", help="지휘 세션이 잠금을 먼저 건 경우")
    a = ap.parse_args()
    out_dir = Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    info = cm.personal_info()
    intent = Path(a.intent_file).read_text().strip()
    dong = Path(a.dong_file).read_text().strip()
    p1, p2, p3 = info["phone"].split("-")
    want = {"wr_8": info["name"], "hp1": p1, "hp2": p2, "hp3": p3, "sido": "서울", "gugun": "동대문구", "dong": dong,
            "wr_1": "비조합원", "personal1": "y", "personal2": "y",
            "wr_link1": a.shop, "wr_link2": a.apt, "wr_content": intent}
    out = {"form": URL}

    def body():
        with cm.tab(URL, a) as T:
            go(T)

    def go(T):
        J = lambda b, timeout=40: c.js_json(T, b, timeout)  # noqa: E731
        cm.poll(T, 'return !!document.querySelector("#wr_content") && document.querySelectorAll("#sido option").length>3', 30)
        # AppleScript JS는 격리 환경이라 페이지 전역(fwrite_submit·alert)이 안 보인다 → <script>를 넣어 페이지 쪽에서 돌리고 결과는 data 속성으로 받는다
        def MW(code):
            J('const s=document.createElement("script");s.textContent=' + json.dumps("(()=>{let __r;try{__r=(()=>{" + code + "})()}catch(e){__r={err:String(e)}}document.documentElement.dataset.mw=JSON.stringify(__r===undefined?null:__r)})()") + ';document.documentElement.dataset.mw="";document.head.appendChild(s);s.remove();return 1')
            v = J('return document.documentElement.dataset.mw')
            return json.loads(v) if v else None
        MW('window.__alerts=[];window.alert=m=>{window.__alerts.push(String(m))};window.confirm=m=>{window.__alerts.push("confirm:"+m);return true};return 1')
        W = json.dumps(want, ensure_ascii=False)
        r = J(f'''const w={W};const f=document.getElementById("fwrite");
const setv=(el,v)=>{{el.value=v;el.dispatchEvent(new Event("input",{{bubbles:true}}));el.dispatchEvent(new Event("keyup",{{bubbles:true}}));}};
const sel=(id,v)=>{{const s=document.getElementById(id);if(![...s.options].some(o=>o.value==v))return false;s.value=v;if(s.onchange)s.onchange();s.dispatchEvent(new Event("change",{{bubbles:true}}));return true}};
const res={{}};
for(const n of ["personal1","personal2","wr_1"]){{const el=[...f.querySelectorAll('input[name="'+n+'"]')].find(x=>x.value==w[n]);res[n]=!!el;if(el)el.checked=true}}
res.hp1=sel("hp1",w.hp1);res.sido=sel("sido",w.sido);res.gugun=sel("gugun",w.gugun);res.dong=sel("dong",w.dong);
for(const n of ["wr_8","hp2","hp3","wr_link1","wr_link2","wr_content"])setv(f.querySelector('[name="'+n+'"]'),w[n]);
return res''')
        out["set"] = r
        got = J(f'''const w={W};const f=document.getElementById("fwrite");const g={{}};
for(const n of Object.keys(w)){{const els=f.querySelectorAll('[name="'+n+'"],#'+n);let v;
 const rs=[...f.querySelectorAll('input[type=radio][name="'+n+'"]')];
 if(rs.length){{const c=rs.find(x=>x.checked);v=c?c.value:null}}else{{const e=document.getElementById(n)||f.querySelector('[name="'+n+'"]');v=e?e.value:null}}
 g[n]=v===w[n]}}
g.content_len=f.wr_content.value.trim().length;return g''')
        out["match"] = got
        print(">> match", json.dumps(got, ensure_ascii=False), file=sys.stderr, flush=True)
        bad = [k for k, v in got.items() if v is False]
        if bad:
            raise cm.Blocked(f"FIELD_MISMATCH {bad}")
        # 입력 상태 기록(개인정보는 가린 값만 파일로)
        masked = J('''const f=document.getElementById("fwrite");const m=s=>s?s[0]+"*".repeat(Math.max(0,s.length-1)):"";
return {"개인정보 수집 및 이용 동의":f.querySelector('input[name=personal1]:checked').value=="y"?"동의":"미동의",
"필수 항목의 마케팅 목적 활용 동의":f.querySelector('input[name=personal2]:checked').value=="y"?"동의":"미동의",
"이름":m(f.wr_8.value),"휴대전화":f.hp1.value+"-****-****","주소":f.mb_addr1.value+" / "+f.mb_addr2.value+" / (가림)",
"조합원 여부":f.querySelector('input[name=wr_1]:checked').value,"상업시설(상가)":f.wr_link1.value,"공동주택(아파트)":f.wr_link2.value,
"제안의도":f.wr_content.value,"제안의도_글자수":f.wr_content.value.length}''')
        (out_dir / "form_values_masked.json").write_text(json.dumps(masked, ensure_ascii=False, indent=1))
        # 사이트 검사함수 통과 여부 (submit은 가로채 막음)
        chk = MW('''const f=document.getElementById("fwrite");window.__go=0;const orig=f.submit;f.submit=function(){window.__go=1};
window.__alerts=[];try{fwrite_submit(f)}finally{f.submit=orig}return {go:window.__go,alerts:window.__alerts}''')
        out["validate"] = chk
        if chk.get("go") != 1:
            raise cm.Blocked(f"VALIDATE_FAIL {chk.get('alerts')}")
        if not a.submit:
            cm.emit(out, "DRY_RUN", "칸 채움·검사 통과, 전송 안 함")
            return
        lock = cm.guard_and_lock(a.contest_id, held=a.held) if a.contest_id else None
        out["pressed_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        MW('''const f=document.getElementById("fwrite");window.__res=null;const fd=new FormData(f);
fetch(f.action,{method:"POST",body:fd,credentials:"include"}).then(r=>r.text().then(t=>{window.__res={status:r.status,url:r.url,redirected:r.redirected,text:t}}))
.catch(e=>{window.__res={error:String(e)}});return 1''')
        res = None
        for _ in range(40):
            time.sleep(1)
            res = MW('return window.__res')
            if res:
                break
        out["done_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        if lock:
            (lock / "SENT.txt").write_text(f"{out['pressed_at']} POST write_update.php status={res and res.get('status')}\n")
        if not res:
            raise cm.Blocked("NO_RESPONSE 40초 안에 응답 없음 — 결과 불확실, 재제출 금지")
        (out_dir / "response.html").write_text(res.get("text", "") or "")
        out["response"] = {k: res.get(k) for k in ("status", "url", "redirected", "error")}
        txt = re.sub(r"\s+", " ", res.get("text", "") or "")
        out["response_alerts"] = re.findall(r'alert\(["\'](.*?)["\']\)', txt)[:5]
        out["response_text"] = re.sub(r"<[^>]+>", " ", txt)[:600]
        # 완료 응답을 탭에 그대로 띄워 캡처(스크립트 제거, alert 문구는 화면 글자로)
        MW('''const r=window.__res;const d=document.createElement("div");d.innerHTML=r.text.replace(/<script[\\s\\S]*?<\\/script>/gi,"");
const al=(r.text.match(/alert\\(["'](.*?)["']\\)/g)||[]).join("\\n");
document.body.innerHTML="<div style='font:16px sans-serif;padding:24px'><h2>신월곡1구역 네이밍 응모 전송 결과</h2><p>POST "+r.status+" → "+r.url+"</p><pre style='white-space:pre-wrap;background:#f4f4f4;padding:12px'>"+(al||"(alert 없음)")+"</pre></div>";
document.body.appendChild(d);return 1''')
        time.sleep(1.5)
        c.shot(T, str(out_dir / "result_tab.png"))
        ok = res.get("status") == 200 and not res.get("error")
        cm.emit(out, "SUBMITTED" if ok else "UNCERTAIN", "응답 확인" if ok else "응답 이상 — 재제출 금지, 확인 필요")

    cm.run(body, a, "신월곡1구역 네이밍 응모폼 — Codex 대체 없음(읽기만)")


if __name__ == "__main__":
    main()
