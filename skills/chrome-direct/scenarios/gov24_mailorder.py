#!/usr/bin/env python3
"""정부24 통신판매업 신고서를 채우고(기본은 제출 안 함) --submit 으로 낸다. 구매안전서비스 비적용대상 확인서도 강남구청 서식으로 만들어 붙인다.

  gov24_mailorder.py --out DIR            → 확인서 생성, 신청서 채움, 화면 캡처(DIR/v*.png), RESULT: READY. 제출 안 함
  gov24_mailorder.py --out DIR --submit   → READY 때 열어 둔 탭에서 '신청하기' 1번. 마지막 줄 RESULT: OK <접수번호>
- 사전 조건: 정부24 로그인. 풀렸으면 RESULT: NEEDS_LOGIN → gov24_status.py --match 통신판매업 --wait 600 으로 로그인 후 다시.
- 멱등: 취소가 아닌 통신판매업 신청이 목록(최근 4일)에 있으면 RESULT: ALREADY <접수번호>로 끝낸다.
- 함정 1 (10/28 취소): 소명 그림이 아니라 강남구청 법정서식 확인서에 사유 체크·소명·서명 필요.
- 함정 2 (11/3 취소): 이메일 '주소1/2' 칸만 채우면 숨은 합본 칸 '신청인/전자우편'이 비어 대표자 이메일 누락으로 취소됐다. 합본 칸도 넣고 확인한다.
- 함정 3: 기타 품목은 20자, 괄호 안 됨. 상세주소는 이벤트 없이 value만 넣어야 남는다. 주소 검색·처리기관·신청하기는 실제 클릭(rclick)만 먹는다.
- 값은 개인정보.md에서 패턴으로 읽고 출력하지 않는다. 왜 화면 조작인가: 정부24 민원 신청은 공개 API가 없다.
- Chrome Apple 이벤트와 ~/Documents 접근 때문에 tmux -L gh(또는 Ghostty)에서 돌린다.
"""
import argparse
import base64
import glob
import os
import re
import subprocess
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.expanduser("~/.claude/skills/chrome-direct"))
import chromectl as c  # noqa: E402

FORM = "https://www.gov.kr/mw/AA040OfferMainFrm.do?capp_biz_cd=11300000006&HighCtgCD=A01010001&tp_seq=01&Mcode=10200"
LIST = "https://plus.gov.kr/mypage/mbrAplySrvcList"
P = "통신판매업신고서/IN-통신판매업신고서/"
ITEM = "모바일게임 디지털콘텐츠"
DOMAIN = "Google Play, App Store, 토스"  # 서식 안내: 오픈마켓 판매는 판매처 이름을 쓰고 호스트서버 칸은 비운다
FID = "3dbb2fc4-f80b-4955-b720-0bd50aed61ff"
TABFILE = os.path.expanduser("~/.cache/gov24_mailorder.tab")
ADDR = r"(\S+구)\s+(\S+(?:로|길))\s*(\d+(?:-\d+)?)(?![0-9가-힣])"

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--out", required=True)
ap.add_argument("--submit", action="store_true")
ap.add_argument("--profile", default="Profile 1")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
JPG = os.path.join(a.out, "구매안전서비스_비적용대상확인서.jpg")


def result(status, note=""):
    print(f"RESULT: {status} {note}".rstrip())
    sys.exit(0 if status in ("OK", "READY", "ALREADY") else 1)


