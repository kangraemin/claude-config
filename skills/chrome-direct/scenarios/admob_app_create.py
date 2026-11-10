"""Usage: admob_app_create.py <앱이름> --platform Android|iOS [--platform ...] [--unit hint_rewarded --reward-item hint --reward-amount 1] [--dry-run]

AdMob(remin1994, pub-4785237655148075)에 앱(스토어 미등록 '아니요')과 보상형 광고 단위를 만든다. 이미 있으면 새로 만들지 않고 ID만 출력(멱등).
Pre: Chrome Profile 1 구글 로그인(google_relogin이 처리), AdMob 계정 '승인됨'. --dry-run이면 목록만 읽고 만들 것을 출력.
화면 조작인 이유: AdMob 앱/광고 단위 생성 공개 API 없음(Admob API는 읽기 전용).
Gotcha: 앱 목록의 앱 이름은 <a>가 아니라 클릭 가능한 리프 요소. 앱 ID 숫자 = /v2/apps/<숫자>/adunits/create URL. 라디오·버튼은 JS click으로 충분
        (rclick은 다른 창이 앞이면 빗나감). 이름·리워드 상품은 c.fill, 광고 단위 이름 칸은 첫 input, 리워드 상품은 textarea(수량 기본 1).
        '보상형'은 광고 형식 카드의 4번째 '선택' 버튼(보상형 전면 광고 베타와 혼동 주의). 생성 뒤 광고 단위 ID는 완료 화면/adunits/list에 표시.
        app-ads.txt 줄은 AdMob 화면에 안 나온다: google.com, pub-4785237655148075, DIRECT, f08c47fec0942fa0
RESULT: OK | DRY_RUN
출력: APP <이름> <플랫폼> ca-app-pub-…~<id> / UNIT <플랫폼> <단위이름> ca-app-pub-…/<id>
"""
import re
import tempfile
import time

from _common import c, js, parser, tab

PUB = "ca-app-pub-4785237655148075"
ap = parser("Create AdMob app + rewarded unit (idempotent)")
ap.add_argument("name")
ap.add_argument("--platform", action="append", choices=["Android", "iOS"], required=True)
ap.add_argument("--unit", default="hint_rewarded")
ap.add_argument("--reward-item", default="hint")
ap.add_argument("--reward-amount", default="1")
ap.add_argument("--formats", default="", help="banner,interstitial 처럼 쉼표로. 주면 --unit 대신 이 형식 단위를 앱당 만든다(단위 이름은 <앱영문>_<형식>)")
ap.add_argument("--unit-prefix", default="tu", help="--formats 단위 이름 앞부분")
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()
png = tempfile.gettempdir() + "/admob_app_create.png"


def front(tid, wait=8):
    c.shot(tid, png)  # Angular는 백그라운드 탭에서 안 그려진다
    time.sleep(wait)


def click_btn(tid, text, idx=0):
    return js(tid, "const b=[...document.querySelectorAll('button,material-button,[role=button]')]"
              f".filter(x=>x.textContent.trim()=={text!r}); if(!b[{idx}]) return 0; b[{idx}].click(); return b.length")


def apps(tid):
    c.goto(tid, "https://admob.google.com/v2/apps/list")
    time.sleep(3)
    front(tid)
    t = c.page_text(tid)
    return {(m[0], m[1]): m[2] for m in re.findall(r"\n([^\n]+)\n(Android|iOS)\ncontent_copy\n" + PUB + r"~\n(\d+)\n", "\n" + t)}


def unit(tid, app_id, name=None):
    c.goto(tid, f"https://admob.google.com/v2/apps/{app_id}/adunits/list")
    time.sleep(3)
    front(tid, 9)
    m = re.search(re.escape(name or a.unit) + r"\n(" + PUB + r"/\d+)", c.page_text(tid))
    return m.group(1) if m else None


