#!/usr/bin/env python3
"""[제출] 앱인토스 콘솔 — 게임 앱 '게임 등급분류'(3단계, 스토어 링크 방식) 칸을 채우고 임시저장/검토 요청.

  ait_game_rating.py <appName> --deployment <id> --store-url <스토어 주소>
        --sign <대표 서명 png> --pairs store1.png:toss1.png,store2.png:toss2.png
        [--subcat 시뮬레이션/키우기·육성] [--agency 'Google LLC'] [--grade '전체 이용가']
        [--rating-number N --rating-date YYYY-MM-DD] [--submit]

- 회사 칸(사업자명·대표자·주소·전화)은 ~/Documents/oguri-works/개인정보.md 에서 패턴으로 뽑고 출력하지 않는다(길이만).
- 확약 5개는 사용자 사전 동의(2026-10-22)로 체크한다. --submit 이면 '검토 요청하기'를 누르고 화면 오류문을 그대로 출력.
- 메뉴(radix)는 click 을 보내면 열렸다 바로 닫힌다 → PointerEvent('pointerdown') 하나만 보내고 aria-controls 로 메뉴를 찾는다.
- 첫 번째 aria-haspopup=menu 는 '스토어 링크/등급분류증명서' 유형 선택이다. 내용정보 메뉴와 헷갈리지 말 것.
- 파일 칸은 하나 올릴 때마다 사라진다 → 항상 보이는 첫 칸에 순서대로 넣는다(서명 → 화면1 스토어 → 화면1 토스 → 화면2 …).
- 함정(2026-11-06 골골냥): 등급분류번호·등급분류일자가 비어도 버튼은 켜지지만 누르면
  "등급분류일자를 입력해 주세요. / 등급분류번호를 입력해 주세요." 로 막힌다. 번호는 플레이 IARC 인증 ID(콘솔 '콘텐츠 등급')가
  '-' 인 동안(스토어 미공개)엔 없고, 게임물관리위원회 자체등급분류 게임물 조회(SelfRateGameStatistics.aspx)에도 안 나온다.
  하위 카테고리 미선택도 같은 순간에 "하위 카테고리를 선택해 주세요." 로 막힌다(2단계).
- 날짜: 달력 창(트리거에 pointer 이벤트)에서 날짜 버튼 → '확인'. 내용정보 '해당 없음'은 menu_pick 으로 된다(2026-11-10 골골냥 검토 요청 성공).
- 함정: 2단계 '웹보드 게임' 체크가 켜지면 '스토어 링크'가 비활성이라 유형이 '등급분류증명서'로 남는다 → 스크립트가 끈다.
함정(2026-11-10 spot-difference-daily):
- 임시저장(PUT /draft)은 빠진 값을 '그대로 둠'으로 본다. 웹보드(specialCategory)는 임시저장으로 못 지운다.
  같은 탭에서 웹보드를 끈 채로 바로 '검토 요청하기'를 눌러야 검토본에서 빠진다(combined-review는 폼 값 그대로).
- '필수 값을 입력해 주세요.'만 뜨고 아무 요청이 안 나가면 앞 단계 빈칸이다. '이전'으로 가서 빨간 글(예: 2단계 가로 썸네일 1932x828)을 찾는다.
- 자체등급분류사업자명은 '구글'/'애플'. 숨은그림 게임 하위 카테고리 이름은 '숨은그림·차이찾기'.
- 다른 세션이 같은 Chrome 창 탭을 닫을 수 있다. 실제 마우스 클릭 대신 JS로, 한 번 실행 안에서 끝낸다.
검증: 2026-11-10 golgol-nyang; 2026-11-10 spot-difference-daily — 웹보드 해제·썸네일 보충 후 검토 요청 성공(검토 중) — 스토어 링크(플레이)·IARC 번호·날짜·해당 없음으로 검토 요청 성공(검토 중).
"""
import argparse, base64, json, os, re, sys, time
sys.path.insert(0, os.path.expanduser('~/.claude/skills/chrome-direct'))
import chromectl as c

WS = 35273
CL = "for(const k of ['pointerdown','mousedown','pointerup','mouseup','click'])E.dispatchEvent(new MouseEvent(k,{bubbles:true,cancelable:true,view:window}));"
SV = "function sv(el,v){Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,v);['input','change','blur'].forEach(k=>el.dispatchEvent(new Event(k,{bubbles:true})))};"


def console_tab(u):
    before = {r[4] for r in c.tabs(with_id=True)}
    r = c.jxa("var ws=C.windows(); for (var i=0;i<ws.length;i++){var ts=ws[i].tabs(); for(var j=0;j<ts.length;j++){"
              "if(String(ts[j].url()).indexOf('apps-in-toss.toss.im/workspace/')>=0){ ws[i].tabs.push(C.Tab({url:%s})); return 'ok';}}} return 'none';" % c.q(u))
    if r != 'ok':
        sys.exit('RESULT: LOGIN_REQUIRED 콘솔 탭이 열린 창이 없음 — toss_business_login.sh')
    for _ in range(15):
        time.sleep(1)
        new = [x for x in c.tabs(with_id=True) if x[4] not in before]
        if new:
            time.sleep(8)
            return 'id:' + new[-1][4]
    sys.exit('RESULT: ERROR 탭이 안 열림')