def person():
    root = sorted(glob.glob(os.path.expanduser("~/Documents/*/개인정보.md")))[0]
    t = open(root, encoding="utf-8").read()

    def g(k):
        m = re.search(r"^\s*-\s*" + k + r"[^:：\n]*[:：]\s*(.+)$", t, re.M)
        return re.sub(r"\*", "", m.group(1)).strip() if m else ""

    name = re.search(r"[가-힣]{2,5}", g("이름")).group(0)
    phone = re.sub(r"\D", "", re.search(r"01\d[-\d]{8,12}", g("휴대폰")).group(0))
    email = re.search(r"[\w.+-]+@[\w.-]+", g("이메일")).group(0)
    bz = re.search(r"(\d{3})-(\d{2})-(\d{5})", g("사업자번호")).groups()
    firm = re.search(r"[가-힣A-Za-z0-9]+", g("상호")).group(0)
    home = re.sub(r"\([^)]*\)", "", g("거주지")).strip()
    biz = re.sub(r"\([^)]*\)", "", g("사업장") or "").strip()
    if not re.search(ADDR, biz):
        biz = re.sub(r"\([^)]*\)", "", g("지점") + " " + g("우편"))
    hm, bm = re.search(ADDR, home), re.search(ADDR, biz)
    if not (hm and bm):
        result("FAIL", f"주소 패턴 실패 home={bool(hm)} biz={bool(bm)}")
    return dict(name=name, phone=phone, email=email, bz=bz, firm=firm, home=hm.groups(), home_d=home[hm.end():].strip(" ,"),
                biz=bm.groups(), biz_d=biz[bm.end():].strip(" ,"), sign=os.path.join(os.path.dirname(root), "서명_crop.png"))