with tab("https://admob.google.com/v2/home", a) as tid:
    c.google_relogin(tid)
    time.sleep(3)
    for pf in a.platform:
        have = apps(tid)
        app_id = have.get((a.name, pf))
        if app_id:
            print(f"APP {a.name} {pf} {PUB}~{app_id} (EXISTS)")
        elif a.dry_run:
            print(f"DRY_RUN would create app {a.name} {pf}")
            continue
        else:
            c.goto(tid, "https://admob.google.com/v2/apps/create")
            time.sleep(3)
            front(tid)
            for tx in [pf, "아니요"]:
                js(tid, "const e=[...document.querySelectorAll('div')].filter(x=>x.children.length<3&&x.textContent.trim()==" + repr(tx) + ")[0]; e.click(); return 1")
                time.sleep(1)
            click_btn(tid, "계속")
            time.sleep(4)
            c.fill(tid, "input", a.name)
            time.sleep(1)
            click_btn(tid, "앱 추가")
            time.sleep(5)
            if "추가가 완료" not in c.page_text(tid):
                print("RESULT: FAILED app create"); raise SystemExit(1)
            app_id = apps(tid).get((a.name, pf))
            print(f"APP {a.name} {pf} {PUB}~{app_id} (CREATED)")
        if a.formats:
            card = {"banner": "배너", "interstitial": "전면"}
            for fmt in a.formats.split(","):
                uname = f"{a.unit_prefix}_{pf.lower()}_{fmt}"
                uid = unit(tid, app_id, uname)
                if uid:
                    print(f"UNIT {pf} {uname} {uid} (EXISTS)"); continue
                if a.dry_run:
                    print(f"DRY_RUN would create unit {uname}"); continue
                c.goto(tid, f"https://admob.google.com/v2/apps/{app_id}/adunits/create")
                time.sleep(3)
                front(tid)
                got = js(tid, "const want=%r; const bs=[...document.querySelectorAll('button,material-button,[role=button]')].filter(x=>x.textContent.trim()=='선택');"
                         "for(const b of bs){let e=b;for(let i=0;i<5&&e;i++){e=e.parentElement; if(e&&e.textContent.trim().startsWith(want)&&e.textContent.length<400){b.click();return e.textContent.slice(0,60)}}} return 0" % card[fmt])
                print("CARD", fmt, got)
                time.sleep(4)
                c.fill(tid, "input", uname)
                time.sleep(1)
                click_btn(tid, "광고 단위 만들기")
                time.sleep(5)
                uid = unit(tid, app_id, uname)
                if not uid:
                    c.shot(tid, png); print("RESULT: FAILED unit create", fmt, png); raise SystemExit(1)
                print(f"UNIT {pf} {uname} {uid} (CREATED)")
            continue
        uid = unit(tid, app_id)
        if uid:
            print(f"UNIT {pf} {a.unit} {uid} (EXISTS)")
        elif a.dry_run:
            print(f"DRY_RUN would create unit {a.unit} for {pf}")
        else:
            c.goto(tid, f"https://admob.google.com/v2/apps/{app_id}/adunits/create")
            time.sleep(3)
            front(tid)
            js(tid, "const b=[...document.querySelectorAll('button,material-button,[role=button]')].filter(x=>x.textContent.trim()=='선택'); b[3].click(); return 1")
            time.sleep(4)
            c.fill(tid, "input", a.unit)
            c.fill(tid, "textarea", a.reward_item)
            if a.reward_amount != "1":
                # 수량 칸은 nth-of-type로 안 잡힌다(11/10 NOTFOUND). 보이는 숫자 input 중 마지막을 쓴다
                js(tid, "const v=[...document.querySelectorAll('input')].filter(e=>e.offsetParent&&(e.type=='number'||/^\\d+$/.test(e.value)));if(v.length)v[v.length-1].id='rw_amt';return v.length")
                try:
                    c.fill(tid, "#rw_amt", a.reward_amount)
                except RuntimeError as e:
                    print("WARN reward amount not set, left 1:", e)
            time.sleep(1)
            click_btn(tid, "광고 단위 만들기")
            time.sleep(5)
            uid = unit(tid, app_id)
            if not uid:
                print("RESULT: FAILED unit create"); raise SystemExit(1)
            print(f"UNIT {pf} {a.unit} {uid} (CREATED)")
    print("RESULT: " + ("DRY_RUN" if a.dry_run else "OK"))
