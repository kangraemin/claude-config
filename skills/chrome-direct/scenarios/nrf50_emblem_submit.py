#!/usr/bin/env python3
"""한국연구재단 창립 50주년 엠블럼 공모전(event.dcafein.com/2026-nrf50-emblem) 접수·조회.

  lookup  : /lookup 에서 성명+휴대전화로 접수 상태 조회(이미 냈는지 확인, 캡처)
  entry   : /entry 칸 채우기 — 연령(만 19세 이상)·성명·휴대전화·이메일·작품명·엠블럼 파일·작품설명서·필수 동의 4개.
            기본 dry-run(채우고 캡처). --submit 이면 먼저 lookup 해서 이미 있으면 ALREADY, 없으면 '작품 제출하기' 1회.
  honeypot 칸 ev_check 는 비워 둔다. 값(이름·번호·메일)은 출력하지 않는다.

사용: python3 nrf50_emblem_submit.py lookup --info ~/Documents/oguri-works/개인정보.md --shot-dir out/
      python3 nrf50_emblem_submit.py entry --info ... --title 작품명 --work a.pdf --desc b.pdf --shot-dir out/ [--submit]
      김은미: --info ~/Documents/oguri-works/개인정보-김은미.md --profile "Profile 16"
마지막 줄: RESULT: FOUND | NOT_FOUND | DRYRUN | SUBMITTED | ALREADY | FAIL <이유>
"""
import argparse, json, os, re, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import chromectl as c

BASE = "https://event.dcafein.com/2026-nrf50-emblem"


