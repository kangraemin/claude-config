#!/usr/bin/env python3
"""[제출] 앱인토스 콘솔 — 인앱 결제 상품 1개 등록. 같은 이름 상품이 목록에 있으면 등록하지 않고 EXISTS만 출력.
약관 화면(디지털콘텐츠 위탁매매 약관)이 뜨면 --submit일 때 동의하고 진행한다(사용자 사전 동의 2026-10-22).

  ait_iap_create.py screw-toktok --type 소모품 --name "코인 한 줌" --desc "코인 1,200개" --price 1000 --image docs/store/iap/coins_s.png [--show] [--submit]
--price = 공급가(VAT 별도, 원). 판매가 = 공급가 x 1.1.
"""
import base64
import os
import sys
import time

from _ait import url, wait_page
from _common import emit, js, parser, poll, run, tab
import chromectl as c

ap = parser(__doc__, submit=True)
ap.add_argument("app")
ap.add_argument("--type", required=True, choices=["소모품", "비소모품", "자동 갱신 구독"])
ap.add_argument("--name", required=True)
ap.add_argument("--desc", default="")
ap.add_argument("--price", required=True, type=int)
ap.add_argument("--image", required=True)
ap.add_argument("--show", action="store_true", help="등록 후 바로 노출")
ap.add_argument("--min-version", default="", help="최소 지원 버전(예: 20261023-5). 비우면 목록의 가장 최신 버전")
ap.add_argument("--workspace", default="35273")
a = ap.parse_args()
# The console caps the description at 45 characters and blocks 등록하기 without saying so in the DOM (2026-10-22)
if a.desc and len(a.desc) > 45:
    sys.exit(f"RESULT: TOO_LONG 설명 {len(a.desc)}자 > 45자")
LIST = url(a.workspace, a.app, "in-app-purchase/list")
PRODUCTS = LIST + "?tab=products"
CREATE = url(a.workspace, a.app, "in-app-purchase/create")


def product_id(tid, name):
    """Product ID (ait.000…) of the product named `name` on the products tab, or None if it is not listed."""
    c.goto(tid, PRODUCTS)
    time.sleep(3)
    # products table header, or the empty state of an app with no products yet (2026-10-22 ssum-pandok: waiting only for the
    # header timed out on a brand-new app)
    st = poll(tid, "const t=document.body.innerText; return t.includes('업데이트 날짜') ? 'table' : t.includes('인앱 상품을 등록하고') ? 'empty' : null", 30)
    if st == "empty":
        return None
    time.sleep(3)
    if not js(tid, f"return !!__byText({name!r})"):
        return None
    c.press(tid, text=name)
    m = poll(tid, "const m=location.search.match(/inAppProductId=([\\w.]+)/); return m ? m[1] : null", 15)
    return m


def terms(tid):
    if "iap-terms" not in js(tid, "return location.href"):
        return
    if not a.submit:
        raise RuntimeError("TERMS_REQUIRED 디지털콘텐츠 위탁매매 약관 동의 필요 (--submit이면 동의)")
    js(tid, "const i=document.querySelector('input[type=checkbox]'); if(!i.checked) (i.closest('label')||i.parentElement).click(); return 1")
    time.sleep(1)
    c.press(tid, text="동의하고 시작하기")
    time.sleep(4)