def btn(t, text):
    return c.js_json(t, "const E=[...document.querySelectorAll('button')].filter(x=>x.offsetParent&&x.innerText.trim()==%s).pop();if(!E)return 'none';%sreturn 'ok'" % (c.q(text), CL))


def menu_pick(t, idx, text):
    c.js_json(t, "const E=[...document.querySelectorAll('[aria-haspopup=menu]')].filter(x=>x.offsetParent)[%d];E.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,cancelable:true,button:0,pointerType:'mouse'}));return 1" % idx)
    time.sleep(2)
    return c.js_json(t, "const T=[...document.querySelectorAll('[aria-haspopup=menu]')].filter(x=>x.offsetParent)[%d];const m=document.getElementById(T.getAttribute('aria-controls'));if(!m)return 'nomenu';"
                        "const E=[...m.querySelectorAll('*')].filter(x=>x.innerText&&x.innerText.trim()==%s).pop();if(!E)return 'none: '+m.innerText.replace(/\\n/g,'|');"
                        "E.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,button:0,pointerType:'mouse'}));%sreturn 'ok'" % (idx, c.q(text), CL))


def file_first(t, p):
    c.run_js(t, 'window.__fs=[]')
    b = base64.b64encode(open(p, 'rb').read()).decode()
    c.run_js(t, "window.__b64=''")
    for i in range(0, len(b), 200000):
        c.run_js(t, 'window.__b64+=' + json.dumps(b[i:i + 200000]))
    c.js_json(t, "var s=atob(window.__b64),u=new Uint8Array(s.length);for(var i=0;i<s.length;i++)u[i]=s.charCodeAt(i);window.__fs.push(new File([u],%s,{type:'image/png'}));return 1" % json.dumps(os.path.basename(p)), 60)
    r = c.js_json(t, "var inp=[...document.querySelectorAll('input[type=file]')].filter(x=>x.offsetParent)[0];if(!inp)return 'NOINPUT';var dt=new DataTransfer();window.__fs.forEach(f=>dt.items.add(f));inp.files=dt.files;"
                     "inp.dispatchEvent(new Event('input',{bubbles:true}));inp.dispatchEvent(new Event('change',{bubbles:true}));return 'OK'", 60)
    print(os.path.basename(p), r)
    time.sleep(6)


