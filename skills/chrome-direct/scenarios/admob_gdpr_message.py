"""Usage: admob_gdpr_message.py [--name N] [--app "오늘의 눈썰미"] [--privacy-url URL] [--submit]

AdMob(remin1994, pub-4785237655148075) 개인 정보 보호 및 메시지 > 유럽 규정(GDPR) 메시지를 만들어 게시한다.
멱등: 같은 이름의 메시지가 목록에 있으면 만들지 않고 상태만 출력(EXISTS). --submit 없으면 목록만 읽음(DRY_RUN).
Gotchas: (1) 페이지는 admob.google.com/v2/privacymessaging/gdpr, 목록/시작 화면은 same-origin iframe(display-ads-user-messaging-embed)
  안, 에디터(전체화면)는 최상위 문서에 있다. (2) 'Angular'라 c.shot으로 탭을 앞에 띄운 뒤 읽는다. (3) 앱 선택 대화창: mat-checkbox 클릭,
  개인정보처리방침 'URL 추가'(platform-privacy-policy-cell) → input[type=url] 네이티브 setter+input 이벤트 → 저장. 앱 ID는 '—'로 보여 이름+플랫폼으로 고른다.
  (4) '동의하지 않음'은 기본 '선택'(국가별) → 대화창 맨 위 스위치 input.mdc-switch__native-control을 .click()으로 전체 켜야 '필수' 오류가 사라진다(이벤트 디스패치는 안 먹음).
  (5) 한국어는 언어 목록에 없음 → 영어(en)만. (6) 게시 확인 창의 '게시'는 버튼 목록 마지막. 게시 후 반영까지 최대 1시간.
RESULT: PUBLISHED | EXISTS:<status> | DRY_RUN
"""
import tempfile
import time

from _common import c, js, parser, tab

ap = parser("AdMob GDPR message create+publish (idempotent)", submit=True)
ap.add_argument("--name", default="오늘의 눈썰미 GDPR")
ap.add_argument("--app", default="오늘의 눈썰미")
ap.add_argument("--privacy-url", default="https://oguriworks.remin1994.workers.dev/privacy.html")
a = ap.parse_args()
png = tempfile.gettempdir() + "/admob_gdpr_message.png"
EV = "for(const k of['mousedown','mouseup','click'])b.dispatchEvent(new MouseEvent(k,{bubbles:true,cancelable:true,view:window}));"
IF = "const D=document.querySelector('iframe[src*=user-messaging-embed]').contentDocument;"


def front(tid, w=6):
    c.shot(tid, png)
    time.sleep(w)


def top_click(tid, text, last=False, sel="button,material-button,[role=button],a"):
    return js(tid, f"const l=[...document.querySelectorAll({sel!r})].filter(x=>x.textContent.trim()=={text!r}&&x.getClientRects().length);"
              f"const b=l[{'l.length-1' if last else 0}];if(!b)return 0;{EV}return l.length")


def leaf_click(tid, text, closest="button,[role=button],material-button"):
    return js(tid, f"const e=[...document.querySelectorAll('*')].find(x=>x.children.length==0&&x.textContent.trim().startsWith({text!r})&&x.getClientRects().length);"
              f"if(!e)return 0;const b=e.closest({closest!r})||e;{EV}return 1")


def listing(tid):
    c.goto(tid, "https://admob.google.com/v2/privacymessaging/gdpr")
    time.sleep(3)
    front(tid, 8)
    return js(tid, IF + "return D.body.innerText")


def setv(tid, sel, val):
    return js(tid, f"const i=document.querySelector({sel!r});i.focus();Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,{val!r});"
              "i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}));i.dispatchEvent(new Event('blur'));return i.value")


with tab("https://admob.google.com/v2/privacymessaging", a) as tid:
    c.google_relogin(tid)
    time.sleep(3)
    t = listing(tid)
    if a.name in t:
        i = t.find(a.name)
        st = "게시됨" if "게시됨" in t[i:i + 200] else "초안"
        print(f"MESSAGE {a.name} {st}")
        print(f"RESULT: EXISTS:{st}")
        raise SystemExit(0)
    if not a.submit:
        print(f"DRY_RUN would create+publish '{a.name}' for {a.app} iOS+Android")
        print("RESULT: DRY_RUN")
        raise SystemExit(0)
    # 시작 화면이면 '유럽 규정 메시지 만들기', 목록이면 '메시지 만들기'(둘 다 iframe 안 버튼)
    js(tid, IF + "const b=[...D.querySelectorAll('button')].find(x=>['유럽 규정 메시지 만들기','메시지 만들기'].includes(x.textContent.trim())&&x.getClientRects().length);" + EV + "return 1")
    time.sleep(5)
    front(tid, 4)
    # --- 에디터(최상위 문서) ---
    top_click(tid, "앱 선택")
    time.sleep(3)
    for plat in ("iOS", "Android"):
        js(tid, f"const m=[...document.querySelectorAll('mat-checkbox')].filter(x=>x.getClientRects().length).find(x=>{{const r=x.closest('[class*=row],tr,[role=row]')||x.parentElement.parentElement;const t=r.innerText;return t.includes({a.app!r})&&t.includes('| {plat}')}});"
                 "if(!m)return 0;const b=m.querySelector('input')||m;" + EV + "return 1")
    for idx in range(3):  # 선택한 앱 행의 'URL 추가' (이미 URL 있으면 건너뜀)
        n = js(tid, f"const L=[...document.querySelectorAll('platform-privacy-policy-cell')].filter(x=>x.getClientRects().length&&x.innerText.trim()=='URL 추가'&&"
                    f"(x.closest('[class*=row],tr,[role=row]')||x.parentElement.parentElement).innerText.includes({a.app!r}));if(!L.length)return 0;const b=L[0];{EV}return 1")
        if not n:
            break
        time.sleep(2)
        setv(tid, "input[type=url]", a.privacy_url)
        time.sleep(1)
        top_click(tid, "저장")
        time.sleep(3)
    top_click(tid, "확인")
    time.sleep(3)
    # 동의하지 않음: '선택' → 국가 대화창 → 전체 스위치 → 확인
    js(tid, "const e=[...document.querySelectorAll('span.button-text')].find(x=>x.textContent.trim()=='선택'&&x.getClientRects().length);const b=e.closest('button,[role=button],material-button')||e;" + EV + "return 1")
    time.sleep(3)
    js(tid, "const i=[...document.querySelectorAll('input.mdc-switch__native-control')].filter(x=>x.closest('.mdc-switch').getClientRects().length)[0];i.click();return i.checked")
    time.sleep(1)
    top_click(tid, "확인")
    time.sleep(2)
    setv(tid, 'input[aria-label="메시지 이름 입력"]', a.name)
    time.sleep(1)
    top_click(tid, "게시")           # 상단 게시
    time.sleep(3)
    top_click(tid, "게시", last=True)  # 확인 대화창의 게시
    time.sleep(6)
    t = listing(tid)
    i = t.find(a.name)
    ok = i >= 0 and "게시됨" in t[i:i + 200]
    c.shot(tid, png)
    print(f"MESSAGE {a.name} {'게시됨' if ok else 'UNCONFIRMED'} screenshot={png}")
    print("RESULT: PUBLISHED" if ok else "RESULT: UNCONFIRMED")
    raise SystemExit(0 if ok else 1)