def main():
    with tab(LIST, a) as tid:
        wait_page(tid, "인앱", 40)
        time.sleep(3)
        if "약관 확인하기" in js(tid, "return document.body.innerText"):
            c.press(tid, text="약관 확인하기")
            time.sleep(3)
            terms(tid)
            c.goto(tid, LIST)
            time.sleep(4)
        pid = product_id(tid, a.name)
        if pid:
            emit({"app": a.app, "name": a.name, "id": pid}, "EXISTS", a.name)
            print("IAP_EXISTS", a.app, a.name, pid)
            return
        c.goto(tid, CREATE)
        time.sleep(3)
        wait_page(tid, "상품 유형", 30)
        # Radix menu: opens on keyboard, not on a synthetic click.
        js(tid, "const b=document.querySelector('[role=combobox][aria-haspopup=menu]'); b.focus(); b.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true})); return 1")
        poll(tid, "return document.querySelector('[role=option]') ? 1 : null", 10)
        js(tid, f"""const o=[...document.querySelectorAll('[role=option]')].find(e=>e.innerText.trim().startsWith({a.type!r}));
          __press(o); return 1""")
        time.sleep(1)
        data = base64.b64encode(open(os.path.expanduser(a.image), "rb").read()).decode()
        r = js(tid, f"""const inp=document.querySelector('input[type=file]'); if(!inp) return 'NOFILEINPUT';
          const bin=atob({data!r}); const u=new Uint8Array(bin.length); for(let i=0;i<bin.length;i++) u[i]=bin.charCodeAt(i);
          const dt=new DataTransfer(); dt.items.add(new File([u], {os.path.basename(a.image)!r}, {{type:'image/png'}}));
          inp.files=dt.files; inp.dispatchEvent(new Event('input',{{bubbles:true}})); inp.dispatchEvent(new Event('change',{{bubbles:true}})); return 'OK'""", 60)
        if r != "OK":
            raise RuntimeError(f"image upload: {r}")
        time.sleep(3)
        c.fill(tid, "input[name=name]", a.name)
        if a.desc:
            c.fill(tid, "input[name=description]", a.desc)
        # The price field formats as you type ("1,000"), so compare digits only.
        r = js(tid, f"""const e=document.querySelector('input[name=price]'); e.focus();
          Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e, '{a.price}');
          e.dispatchEvent(new Event('input',{{bubbles:true}})); e.dispatchEvent(new Event('change',{{bubbles:true}})); e.blur();
          return e.value.replace(/\\D/g,'')""")
        if r != str(a.price):
            raise RuntimeError(f"price field shows {r}")
        time.sleep(1)
        # '최소 지원 버전' (required since 2026-10-23): Radix menu like 상품 유형; pick --min-version or the newest build listed
        mv = js(tid, "const b=[...document.querySelectorAll('[role=combobox][aria-haspopup=menu]')].find(e=>e.innerText.includes('선택하기')); if(!b) return 'NONE'; b.focus(); b.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true})); return 'OPEN'")
        if mv == "OPEN":
            poll(tid, "return document.querySelector('[role=option]') ? 1 : null", 10)
            mv = js(tid, f"""const os=[...document.querySelectorAll('[role=option]')]; const want={a.min_version!r};
              const o=want ? os.find(e=>e.innerText.trim()===want) : os.sort((x,y)=>y.innerText.trim().localeCompare(x.innerText.trim()))[0];
              if(!o) return 'NOTFOUND '+os.map(e=>e.innerText.trim()).join(','); __press(o); return o.innerText.trim()""")
            if mv.startswith("NOTFOUND"):
                raise RuntimeError(f"최소 지원 버전: {mv}")
            time.sleep(1)
        js(tid, f"""const boxes=[...document.querySelectorAll('input[type=checkbox]')];
          const show=boxes.find(b=>b.name==='postInspectionStatus'); const ok=boxes.find(b=>b.name!=='postInspectionStatus');
          if (show && show.checked !== {str(a.show).lower()}) (show.closest('label')||show.parentElement).click();
          if (ok && !ok.checked) (ok.closest('label')||ok.parentElement).click(); return 1""")
        time.sleep(1)
        st = js(tid, r"""const t=document.body.innerText; const b=[...document.querySelectorAll('button')].filter(__vis).find(e=>e.innerText.trim()==='등록하기');
          const opt=document.querySelector('[role=combobox][aria-haspopup=menu]');
          return {type: opt && opt.innerText.trim(), minVersion: (t.match(/최소 지원 버전\s*\n?\s*(\S+)/)||[])[1], sale: (t.match(/판매가\s*\n?\s*([\d,]+원)/)||[])[1], img: /1024/.test(t) && !document.querySelector('img[src^="blob:"],img[src^="http"]') ? 'maybe-missing' : 'ok',
                  name: document.querySelector('input[name=name]').value, price: document.querySelector('input[name=price]').value,
                  disabled: b ? (b.disabled || b.getAttribute('aria-disabled')==='true') : 'nobtn',
                  errors: [...document.querySelectorAll('[role=alert],[class*=error]')].filter(__vis).map(e=>e.innerText.trim()).filter(Boolean)}""")
        if not a.submit:
            emit(st, "DRY_RUN", "등록하기 안 누름")
            return
        if st.get("disabled") is not False:
            raise RuntimeError(f"등록하기 비활성: {st}")
        c.press(tid, text="등록하기")
        time.sleep(3)
        dlg = js(tid, "const d=[...document.querySelectorAll('[role=dialog],[role=alertdialog]')].filter(__vis).pop(); return d ? d.innerText : ''")
        if dlg:
            for label in ("등록하기", "확인", "등록"):
                if label in dlg:
                    js(tid, f"const d=[...document.querySelectorAll('[role=dialog],[role=alertdialog]')].filter(__vis).pop(); const b=[...d.querySelectorAll('button')].reverse().find(e=>e.innerText.trim()==={label!r}); if(b) __press(b); return 1")
                    break
        time.sleep(5)
        pid = product_id(tid, a.name)
        emit({"app": a.app, "name": a.name, "id": pid, "dialog": dlg[:300]}, "OK" if pid else "UNCONFIRMED", a.name)
        if pid:
            print("IAP_CREATED", a.app, a.name, pid)


run(main, a, f"앱인토스 콘솔 워크스페이스 {a.workspace} 앱 {a.app} → 수익화 > 인앱 결제 > 등록하기. 유형 {a.type}, 상품명 {a.name}, "
    f"설명 {a.desc}, 공급가 {a.price}원, 이미지 {a.image}. 같은 이름이 있으면 만들지 말고 목록만 읽어라.", cwd="/tmp")