def biz_info():
    L = open(os.path.expanduser('~/Documents/oguri-works/개인정보.md'), encoding='utf-8').read().splitlines()
    def val(label, start=0):
        for l in L[start:]:
            m = re.match(r'^\s*-\s*' + re.escape(label) + r'\s*[:：]\s*(.*)$', l)
            if m:
                return m.group(1)
    sec = next(i for i, l in enumerate(L) if l.startswith('## 사업자'))
    phone = re.search(r'01[0-9]-?\d{3,4}-?\d{4}', val('휴대폰')).group(0)
    if '-' not in phone:
        phone = phone[:3] + '-' + phone[3:-4] + '-' + phone[-4:]
    biz = re.split(r'\s*[(（,·/]|\s{2}', val('상호', sec))[0].strip()
    addr = re.sub(r'\s*[(（][^)）]*[)）]', '', val('사업장', sec)).strip()
    return biz, val('이름'), addr, phone


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('app'); ap.add_argument('--deployment', required=True); ap.add_argument('--store-url', required=True)
    ap.add_argument('--sign', required=True); ap.add_argument('--pairs', required=True)
    ap.add_argument('--subcat', default=''); ap.add_argument('--agency', default='구글'); ap.add_argument('--grade', default='전체 이용가')
    ap.add_argument('--rating-number', default=''); ap.add_argument('--rating-date', default='')
    ap.add_argument('--ws', type=int, default=WS); ap.add_argument('--submit', action='store_true')
    a = ap.parse_args()
    t = console_tab(f'https://apps-in-toss.toss.im/workspace/{a.ws}/mini-app/{a.app}/meta/edit?deploymentId={a.deployment}')
    btn(t, '다음'); time.sleep(4)
    if a.subcat:
        s1, s2 = a.subcat.split('/')
        print('subcat', menu_pick(t, 1, s1)); time.sleep(2); print('subcat2', menu_pick(t, 2, s2))
    # 웹보드 체크가 켜져 있으면 3단계 '스토어 링크'가 비활성(aria-disabled)이 된다 → 끈다(2026-11-10 골골냥)
    print('webboard', c.js_json(t, "const x=[...document.querySelectorAll('input[type=checkbox]')].find(x=>{let p=x;for(let i=0;i<4;i++)p=p.parentElement;return p.innerText.includes('웹보드')});if(!x)return 'none';if(x.checked)x.click();return 'off'"))
    btn(t, '임시저장'); time.sleep(2)
    btn(t, '다음'); time.sleep(5)
    print('type', menu_pick(t, 0, '스토어 링크')); time.sleep(3)
    biz, name, addr, phone = biz_info()
    V = {'step3.bizName': biz, 'step3.representativeName': name, 'step3.address': addr, 'step3.phoneNumber': phone,
         'step3.registrantName': biz, 'step3.ratingAgencyName': a.agency}
    if a.rating_number:
        V['step3.ratingNumber'] = a.rating_number
    print(c.js_json(t, SV + "const V=%s;for(const k in V){const e=document.querySelector('input[name=\"'+k+'\"]');if(e)sv(e,V[k])}"
                        "const s=[...document.querySelectorAll('input')].find(x=>x.placeholder&&x.placeholder.startsWith('앱스토어, 플레이'));if(s)sv(s,%s);"
                        "return JSON.stringify([...document.querySelectorAll('input[name^=step3]')].map(x=>[x.name,x.value.length]))" % (json.dumps(V, ensure_ascii=False), json.dumps(a.store_url))))
    if a.rating_date:
        # 날짜 칸(spinbutton)에 키를 넣으면 화면엔 보여도 폼 값이 안 들어간다 → 달력 창에서 날을 누르고 '확인'
        y, m, d = a.rating_date.split('-')
        P = "const f=E=>{for(const n of ['pointerdown','mousedown','pointerup','mouseup','click'])E.dispatchEvent(new PointerEvent(n,{bubbles:true,cancelable:true,button:0,pointerType:'mouse'}))};"
        c.js_json(t, P + "f(document.querySelector('[data-tds-data-picker-trigger]'));return 1"); time.sleep(2)
        for _ in range(24):
            head = c.js_json(t, "const d=document.getElementById(document.querySelector('[data-tds-data-picker-trigger]').getAttribute('aria-controls'));return d?d.innerText.split('\\n')[0]:''")
            hy, hm = [int(x) for x in re.findall(r'\d+', head)[:2]] if head else (0, 0)
            if (hy, hm) == (int(y), int(m)) or not head:
                break
            lab = '이전' if (hy, hm) > (int(y), int(m)) else '다음'
            c.js_json(t, P + "const d=document.getElementById(document.querySelector('[data-tds-data-picker-trigger]').getAttribute('aria-controls'));const b=[...d.querySelectorAll('button')].find(x=>(x.getAttribute('aria-label')||'').includes(%s));if(b)f(b);return 1" % json.dumps(lab)); time.sleep(1)
        print('date', c.js_json(t, P + "const d=document.getElementById(document.querySelector('[data-tds-data-picker-trigger]').getAttribute('aria-controls'));if(!d)return 'nodlg';"
                                 "const E=[...d.querySelectorAll('button')].find(x=>x.innerText.trim()==%s);if(!E)return 'noday';f(E);const ok=[...d.querySelectorAll('button')].find(x=>x.innerText.trim()=='확인');if(ok)f(ok);return 'ok'" % json.dumps(str(int(d)))))
        time.sleep(2)
        print('date shown', c.js_json(t, "return [...document.querySelectorAll('[data-tds-data-picker-trigger] [role=spinbutton]')].map(x=>x.innerText).join('.')"))
    if c.js_json(t, "return [...document.querySelectorAll('input[type=file]')].filter(x=>x.offsetParent).length") >= 5:
        file_first(t, os.path.expanduser(a.sign))
        for pr in a.pairs.split(','):
            for p in pr.split(':'):
                file_first(t, os.path.expanduser(p))
    else:
        print('files: 이미 올라가 있음 — 건너뜀')
    # 이용등급 → 내용정보 순으로 '선택하기'가 남아 있으면 고른다(내용정보는 IARC 항목이 없으면 '해당 없음')
    for want in (a.grade, '해당 없음'):
        idx = c.js_json(t, "return [...document.querySelectorAll('[aria-haspopup=menu]')].filter(x=>x.offsetParent).findIndex(x=>x.innerText.trim()=='선택하기')")
        if idx < 0:
            break
        print('pick', want, menu_pick(t, idx, want)); time.sleep(2)
    print(c.js_json(t, "const lab=x=>{let p=x;for(let i=0;i<4;i++)p=p.parentElement;return p.innerText};const cb=[...document.querySelectorAll('input[type=checkbox]')].filter(x=>!lab(x).includes('웹보드'));for(const x of cb){if(!x.checked)x.click()}return 'pledges '+cb.filter(x=>x.checked).length+'/'+cb.length"))
    btn(t, '임시저장'); time.sleep(3)
    if not a.submit:
        print('RESULT: DRAFT_SAVED'); return
    btn(t, '검토 요청하기'); time.sleep(6)
    err = c.js_json(t, "return [...document.querySelectorAll('[role=dialog],[role=alertdialog],[role=alert],[class*=toast]')].map(x=>x.innerText).join(' | ')")
    print('RESULT: ' + ('BLOCKED ' + err if '입력해 주세요' in err or '선택해 주세요' in err else 'CHECK_SCREEN ' + err + ' → miniapp_meta_status 로 확인'))


if __name__ == '__main__':
    main()
