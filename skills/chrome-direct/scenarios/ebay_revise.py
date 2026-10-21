#!/usr/bin/env python3
"""[제출] eBay(호주) 판매 중 상품의 제목·상품 속성(item specifics)·광고(Promoted General)비를 고친다.

  ebay_revise.py <itemId> [--title T] [--attr "Features=Squeaky"]... [--ad-rate 3] [--submit]

- 수정 화면 /sl/list?mode=ReviseItem&itemId=<id> (→ /lstng?draftId=..) 에서 고친다.
  - 제목: input[name=title] (80자 제한, 넘으면 중단).
  - 속성: button[name="attributes.<이름>"] 를 누르면 메뉴가 열린다. 보기는 div[role=menuitemcheckbox].
    보기에 없는 값은 input[name="search-box-attributes<이름 공백제거>"] 에 쳐서 Enter 로 직접 넣는다.
    여러 값 칸(Features 등)은 더해지고, 한 값 칸은 바뀐다.
  - 광고: checkbox[name="Toggle General"] 켜기 → input[name=adRate] 에 % 숫자. 켜면 새 캠페인이 자동 생성된다.
- 멱등: 이미 같은 제목·값·광고비면 건드리지 않는다. 바뀐 게 없으면 저장도 안 한다.
- --submit 이 없으면 바꿀 내용만 출력하고 저장하지 않는다(초안은 버려진다).
- 왜 화면 조작인가: 개인 셀러 API 키가 없다. 로그인은 ebay_listings.py docstring 참고.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/.config/claude-accounts/personal/skills/chrome-direct"))
import chromectl as c  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("item")
ap.add_argument("--title")
ap.add_argument("--attr", action="append", default=[])
ap.add_argument("--ad-rate")
ap.add_argument("--submit", action="store_true")
ap.add_argument("--profile", default="Profile 1")
a = ap.parse_args()
if a.title and len(a.title) > 80:
    sys.exit(f"RESULT: FAIL title {len(a.title)}자 > 80")


def J(body):
    return c.js_json(t, body)


def menu_state(name):
    """열린 속성 메뉴의 (선택값, 전체 보기)."""
    return J(f"""const b=document.querySelector('[name="attributes.{name}"]');let p=b;for(let i=0;i<8&&p&&!p.querySelector('[role=menuitemcheckbox]');i++)p=p.parentElement;
      const it=[...(p||document).querySelectorAll('[role=menuitemcheckbox]')];
      return {{sel:it.filter(e=>e.getAttribute('aria-checked')=='true').map(e=>e.innerText.trim()),all:it.map(e=>e.innerText.trim())}}""")


def close_menu(name):
    box = f"search-box-attributes{name.replace(' ', '')}"
    J(f"""const e=document.querySelector('[name="{box}"]');if(e&&e.offsetParent)document.querySelector('[name="attributes.{name}"]').click();return 1""")
    time.sleep(1)


t = c.new_tab(f"https://www.ebay.com.au/sl/list?mode=ReviseItem&itemId={a.item}", profile=a.profile)
changes = []
try:
    time.sleep(10)
    if "signin" in J("return location.href"):
        print("RESULT: BLOCKED 로그아웃 상태")
        sys.exit()
    c.shot(t, "/tmp/ebay_revise.png")  # 탭을 앞으로 띄워 렌더링
    if a.title:
        cur = J("return document.querySelector('[name=title]').value")
        if cur != a.title:
            c.fill(t, "[name=title]", a.title)
            changes.append(f"title: {cur} -> {a.title}")
    for kv in a.attr:
        name, val = kv.split("=", 1)
        box = f"[name='search-box-attributes{name.replace(' ', '')}']"
        cur = J(f"""const b=document.querySelector('[name="attributes.{name}"]');return b?b.innerText.trim():null""")
        if cur is None:
            print(f"skip {name}: 칸 없음")
            continue
        if cur == val:  # 한 값 칸은 현재 값이 버튼 글자로 보인다
            continue
        for _ in range(4):  # 메뉴가 열렸는지는 검색칸이 보이는지로 판단(aria-expanded 가 늦게 바뀐다)
            if J(f"""const e=document.querySelector("{box}");return !!(e&&e.offsetParent)"""):
                break
            J(f"""const b=document.querySelector('[name="attributes.{name}"]');b.scrollIntoView({{block:'center'}});b.click();return 1""")
            time.sleep(1.5)
        st = menu_state(name) or {"sel": [], "all": []}
        if val in st["sel"]:
            close_menu(name)
            continue
        if val in st["all"]:
            J(f"""const b=document.querySelector('[name="attributes.{name}"]');let p=b;for(let i=0;i<8&&!p.querySelector('[role=menuitemcheckbox]');i++)p=p.parentElement;
              [...p.querySelectorAll('[role=menuitemcheckbox]')].find(e=>e.innerText.trim()=={val!r}).click();return 1""")
        else:
            c.fill(t, box, val)
            time.sleep(1)
            J(f"""const e=document.querySelector("{box}");for(const ty of ['keydown','keypress','keyup'])e.dispatchEvent(new KeyboardEvent(ty,{{key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true}}));return 1""")
        time.sleep(1.5)
        st2 = menu_state(name) or {"sel": []}
        ok = val in st2["sel"] or val in J(f"""return document.querySelector('[name="attributes.{name}"]').innerText""")
        changes.append(f"{name} += {val} ({'OK' if ok else 'FAIL'})")
        close_menu(name)
    if a.ad_rate:
        r = J(f"""const g=document.querySelector('[name="Toggle General"]');g.scrollIntoView({{block:'center'}});if(!g.checked)g.click();return g.checked""")
        time.sleep(2)
        cur = J("return (document.querySelector('[name=adRate]')||{}).value")
        if cur != a.ad_rate:
            c.fill(t, "[name=adRate]", a.ad_rate)
            changes.append(f"adRate: {cur} -> {a.ad_rate} (General={r})")
    for x in changes:
        print(" -", x)
    if not changes:
        print("RESULT: SKIP 바꿀 것 없음")
        sys.exit()
    if not a.submit:
        print("RESULT: DRY-RUN (저장 안 함)")
        sys.exit()
    btn = J("""const b=[...document.querySelectorAll('button')].filter(b=>b.offsetParent&&/^(Revise it|Save)$/.test(b.innerText.trim()));const x=b.find(b=>b.innerText.trim()=='Revise it')||b[0];if(!x)return '';x.scrollIntoView({block:'center'});setTimeout(()=>x.click(),10);return x.innerText.trim()""")
    print("clicked:", btn)
    time.sleep(10)
    url = J("return location.href")
    body = J("return document.body.innerText.slice(0,400)").replace("\n", " / ")
    print("after:", url, "|", body[:300])
    ok = "Your listing has been revised" in body
    err = "" if ok else J("""return [...document.querySelectorAll('.field__error,.textbox__error,[role=alert]')].filter(e=>e.offsetParent).map(e=>e.innerText.trim()).filter(Boolean).join(' | ')""")
    print(f"RESULT: {'OK' if ok else 'FAIL ' + err} {a.item}")
finally:
    c.close_tab(t)
