"""위시켓 파트너 헬퍼 (2026-10-23 실제로 돈 순서).
사용:
  python3 wishket_partner.py list                       # 모집 중 외주(도급) 공고만
  python3 wishket_partner.py read 159202 [159219 ...]   # 공고 본문
  python3 wishket_partner.py skills "Python:고급:5" "React:중급:3"   # 보유기술 추가(이미 있으면 건너뜀)
  python3 wishket_partner.py apply 159202 --budget 1800000 --term 14 --body body.txt --rel rel.txt --portfolio 322783 [--submit]
하는 일: 사용자 Chrome(로그인된 Profile 1)의 wishket.com 탭에서 목록·상세 읽기, 보유기술 추가, 지원서 작성·제출.
사전 조건: 위시켓 파트너 로그인(계정 ~/.claude/sns.env WISHKET_*), 외주 지원은 포트폴리오 1개 이상 필요.
왜 화면 조작: 공개 API 없음. 목록 필터는 URL 파라미터가 안 먹고 버튼이 만든 d= 토큰만 먹는다.
함정:
- 페이지 함수(modal_close, start_cropper, jQuery 핸들러)는 AppleScript JS에서 안 보인다 → <script> 주입으로 메인 월드에서 돈다(main()).
- 관련 포트폴리오 상자는 jQuery 핸들러라 dispatchEvent 클릭은 토글이 여러 번 일어난다 → 메인 월드 $(...).trigger('click').
- 보유기술: '.add-edit-box' 클릭 → 폼 안 '.stack-selector[data-tag-name=X]' 클릭 뒤 기술명이 비면 다시 넣어야 저장된다.
- 포트폴리오 등록(1회성이라 스크립트 안 함): 이미지는 DataTransfer로 input.temporary-image(본문)·.thumbnail-temporary-image-file(표지)에 넣고,
  표지는 업로드 모달이 멈추므로 메인 월드에서 modal_close('upload-thumbnail-img-modal');start_cropper();modal_open('crop-thumbnail-img-modal'),
  cropper.setData({x:0,y:0,width:480,height:480}) 뒤 #crop-portfolio-img 클릭. 하위 카테고리 field_web은 checked=true + change.
- 업력 1년 이상(사업자등록증 기준) 조건 공고가 많다. 지원 전 '모집 요건' 확인.
- 페이지 텍스트에 사용자 전화번호가 섞여 나오므로 출력 전 번호 패턴을 가린다.
"""
import sys, os, re, json, time, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chromectl as c

M = 'wishket.com'
LIST_URL = 'https://www.wishket.com/project/?d=A4FwvCCGDODWD6AjGBTAJkA%3D'  # 외주(도급) 칩을 누른 상태


def js(code): return c.js_json(M, code)


def main_world(code):
    """페이지 전역(jQuery·페이지 함수)이 보이는 메인 월드에서 code(함수 본문)를 돌리고 JSON 결과를 받는다."""
    js('delete document.body.dataset.r;return 1')
    s = json.dumps("try{document.body.dataset.r=JSON.stringify((function(){" + code + "})())}catch(e){document.body.dataset.r='ERR '+e}")
    return js('const s=document.createElement("script");s.textContent=%s;document.body.appendChild(s);s.remove();return document.body.dataset.r' % s)


def mask(t): return re.sub(r'\d{3,4}-\d{3,4}-\d{4}', '[번호]', t or '')


def ensure_tab():
    try:
        c.find_tab(M)
    except Exception:
        c.new_tab('https://www.wishket.com/', profile='Profile 1'); time.sleep(3)


def go(url, wait=4):
    js('location.href=%s;return 1' % json.dumps(url)); time.sleep(wait)


def cmd_list(_):
    go(LIST_URL)
    rows = js('''return [...document.querySelectorAll("a[href^='/project/']")].filter(a=>/^\\/project\\/\\d+\\/$/.test(a.getAttribute("href"))).map(a=>{let c=a;for(let i=0;i<6&&c.parentElement&&!/예상 기간/.test(c.innerText);i++)c=c.parentElement;return a.getAttribute("href")+" || "+c.innerText.replace(/\\s+/g," ").slice(0,200)})''') or []
    seen = set(); n = 0
    for r in rows:
        h = r.split(' || ')[0]
        if h in seen or '월 금액' in r or '모집 중' not in r: continue
        seen.add(h); n += 1; print(r)
    print(f'RESULT: OK {n}건')


def cmd_read(a):
    for pid in a.ids:
        go(f'https://www.wishket.com/project/{pid}/', 5)
        t = mask(js('return document.body.innerText'))
        i = t.find('모집'); j = t.find('프로젝트 문의', i)
        print('=====', pid); print(t[i:j if j > 0 else i + 6000])
    print('RESULT: OK')