def make_confirm(me):
    """강남구청 게시판 뷰어에서 서식 쪽 그림을 받아 제3호 체크·소명·이름·오늘 날짜·서명을 넣는다."""
    from PIL import Image, ImageDraw, ImageFont
    from playwright.sync_api import sync_playwright
    f = f"https://www.gangnam.go.kr/file/7/get/{FID}/download.do"
    u = "https://viewer.gangnam.go.kr/SynapDocViewServer/job?filePath=" + urllib.parse.quote(f, safe="") + f"&fid={FID}_7&convertType=1&fileType=URL&sync=true&downloadUrl=" + urllib.parse.quote(f, safe="")
    th, page = [], os.path.join(a.out, "page_hi.png")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 1700})
        pg.on("request", lambda r: th.append(r.url) if "/thumbnail/" in r.url else None)
        pg.goto(u, wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(2000)
        t2 = re.sub(r"h=1123", "h=2339", re.sub(r"w=794", "w=1654", re.sub(r"dpi=96", "dpi=200", th[0])))
        d = pg.evaluate("async(u)=>{const r=await fetch(u);const bl=await r.blob();return await new Promise(res=>{const fr=new FileReader();fr.onload=()=>res(fr.result);fr.readAsDataURL(bl)})}", t2)
        open(page, "wb").write(base64.b64decode(d.split(",")[1]))
        b.close()
    im = Image.open(page).convert("RGB")
    dr = ImageDraw.Draw(im)
    F, k = "/System/Library/Fonts/AppleSDGothicNeo.ttc", 1.17
    f40, fb, fs = ImageFont.truetype(F, 40, index=0), ImageFont.truetype(F, 40, index=6), ImageFont.truetype(F, 32, index=0)
    cx, cy = int(184 * k), int(631 * k)
    dr.line([(cx - 14, cy), (cx - 3, cy + 13), (cx + 18, cy - 18)], fill=(0, 0, 0), width=6)
    y = int(1168 * k)
    for L in [f"{me['firm']}는 모바일 게임 앱('오늘의 눈썰미', '강화 서바이버' 등)의 인앱 디지털",
              "콘텐츠를 Google Play·App Store·토스 앱의 앱마켓 결제로만 판매합니다. 구매 즉시",
              "앱 안에서 정보통신망으로 전송되어 제공되며, 실물 배송이 없어 제3자가 배송을",
              "확인할 수 없습니다. 따라서 위 해당사유 제3호의 거래에 해당합니다."]:
        dr.text((int(203 * k), y), L, font=fs, fill=(0, 0, 0))
        y += 46
    dr.text((int(410 * k), int(1352 * k)), me["name"], font=fb, fill=(0, 0, 0))
    now = time.localtime()
    for x, v in ((505, str(now.tm_year)), (680, str(now.tm_mon)), (815, str(now.tm_mday))):
        dr.text((int(x * k), int(1597 * k)), v, font=f40, fill=(0, 0, 0))
    s = Image.open(me["sign"]).convert("RGBA")
    s = s.resize((260, int(260 * s.height / s.width)))
    im.paste(s, (int(1150 * k) - s.width // 2, int(1712 * k) - s.height // 2), s)
    im.save(JPG, quality=92)


def front(t, tmp):
    c.shot(t, tmp)  # 탭을 앞으로
    subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'])
    time.sleep(1.2)


def real_click(t, sel=None, text=None):
    """화면 좌표 클릭이라 이 탭 창이 맨 앞일 때만 누른다(다른 세션 창에 떨어진 사고, 11/3). 안 맨 앞이면 RuntimeError."""
    for _ in range(12):
        front(t, os.path.join(a.out, "_f.png"))
        if c.run_js(t, "document.hasFocus()") in (True, "true"):
            c.rclick(t, sel, text)
            return
        time.sleep(3)
    raise RuntimeError("창을 맨 앞으로 못 가져옴")


def setv(t, name, v):
    c.run_js(t, "(()=>{const e=document.getElementsByName(%s)[0];e.value=%s;return 1})()" % (c.q(P + name), c.q(v)))


def pick_addr(t, btn, gu, road, num):
    w = []
    for x in c.tabs(with_id=True):  # 남은 팝업에 다음 주소가 들어가지 않게 닫는다
        if x[2] == "주소검색":
            c.close_tab("id:" + x[4])
    for _ in range(3):
        real_click(t, "#" + btn)
        time.sleep(4)
        w = [x for x in c.tabs(with_id=True) if x[2] == "주소검색"]
        if w:
            break
    if not w:
        result("FAIL", "주소 팝업 안 뜸(팝업 차단 확인)")
    W = "id:" + w[0][4]
    c.run_js(W, "document.getElementById('txtRoad').value=%s;[...document.querySelectorAll('button')].find(b=>b.innerText.trim()=='검색').click();1" % c.q(f"{gu} {road} {num}"))
    time.sleep(4)
    r = c.js_json(W, """const k=%s;const a=[...document.querySelectorAll('a')].filter(e=>/도로명/.test(e.innerText));
      const ok=a.filter(e=>{const s=e.innerText.split('지번')[0];const i=s.indexOf(k);return i>=0&&!/[0-9-]/.test(s[i+k.length]||'')});
      if(ok.length==1)ok[0].click();return {n:a.length,ok:ok.length}""" % c.q(f"{gu} {road} {num}"))
    if r["ok"] != 1:
        result("FAIL", f"주소 결과 {r}")
    time.sleep(4)
    for _ in range(5):  # 처리기관 클릭이 다른 창에 떨어지면 팝업이 남고, 다음 주소가 이 팝업으로 들어가 소재지를 덮어쓴다(11/3)
        if not [x for x in c.tabs(with_id=True) if x[2] == "주소검색"]:
            return
        office = c.js_json(W, "return [...document.querySelectorAll('a')].filter(e=>/areaSelected/.test((e.getAttribute('href')||'')+(e.getAttribute('onclick')||''))).map(e=>e.innerText.trim())")
        if office:
            real_click(W, text=office[0])
        time.sleep(4)
    result("FAIL", "주소 팝업이 안 닫힘")


def upload(t):
    b64 = base64.b64encode(open(JPG, "rb").read()).decode()
    c.run_js(t, "window.__cu=[];1")
    for i in range(0, len(b64), 300000):
        c.run_js(t, f"window.__cu.push({c.q(b64[i:i+300000])});1", 60)
    r = c.run_js(t, """(()=>{const s=atob(window.__cu.join(''));window.__cu=null;const u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);
      const d=document.getElementById('dext5uploader_frame_comp0').contentDocument;const e=d.querySelector('input[type=file]');if(!e)return 'noinput';
      const dt=new DataTransfer();dt.items.add(new File([u],'구매안전서비스_비적용대상확인서.jpg',{type:'image/jpeg'}));e.files=dt.files;
      e.dispatchEvent(new Event('change',{bubbles:true}));return 'ok'})()""", 120)
    if r != "ok":
        result("FAIL", f"첨부 {r}")
    time.sleep(2)


def existing(t):
    c.goto(t, LIST)
    time.sleep(6)
    txt = c.run_js(t, "document.body.innerText")
    if "로그인이 필요한" in txt or "회원 로그인 상태" not in txt:
        result("NEEDS_LOGIN", "gov24_status.py 로 로그인 후 다시")
    return re.findall(r"(\d{8}-\d+)\s*\[[^\]]*\]\s*(?:민원 사무명\s*)?통신판매업신고[^\n]*[\s\S]*?처리상태\s*(?:툴팁 열기\s*)?([^\n]+)", txt), txt


def fill(t, me):
    c.goto(t, FORM)
    time.sleep(8)
    c.js_json(t, "const l=[...document.querySelectorAll('label')].find(e=>(e.innerText||'').includes('유의사항을 모두 확인'));if(l)l.click();return !!l")
    c.press(t, text="다음으로")
    time.sleep(4)
    if not c.js_json(t, "const e=document.getElementById('busiAddBtn');return !!(e&&e.getBoundingClientRect().width)"):
        result("FAIL", "2단계 안 열림")
    upload(t)
    u, d = me["email"].split("@")
    ph = me["phone"]
    vals = {"신청인/법인명": me["firm"], "신청인/사업자등록번호/앞번호": me["bz"][0], "신청인/사업자등록번호/중간번호": me["bz"][1], "신청인/사업자등록번호/뒷번호": me["bz"][2],
            "신청인/법인전화번호/지역번호": ph[:3], "신청인/법인전화번호/국번": ph[3:7], "신청인/법인전화번호/번호": ph[7:],
            "신청인/전자우편/주소1": u, "신청인/전자우편/주소2": d, "신청인/전자우편": me["email"], "신청인/도메인명": DOMAIN, "참고사항/취급품목기타": ITEM}
    c.js_json(t, """const P=%s;document.querySelectorAll('input[type=checkbox]').forEach(e=>{if(!e.name.startsWith(P))return;const lb=(e.closest('label')||document.querySelector('label[for="'+e.id+'"]')||{}).innerText||'';
      if(((/판매방식/.test(e.name)&&/인터넷/.test(lb+e.value))||(/취급품목$/.test(e.name)&&/기타/.test(lb+e.value)))&&!e.checked)e.click()});return 1""" % c.q(P))
    time.sleep(1)
    for k, v in vals.items():
        setv(t, k, v)
    pick_addr(t, "busiAddBtn", *me["biz"])
    c.run_js(t, "(()=>{const a=[...document.querySelectorAll('a.mw_btn')].filter(e=>(e.getAttribute('onclick')||'').includes('신청인주소'));if(a[0])a[0].id='homeAddBtn';return a.length})()")
    pick_addr(t, "homeAddBtn", *me["home"])
    setv(t, "신청인/소재지/특수지주소/특수지명", me["biz_d"])
    setv(t, "신청인/신청인주소/특수지주소/특수지명", me["home_d"])
    for k, v in vals.items():  # 주소 선택이 값을 건드렸을 수 있어 한 번 더
        if k.startswith("신청인/전자우편"):
            setv(t, k, v)


def check(t, me):
    r = c.js_json(t, """const P=%s;const g=n=>(document.getElementsByName(P+n)[0]||{}).value||'';const d=document.getElementById('dext5uploader_frame_comp0').contentDocument;
      const need=['신청인/법인명','신청인/사업자등록번호/뒷번호','신청인/법인전화번호/번호','신청인/소재지/지역정보/지역명','신청인/소재지/특수지주소/특수지명','신청인/전화번호/뒷번호','신청인/신청인주소/지역정보/지역명','신청인/신청인주소/특수지주소/특수지명','신청인/전자우편/주소1','신청인/전자우편/주소2','신청인/도메인명','참고사항/취급품목기타'];
      return {empty:need.filter(n=>!g(n)),mail:g('신청인/전자우편/주소1')+'@'+g('신청인/전자우편/주소2')==%s,mailAll:g('신청인/전자우편')==%s,
      dept:(document.getElementsByName(P.split('/')[0]+'/COMMON-INFO/TRANSMISSION-RECEPTION/ISSUE-ORG/DEPARTMENT')[0]||{}).value||'',
      cb:[...document.querySelectorAll('input[type=checkbox]')].filter(e=>e.checked&&e.name.startsWith(P)).map(e=>e.value),
      up:(d.body.innerText.match(/\\d+ 개, [^\\n]+추가됨/)||[''])[0],
      mailHandlers:['주소1','주소2'].map(s=>{const e=document.getElementsByName(P+'신청인/전자우편/'+s)[0];return e?[e.type,e.getAttribute('onchange'),e.getAttribute('onblur')]:null})}""" % (c.q(P), c.q(me["email"]), c.q(me["email"])))
    print("CHECK", r)
    if "강남구" not in r["dept"] or r["empty"] or not r["mail"] or not r["mailAll"] or not r["up"].startswith("1 ") or not set(["인터넷", "기타"]) <= set(r["cb"]):
        result("FAIL", "신청서 값 확인 실패")
    return r


def shots(t):
    """신청서 위부터 끝까지 한 화면씩 캡처(v00.png~). 다른 세션이 창을 띄우면 다른 창이 찍히므로 찍기 전후 포커스를 본다."""
    H = c.js_json(t, "return [document.documentElement.scrollHeight, innerHeight]")
    focused = lambda: c.js_json(t, "return document.hasFocus()&&document.visibilityState=='visible'")
    for i, y in enumerate(range(0, H[0], max(H[1] - 80, 300))):
        c.run_js(t, f"window.scrollTo(0,{y});1")
        out = os.path.join(a.out, f"v{i:02d}.png")
        for _ in range(10):
            try:  # 다른 세션이 창·탭을 여닫으면 Apple 이벤트가 -1728로 실패한다
                front(t, out + ".tmp.png")
                if not focused():
                    continue
                x1, y1, x2, y2 = c.window_bounds()
                subprocess.run(["screencapture", "-x", "-R", f"{x1},{y1},{x2-x1},{y2-y1}", out], check=True)
                if focused():
                    break
            except RuntimeError:
                time.sleep(2)
        else:
            raise SystemExit(f"RESULT: FAIL 신청서 화면 캡처 실패 {i}")


def submit(t, me):
    check(t, me)
    c.run_js(t, "(()=>{const b=[...document.querySelectorAll('a,button')].find(e=>e.innerText.trim()=='신청하기'&&e.getBoundingClientRect().width>0);b.id='submitBtnX';return 1})()")
    real_click(t, "#submitBtnX")  # 두 번 접수되면 안 되므로 자동 재시도 없음
    for _ in range(40):
        time.sleep(3)
        title = c.run_js(t, "document.title")
        if "신청 내역" in title:
            break
    else:
        err = c.run_js(t, "[...document.querySelectorAll('p[id$=-error]')].filter(e=>e.getBoundingClientRect().width>0).map(e=>e.id+':'+e.innerText).join(', ')")
        c.shot(t, os.path.join(a.out, "post.png"))
        result("FAIL", f"제출 뒤 화면 안 바뀜(재클릭 금지, 화면 확인) err={err}")
    rows, _ = existing(t)
    live = [n for n, s in rows if "취소" not in s]
    if live:
        result("OK", live[0])
    result("FAIL", "제출 뒤 목록에서 접수번호 못 찾음(재제출 금지, 목록 확인)")


def main():
    me = person()
    if a.submit:
        t = open(TABFILE).read().strip()
        submit(t, me)
    t = c.new_tab(LIST, profile=a.profile)
    try:
        rows, _ = existing(t)
        print("LIST", rows)
        live = [n for n, s in rows if "취소" not in s]
        if live:
            result("ALREADY", live[0])
        make_confirm(me)
        fill(t, me)
        check(t, me)
        shots(t)
        open(TABFILE, "w").write(t)
        print("TAB kept for --submit")
        result("READY", a.out)
    except SystemExit as e:
        if e.code:
            c.close_tab(t)
        raise


main()
