"""크몽 엔터프라이즈(기업 프로젝트) 공고 목록 읽기·제안 제출.
사용:
  python3 kmong_enterprise.py list                      # 공고 목록(마감·제목·분야·기간·지원자·예산)
  python3 kmong_enterprise.py read <id>                 # 공고 본문
  python3 kmong_enterprise.py propose <id> --amount 1980 --days 102 --content-file prop.txt \
      [--attach a.png --attach b.pdf] [--no-tax] [--submit]
하는 일: 사용자 Chrome(Profile 1, 크몽 로그인 상태)에서 새 탭을 열어 조작하고 탭을 닫는다.
사전 조건: 엔터프라이즈 프로필(/enterprise/seller/profile) 등록 완료. 사업자 승인은 필요 없다.
왜 화면 조작인가: 크몽은 공개 API가 없다.
멱등: 공고 페이지에 '제안하기' 버튼이 없으면(이미 제안·마감) ALREADY로 끝낸다.
함정:
- 제안 양식 체크박스는 다시 그려지면 name이 사라진다 → 순서로 잡는다(필수 2개).
- 크몽 datepicker도 role=dialog다. 모달 안 입력을 찾을 땐 .react-datepicker를 빼고 고른다.
- 다른 스크립트(인증 감시)가 'kmong.com' 탭을 이동시키므로 탭은 new_tab id로만 가리킨다.
- 제안 후 수정 불가. 최종 확인 모달의 '제안하기'를 한 번 더 눌러야 제출된다.
"""
import sys, os, re, time, json, base64, argparse
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

BASE = 'https://kmong.com/enterprise/requests'


def text(t):
    return c.js_json(t, 'return document.body.innerText') or ''


def cmd_list(t):
    c.goto(t, BASE); time.sleep(6)
    s = re.sub(r'\s+', ' ', text(t))
    n = 0
    for m in re.finditer(r'(외주 모집|상주 모집|모집 마감)\s*(D-\d+|D-DAY)?\s*(.{0,70}?)\s*(IT·프로그래밍|디자인|마케팅|영상·사진·음향|기획)\s.*?진행 기간\s*(\d+)일\s*지원자\s*(\d+)명\s*([\d,]+만원|금액 협의|[^ ]+)', s):
        n += 1
        print(' | '.join(x or '' for x in m.groups()))
    ids = c.js_json(t, 'return [...new Set([...document.querySelectorAll("a[href*=\'/enterprise/requests/\']")].map(a=>a.href.match(/requests\\/(\\d+)/)?.[1]).filter(Boolean))].join(",")')
    print('ids:', ids)
    return f'OK {n}건'


def cmd_read(t, rid):
    c.goto(t, f'{BASE}/{rid}'); time.sleep(6)
    s = text(t)
    i = s.find('프로젝트 설명'); j = s.find('비슷한 프로젝트 등록하기')
    print(re.sub(r'\d{2,3}-\d{3,4}-\d{4}', '[번호]', s[max(i - 600, 0):j if j > 0 else None]))
    return 'OK'


def setv(t, sel, val):
    return c.js_json(t, 'const e=document.querySelector(%s);if(!e)return "NF";const p=Object.getPrototypeOf(e);Object.getOwnPropertyDescriptor(p,"value").set.call(e,%s);e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}));return "ok"' % (json.dumps(sel), json.dumps(val)))


def cmd_propose(t, a):
    c.goto(t, f'{BASE}/{a.id}'); time.sleep(6)
    has = c.js_json(t, 'return [...document.querySelectorAll("button,a")].some(b=>b.innerText.trim()=="제안하기")')
    if not has:
        return 'ALREADY 제안하기 버튼 없음(이미 제안했거나 마감)'
    c.js_json(t, '[...document.querySelectorAll("button,a")].find(b=>b.innerText.trim()=="제안하기").click();return 1'); time.sleep(4)
    content = open(a.content_file).read().strip()
    if len(content) > 3000:
        return f'BLOCKED 본문 {len(content)}자 > 3000'
    out = [setv(t, 'input[name=amount]', str(a.amount)), setv(t, 'input[name=days]', str(a.days)), setv(t, 'textarea[name=content]', content)]
    out.append(c.js_json(t, 'const b=[...document.querySelectorAll("button")].find(b=>b.innerText.trim()==%r);if(!b)return "NF";b.click();return "ok"' % ('불가능' if a.no_tax else '가능')))
    for f in a.attach or []:
        b = base64.b64encode(open(f, 'rb').read()).decode()
        mime = 'application/pdf' if f.lower().endswith('.pdf') else 'image/png' if f.lower().endswith('.png') else 'image/jpeg'
        out.append(c.js_json(t, 'const i=document.querySelector("input[type=file]");const bin=atob(%s);const u=new Uint8Array(bin.length);for(let k=0;k<bin.length;k++)u[k]=bin.charCodeAt(k);const dt=new DataTransfer();dt.items.add(new File([u],%s,{type:%s}));i.files=dt.files;i.dispatchEvent(new Event("change",{bubbles:true}));return "ok"' % (json.dumps(b), json.dumps(os.path.basename(f)), json.dumps(mime)), timeout=60))
        time.sleep(3)
    out.append(str(c.js_json(t, 'const cs=[...document.querySelectorAll("input[type=checkbox]")];cs.forEach(e=>{if(!e.checked)e.click()});return cs.map(e=>e.checked).join(",")')))
    vals = c.js_json(t, 'return [...document.querySelectorAll("input[type=text],textarea")].map(e=>e.value.length).join(",")')
    print('fill:', out, 'lengths:', vals)
    if 'NF' in out:
        return 'FAIL 입력칸을 못 찾음'
    if not a.submit:
        return 'DRY-RUN 채우기만 함(--submit 없으면 제출 안 함)'
    c.js_json(t, 'const b=[...document.querySelectorAll("button")].filter(b=>b.innerText.trim()=="제안하기").pop();setTimeout(()=>b.click(),10);return 1'); time.sleep(4)
    c.js_json(t, 'const d=[...document.querySelectorAll("[role=dialog],.swal2-popup")].pop();const b=d&&[...d.querySelectorAll("button")].find(b=>b.innerText.trim()=="제안하기");if(b)setTimeout(()=>b.click(),10);return 1'); time.sleep(6)
    done = c.js_json(t, 'return [...document.querySelectorAll("[role=dialog],.swal2-popup")].some(d=>d.innerText.includes("제안 완료"))')
    return 'SUBMITTED' if done else 'UNKNOWN 제안 완료 창을 못 봄'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['list', 'read', 'propose'])
    ap.add_argument('id', nargs='?')
    ap.add_argument('--amount', type=int); ap.add_argument('--days', type=int)
    ap.add_argument('--content-file'); ap.add_argument('--attach', action='append')
    ap.add_argument('--no-tax', action='store_true'); ap.add_argument('--submit', action='store_true')
    a = ap.parse_args()
    t = c.new_tab(BASE, profile='Profile 1'); time.sleep(5)
    try:
        if a.cmd == 'list': r = cmd_list(t)
        elif a.cmd == 'read': r = cmd_read(t, a.id)
        else: r = cmd_propose(t, a)
    finally:
        c.close_tab(t)
    print('RESULT:', r)


if __name__ == '__main__':
    main()