def cmd_skills(a):
    go('https://www.wishket.com/partners/p/%s/skill/update/' % a.user)
    have = set(js('return [...document.querySelectorAll(".view-box .title")].map(e=>e.innerText.trim())') or [])
    for x in a.items:
        name, rating, exp = x.split(':')
        if name in have:
            print(name, 'SKIP(있음)'); continue
        js('document.querySelector(".add-edit-box").click();return 1'); time.sleep(1.2)
        r = js('''const t=[...document.querySelectorAll("input[name=title]")].find(e=>e.offsetParent);const f=t.closest("form");
const set=v=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set.call(t,v);t.dispatchEvent(new Event("input",{bubbles:true}));t.dispatchEvent(new KeyboardEvent("keyup",{bubbles:true}));};
set(%s);const sel=f.querySelector('.stack-selector[data-tag-name="'+%s+'"]');if(sel)sel.click();if(!t.value)set(%s);
const S=(n,txt)=>{const e=f.querySelector("select[name="+n+"]");const o=[...e.options].find(o=>o.text.trim().startsWith(txt));e.value=o.value;e.dispatchEvent(new Event("change",{bubbles:true}));return o.text};
const a=S("rating",%s),b=S("experience",%s);[...f.parentElement.querySelectorAll("button")].find(b=>b.innerText.trim()=="저장").click();return [!!sel,t.value,a,b]''' % tuple(json.dumps(v) for v in (name, name, name, rating, exp)))
        print(name, r); time.sleep(2.5)
    js('location.reload();return 1'); time.sleep(4)
    print(js('return [...document.querySelectorAll(".view-box .title")].map(e=>e.innerText.trim())'))
    print('RESULT: OK')


def setf(fields):
    import base64
    b = base64.b64encode(json.dumps(fields, ensure_ascii=False).encode()).decode()
    return js('const a=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob("%s"),ch=>ch.charCodeAt(0))));const out=[];'
              'for(const [n,v] of Object.entries(a)){const e=document.querySelector("input[name=\'"+n+"\'],textarea[name=\'"+n+"\']");if(!e){out.push(n+":NF");continue;}'
              'Object.getOwnPropertyDescriptor(e.tagName=="TEXTAREA"?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,"value").set.call(e,v);'
              'for(const t of ["input","change","keyup"])e.dispatchEvent(new Event(t,{bubbles:true}));out.push(n+":"+e.value.length)}return out' % b)


def applied(pid):
    go('https://www.wishket.com/partners/manage/proposal/')
    return f'/project/{pid}/' in (js('return [...document.querySelectorAll("a")].map(a=>a.getAttribute("href")).join(" ")') or '')


def cmd_apply(a):
    if applied(a.id):
        print('RESULT: ALREADY 이미 지원함'); return
    go(f'https://www.wishket.com/project/{a.id}/proposal/apply/', 5)
    if 'proposal/apply' not in (js('return location.href') or ''):
        print('RESULT: BLOCKED 지원 화면이 안 열림(마감·포트폴리오 없음 등)'); return
    body = open(a.body).read().strip()
    rel = open(a.rel).read().strip() if a.rel else ''
    print(setf({'budget': str(a.budget), 'term': str(a.term), 'body': body}))
    js('const r=[...document.querySelectorAll("input[name=has_related_portfolio]")].find(e=>e.value=="True");(r.closest("label")||r.parentElement).click();return 1'); time.sleep(1)
    if a.portfolio:
        print(main_world('$(".portfolio-box[data-portfolio=%d]").first().trigger("click");$("#select_portfolio_btn").trigger("click");return $("input[name=relate_portfolio_first]").val()' % a.portfolio))
    if rel:
        print(setf({'related_description': rel}))
    main_world('$("#proposal_review_btn").trigger("click");return 1'); time.sleep(3)
    review = js('return [...document.querySelectorAll(".modal-content")].filter(e=>e.offsetParent).map(e=>e.innerText.slice(0,600)).join("\\n")')
    print(mask(review))
    if not a.submit:
        print('RESULT: DRY-RUN 확인 창까지 채움(--submit 없으면 제출 안 함)'); return
    main_world('$("#confirm_apply_btn").trigger("click");return 1'); time.sleep(6)
    print('RESULT:', 'OK 지원 완료' if applied(a.id) else 'FAIL 지원 내역에 없음')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); s = p.add_subparsers(dest='cmd', required=True)
    s.add_parser('list')
    r = s.add_parser('read'); r.add_argument('ids', nargs='+')
    k = s.add_parser('skills'); k.add_argument('items', nargs='+'); k.add_argument('--user', default='oguriworks')
    ap = s.add_parser('apply'); ap.add_argument('id'); ap.add_argument('--budget', type=int, required=True); ap.add_argument('--term', type=int, required=True)
    ap.add_argument('--body', required=True); ap.add_argument('--rel'); ap.add_argument('--portfolio', type=int); ap.add_argument('--submit', action='store_true')
    a = p.parse_args(); ensure_tab()
    {'list': cmd_list, 'read': cmd_read, 'skills': cmd_skills, 'apply': cmd_apply}[a.cmd](a)
