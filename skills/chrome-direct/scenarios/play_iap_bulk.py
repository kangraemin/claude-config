"""Usage: play_iap_bulk.py korea-info [--submit] | bulk <store-build.md> [--submit] [--only id,id]

Play Console 인앱(일회성 제품) 일괄 등록. Pre: Chrome Profile 1 = remin1994 (Play 개발자 8396615316670096970), 앱 4973170760525515872.
korea-info : 계정 > 내 정보의 '한국 개발자 추가 정보'(사업자 등록 번호·전자상거래 라이선스 번호·대행사)를 읽고,
             환경변수 PLAY_BRN / PLAY_MAIL_NO / PLAY_MAIL_AGENCY 가 있으면 채워 저장(--submit). 값은 출력하지 않는다(길이만).
bulk       : store-build.md '인앱 상품 등록 표'를 읽어 one-time-products/create 마다 id/이름/설명 → 구매 옵션 → 가격(KRW) → 활성화.
Gotcha(2026-10-31): 세 칸이 비면 저장·활성화가 모두 "변경사항을 저장할 수 없습니다."로 실패하고 초안도 안 남는다. 면제/해당 없음 선택지 없음.
        통신판매업 신고는 정부24 처리 완료(번호 발급) 뒤에만 가능 → gov24_status.py --match 통신판매업 로 확인.
        계정은 이미 '조직'(D-U-N-S 인증), 프로덕션 접근은 12명 테스트 요건 없음.
        bulk 폼 구간은 미검증. 실제 상품 등록은 play_iap_create.py(2026-11-06 검증)를 쓴다.
RESULT: KOREA_INFO_OK | KOREA_INFO_EMPTY:<칸> | SAVE_FAILED | BULK_DONE n/m
"""
import json, os, re, sys, time
sys.path.insert(0, os.path.expanduser("~/.claude/skills/chrome-direct"))
import chromectl as c

DEV = "8396615316670096970"; APP = "4973170760525515872"
BASE = f"https://play.google.com/console/u/0/developers/{DEV}"
CLICK = "for(const k of ['pointerdown','mousedown','pointerup','mouseup','click'])E.dispatchEvent(new MouseEvent(k,{bubbles:true,cancelable:true,view:window}));"
SET = ("const set=(P,el,v)=>{el.focus();Object.getOwnPropertyDescriptor(P.prototype,'value').set.call(el,v);"
       "for(const k of ['input','change','blur'])el.dispatchEvent(new Event(k,{bubbles:true}));};")

def goto(tab, url, wait=8):
    c.js_json(tab, f"location.href={json.dumps(url)};return 1")
    time.sleep(wait)

def btn(tab, text):
    return c.js_json(tab, "const E=[...document.querySelectorAll('button,[role=button]')].filter(x=>x.offsetParent&&(x.innerText||'').trim()=="
                     + json.dumps(text) + "&&!x.disabled)[0];if(!E)return 'none';" + CLICK + "return 'ok'")

def korea_info(tab, submit):
    goto(tab, f"{BASE}/account/developer-details?tab=aboutYou")
    labels = {"사업자 등록 번호": "PLAY_BRN", "전자상거래 라이선스 번호": "PLAY_MAIL_NO", "전자상거래 라이선스 대행사": "PLAY_MAIL_AGENCY"}
    empty = []
    for lab, env in labels.items():
        v = os.environ.get(env)
        cur = c.js_json(tab, "return ([...document.querySelectorAll('input')].find(x=>x.getAttribute('aria-label')==" + json.dumps(lab) + ")||{value:''}).value.length")
        if v and cur == 0:
            c.js_json(tab, SET + "const i=[...document.querySelectorAll('input')].find(x=>x.getAttribute('aria-label')==" + json.dumps(lab) + ");set(HTMLInputElement,i," + json.dumps(v) + ");return 1")
        elif cur == 0:
            empty.append(lab)
    if empty:
        print("RESULT: KOREA_INFO_EMPTY:" + ",".join(empty)); return 2
    if not submit:
        print("RESULT: KOREA_INFO_OK (dry-run)"); return 0
    btn(tab, "변경사항 저장"); time.sleep(4)
    bad = c.js_json(tab, "return document.body.innerText.includes('변경사항을 저장할 수 없습니다')")
    print("RESULT: " + ("SAVE_FAILED" if bad else "KOREA_INFO_OK")); return 1 if bad else 0

def parse_table(md):
    rows = []
    for l in open(md, encoding="utf-8"):
        m = re.match(r"\|\s*([a-z0-9_]+)\s*\|\s*([^|]+?)\s*\|\s*(비소모품|소모품)\s*\|\s*([\d,]+)\s*\|", l)
        if m: rows.append((m[1], m[2], m[3], int(m[4].replace(",", ""))))
    return rows

def bulk(tab, md, submit, only):
    rows = [r for r in parse_table(md) if not only or r[0] in only]
    done = 0
    for pid, name, kind, krw in rows:
        goto(tab, f"{BASE}/app/{APP}/one-time-products/create")
        c.js_json(tab, SET + "const ins=[...document.querySelectorAll('input[type=text]')].filter(x=>x.offsetParent);"
                  f"set(HTMLInputElement,ins[0],{json.dumps(pid)});set(HTMLInputElement,ins[2],{json.dumps(name)});"
                  f"set(HTMLTextAreaElement,document.querySelector('textarea'),{json.dumps(name)});return 1")
        btn(tab, "다음"); time.sleep(3)
        # 단계2: 구매 옵션 ID / 가격 일괄 수정(KRW) -> 활성화 (notes.md 순서, 첫 상품에서 검증 필요)
        c.js_json(tab, SET + "const i=[...document.querySelectorAll('input[type=text]')].filter(x=>x.offsetParent)[0];if(i)set(HTMLInputElement,i," + json.dumps(pid.replace('_', '-')) + ");return 1")
        print(f"{pid}: filled (price {krw} KRW은 화면에서 가격 일괄 수정 필요 — 미구현 구간)")
        if not submit: continue
        btn(tab, "활성화"); time.sleep(4)
        bad = c.js_json(tab, "return document.body.innerText.includes('변경사항을 저장할 수 없습니다')")
        if bad: print("RESULT: SAVE_FAILED at " + pid); return 1
        done += 1
    print(f"RESULT: BULK_DONE {done}/{len(rows)}"); return 0

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args: print(__doc__); sys.exit(1)
    submit = "--submit" in args
    tab = c.new_tab(f"{BASE}/home", profile="Profile 1")
    try:
        if args[0] == "korea-info": rc = korea_info(tab, submit)
        else:
            only = args[args.index("--only") + 1].split(",") if "--only" in args else None
            rc = bulk(tab, args[1], submit, only)
    finally:
        c.close_tab(tab)
    sys.exit(rc)