def info(path):
    t = open(os.path.expanduser(path), encoding="utf-8").read()
    g = lambda k: re.search(r"^- " + k + r"[^:]*:\s*(.+)$", t, re.M).group(1).strip().strip("`")
    name = g("이름").split(" (")[0].split("(")[0].strip()
    phone = re.sub(r"\D", "", g("휴대"))
    mail = re.search(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", g("이메일")).group(0)
    phone = f"{phone[:3]}-{phone[3:7]}-{phone[7:]}" if len(phone) == 11 else phone
    return name, phone, mail


SET = """const set=(sel,v)=>{const e=document.querySelector(sel); const p=Object.getPrototypeOf(e);
  Object.getOwnPropertyDescriptor(p,'value').set.call(e,v); e.dispatchEvent(new Event('input',{bubbles:true}));
  e.dispatchEvent(new Event('change',{bubbles:true})); e.dispatchEvent(new Event('blur',{bubbles:true}));};"""


def lookup(tab, name, phone, shot):
    c.goto(tab, BASE + "/lookup")
    c.wait(tab, sel="#lookupName", timeout=30)
    c.js_json(tab, SET + f"""const r=document.querySelector("input[name=lookup_by]"); r.click();
      set('#lookupName',{c.q(name)}); set('#lookupPhone',{c.q(phone)}); return 1""")
    c.run_js(tab, "(() => { const b=[...document.querySelectorAll('button[type=submit]')].find(b=>b.innerText.includes('조회')); b.click(); return 1; })()")
    time.sleep(4)
    txt = c.page_text(tab)
    if shot:  # 증거 캡처엔 성명·번호를 가린다(입력칸 값·결과 글자)
        c.js_json(tab, f"""for (const e of document.querySelectorAll('#lookupName,#lookupPhone')) e.value='●●●';
          const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT); let n;
          while((n=w.nextNode())) n.nodeValue=n.nodeValue.split({c.q(name)}).join('●●●').split({c.q(phone)}).join('010-●●●●-●●●●');
          return 1""")
        c.shot(tab, shot)
    body = txt.split("조회하기", 1)[-1][:800]
    # 안내문에 '찾지 못하면'이 늘 있어 그걸로 판정하지 않는다(11/16 FOUND를 NOT_FOUND로 오판)
    found = bool(re.search(r"NRF50-\d{4}-\d+|접수 완료|확인 대기", body)) and "일치하는 접수가 없습니다" not in body
    return found, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["lookup", "entry"])
    ap.add_argument("--info", required=True)
    ap.add_argument("--profile", default="Profile 1")
    ap.add_argument("--title")
    ap.add_argument("--work")
    ap.add_argument("--desc")
    ap.add_argument("--shot-dir", required=True)
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--keep-tab", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.shot_dir, exist_ok=True)
    name, phone, mail = info(a.info)
    tab = c.new_tab(BASE + "/lookup", profile=a.profile, timeout=25)
    try:
        if a.mode == "lookup":
            found, body = lookup(tab, name, phone, os.path.join(a.shot_dir, "lookup.png"))
            print("LOOKUP", json.dumps(body.replace(name, "<성명>").replace(phone, "<번호>")[:500], ensure_ascii=False))
            print("RESULT: FOUND" if found else "RESULT: NOT_FOUND"); return 0
        for f in (a.work, a.desc):
            if not f or not os.path.isfile(f):
                print(f"RESULT: FAIL 파일 없음 {f}"); return 1
        if os.path.getsize(a.work) > 20 * 1024 * 1024 or os.path.getsize(a.desc) > 5 * 1024 * 1024:
            print("RESULT: FAIL 용량 초과(엠블럼 20MB·설명서 5MB)"); return 1
        if a.submit:
            found, body = lookup(tab, name, phone, os.path.join(a.shot_dir, "lookup-before.png"))
            if found:
                print("LOOKUP", json.dumps(body.replace(name, "<성명>").replace(phone, "<번호>")[:300], ensure_ascii=False))
                print("RESULT: ALREADY 이미 접수 기록 있음"); return 2
        c.goto(tab, BASE + "/entry")
        c.wait(tab, sel="#ef-name", timeout=30)
        time.sleep(1)
        c.js_json(tab, SET + f"""
          const ages=[...document.querySelectorAll("input[name='f[age]']")];
          const adult=ages.find(e=>(e.closest('label')||e.parentElement).innerText.includes('만 19세 이상'))||ages[0]; adult.click();
          set('#ef-name',{c.q(name)}); set('#ef-phone',{c.q(phone)}); set('#ef-email',{c.q(mail)}); set('#ef-work_title',{c.q(a.title)});
          return 1""")
        for sel, f in (("#ef-work_file", a.work), ("#ef-desc_file", a.desc)):
            r = c.upload_file(tab, os.path.abspath(f), selector=sel)
            if not str(r).startswith("ok"):
                print(f"RESULT: FAIL 파일 넣기 실패 {sel} {r}"); return 1
        c.js_json(tab, """for (const id of ['ec-agree_rules','ec-agree_original','ec-agree_copyright','entryAgree']) {
            const e=document.getElementById(id); if(!e.checked) e.click(); } return 1""")
        time.sleep(1)
        st = c.js_json(tab, """const v=s=>document.querySelector(s);
          const age=[...document.querySelectorAll("input[name='f[age]']")].find(e=>e.checked);
          const f=s=>v(s).files[0]?[v(s).files[0].name,v(s).files[0].size]:null;
          return {age:age?(age.closest('label')||age.parentElement).innerText.trim():null, name:!!v('#ef-name').value,
            phone:/^010-\\d{4}-\\d{4}$/.test(v('#ef-phone').value), mail:v('#ef-email').value.includes('@'), title:v('#ef-work_title').value,
            work:f('#ef-work_file'), desc:f('#ef-desc_file'), honeypot:v("input[name=ev_check]").value,
            agrees:['ec-agree_rules','ec-agree_original','ec-agree_copyright','entryAgree'].map(i=>document.getElementById(i).checked)}""")
        print("FILLED", json.dumps(st, ensure_ascii=False))
        ok = (st["age"] and "19세 이상" in st["age"] and st["name"] and st["phone"] and st["mail"] and st["title"] == a.title
              and st["work"] and st["work"][0] == os.path.basename(a.work) and st["desc"] and st["desc"][0] == os.path.basename(a.desc)
              and st["honeypot"] == "" and all(st["agrees"]))
        c.run_js(tab, "(() => { const b=[...document.querySelectorAll('button[type=submit]')].find(b=>b.innerText.includes('작품 제출')); b.scrollIntoView({block:'center'}); return 1; })()")
        c.shot(tab, os.path.join(a.shot_dir, "entry-filled.png"))
        if not ok:
            print("RESULT: FAIL 칸·파일·동의 확인 안 됨"); return 1
        if not a.submit:
            print("RESULT: DRYRUN"); return 0
        # confirm 창은 자동 승인, alert 문구는 기록
        c.run_js(tab, """(() => { localStorage.setItem('__nrf_log','[]'); const s=document.createElement('script'); s.textContent=`(function(){
          const L=m=>{const a=JSON.parse(localStorage.getItem('__nrf_log')||'[]'); a.push(m); localStorage.setItem('__nrf_log',JSON.stringify(a));};
          window.confirm=m=>{L('confirm:'+m); return true;}; window.alert=m=>{L('alert:'+m);};})();`;
          document.documentElement.appendChild(s); s.remove(); return 1; })()""")
        c.run_js(tab, "(() => { const b=[...document.querySelectorAll('button[type=submit]')].find(b=>b.innerText.includes('작품 제출')); b.click(); return 1; })()")
        end = time.time() + 120
        txt = ""
        while time.time() < end:
            time.sleep(3)
            try:
                txt = c.page_text(tab)
            except Exception:
                continue
            if re.search(r"접수번호|접수가 완료|접수 완료|제출되었|완료되었", txt):
                break
        log = c.js_json(tab, "return localStorage.getItem('__nrf_log')")
        url = c.js_json(tab, "return location.href")
        c.shot(tab, os.path.join(a.shot_dir, "entry-done.png"))
        safe = txt.replace(name, "<성명>").replace(phone, "<번호>").replace(mail, "<메일>")
        m = re.search(r"접수번호\s*[:：]?\s*([A-Za-z0-9-]{4,})", safe)
        print("DONE", json.dumps({"url": url, "log": log, "receipt": m.group(1) if m else None,
                                  "text": safe.split("작품 접수", 1)[-1][:600]}, ensure_ascii=False))
        print(f"RESULT: SUBMITTED {m.group(1)}" if m else "RESULT: FAIL 완료 화면 확인 안 됨 — 재제출 말고 lookup으로 확인")
        return 0 if m else 1
    finally:
        if not a.keep_tab:
            try:
                c.close_tab(tab)
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
