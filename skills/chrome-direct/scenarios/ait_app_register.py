#!/usr/bin/env python3
"""[제출] 앱인토스 콘솔 — 새 미니앱 만들기 / 테스트 푸시 / 첫 등록 정보 채우고 검토 요청. 출시는 절대 안 누름.

  ait_app_register.py create <appName> <표시이름> [--game] [--submit]
  ait_app_register.py push   <appName> [--submit]                  # 버전 내역 첫 행 '테스트' → '푸시 보내기'
  ait_app_register.py meta   <appName> --deployment <id> --store <store-text.md> --icon <600png> --shots a.png,b.png,c.png[,d.png]
                             --category 생활/콘텐츠/운세 [--dark-icon png] [--submit]

- create: 콘솔 화면의 '앱 만들기'는 appName이 이미 쓰이면(다른 워크스페이스 포함) 아무 표시 없이 실패한다.
  그래서 콘솔이 쓰는 API를 탭 안에서 직접 부른다(POST .../workspaces/{ws}/mini-app). 이미 이 워크스페이스에 있으면 EXISTS.
  실패 사유는 그대로 출력(예: miniApp.AppNameAlreadyTaken → 다른 이름으로 다시).
- meta: meta/edit?deploymentId=… 폼을 채운다. store-text.md 의 '## 영어 이름' '## 부제' '## 상세 설명' '## 검색 키워드' '## 출시 노트' 절을 읽는다.
  고객문의 이메일은 같은 워크스페이스의 다른 앱(--cs-from, 기본 oneul-kkum) 값을 복사한다(출력 안 함).
  --submit 이 없으면 채우고 임시저장까지만. --submit 이면 확인 체크 5개(사용자 사전 동의 2026-10-22) → 검토 요청하기.
- 검토 요청은 테스트 푸시를 보내고 테스터가 토스 앱에서 한 번 열어야 풀리던 적이 있다(오늘꿈해몽). 오늘타로는 푸시 직후 바로 됐다.
- 왜 화면 조작인가: 콘솔에 공개 API가 없다. 로그인 쿠키가 있는 탭 안에서 XHR/폼을 쓴다.
  탭은 이미 workspace 탭이 열린 창에 연다(다른 프로필 창은 콘솔 로그아웃 상태).
검증: 2026-10-22 oneul-tarot-card(오늘타로) 손으로 같은 순서 성공 — create(API)·push·meta 전체·검토 요청. 스크립트 형태로는 create EXISTS 경로만 실행.
"""
import argparse, base64, json, os, re, sys, time
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

API = '/console/api-public/v3/appsintossconsole/workspaces/{ws}'
SETV = r"""function __setv(el,v){const p=el.tagName=='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
Object.getOwnPropertyDescriptor(p,'value').set.call(el,v);['input','change','blur'].forEach(t=>el.dispatchEvent(new Event(t,{bubbles:true})))}"""


def console_tab(u):
    """이미 콘솔 workspace 탭이 있는 창에 새 탭을 연다(로그인 상태 유지)."""
    before = {r[4] for r in c.tabs(with_id=True)}
    r = c.jxa("var ws=C.windows(); for (var i=0;i<ws.length;i++){var ts=ws[i].tabs(); for(var j=0;j<ts.length;j++){"
              "if(String(ts[j].url()).indexOf('apps-in-toss.toss.im/workspace/')>=0){ ws[i].tabs.push(C.Tab({url:%s})); return 'ok';}}} return 'none';" % c.q(u))
    if r != 'ok':
        sys.exit('RESULT: LOGIN_REQUIRED 콘솔 탭이 열린 창이 없음 — toss_business_login.sh')
    for _ in range(15):
        time.sleep(1)
        new = [x for x in c.tabs(with_id=True) if x[4] not in before]
        if new:
            t = 'id:' + new[-1][4]
            c.jxa("var ws=C.windows(); for (var i=0;i<ws.length;i++){var ts=ws[i].tabs(); for(var j=0;j<ts.length;j++){ if(ts[j].id()==%s){ws[i].activeTabIndex=j+1; return 1}}}" % new[-1][4])
            time.sleep(5)
            return t
    sys.exit('RESULT: ERROR 탭이 안 열림')


def xhr(t, method, path, body=None):
    js = "var x=new XMLHttpRequest();x.open(%s,%s,false);x.setRequestHeader('Content-Type','application/json');x.send(%s);return x.responseText" % (
        json.dumps(method), json.dumps(path), json.dumps(json.dumps(body)) if body is not None else 'null')
    return json.loads(c.js_json(t, js))


def click_text(t, text, last=False):
    r = c.js_json(t, "var b=[...document.querySelectorAll('button')].filter(e=>e.textContent.trim()===%s);b=b[%s];if(!b)return 'NOTFOUND';if(b.disabled)return 'DISABLED';b.click();return 'OK'"
                  % (json.dumps(text), 'b.length-1' if last else '0'))
    if r != 'OK':
        raise RuntimeError(f'button {text}: {r}')


def files_into(t, input_js, paths):
    c.run_js(t, 'window.__fs=[]')
    for p in paths:
        b = base64.b64encode(open(p, 'rb').read()).decode()
        c.run_js(t, "window.__b64=''")
        for i in range(0, len(b), 200000):
            c.run_js(t, 'window.__b64+=' + json.dumps(b[i:i + 200000]))
        c.js_json(t, "var s=atob(window.__b64),u=new Uint8Array(s.length);for(var i=0;i<s.length;i++)u[i]=s.charCodeAt(i);"
                     "window.__fs.push(new File([u],%s,{type:'image/png'}));return 1" % json.dumps(os.path.basename(p)), 60)
    r = c.js_json(t, "var inp=%s;if(!inp)return 'NOINPUT';var dt=new DataTransfer();window.__fs.forEach(f=>dt.items.add(f));inp.files=dt.files;"
                     "inp.dispatchEvent(new Event('input',{bubbles:true}));inp.dispatchEvent(new Event('change',{bubbles:true}));return 'OK'" % input_js, 60)
    if r != 'OK':
        raise RuntimeError(f'file input: {r}')
    time.sleep(4 + 2 * len(paths))


def section(md, title):
    m = re.search(r'^## ' + re.escape(title) + r'[^\n]*\n(.*?)(?=^## |\Z)', md, re.S | re.M)
    return m.group(1).strip() if m else ''


def bullet(s):
    return re.sub(r'\s*\(.*?\)\s*$', '', s.lstrip('- ').splitlines()[0]).strip()


def cmd_create(a):
    t = console_tab(f'https://apps-in-toss.toss.im/workspace/{a.ws}/mini-app')
    try:
        apps = xhr(t, 'GET', API.format(ws=a.ws) + '/mini-app')
        names = json.dumps(apps, ensure_ascii=False)
        if f'"appName": "{a.app}"' in names or f'"appName":"{a.app}"' in names:
            print(f'RESULT: EXISTS {a.app}')
            return
        if not a.submit:
            print(f'RESULT: DRY_RUN 만들 수 있음(이 워크스페이스엔 없음) {a.app} {a.title}')
            return
        r = xhr(t, 'POST', API.format(ws=a.ws) + '/mini-app', {'appName': a.app, 'title': a.title, 'appType': 'GAME' if a.game else 'NON_GAME'})
        if r.get('resultType') == 'SUCCESS':
            print(f"RESULT: CREATED {a.app} miniAppId {r['success'].get('miniAppId')}")
        else:
            print('RESULT: FAILED', json.dumps(r.get('error', r), ensure_ascii=False)[:300])
    finally:
        c.close_tab(t)


def cmd_push(a):
    t = console_tab(f'https://apps-in-toss.toss.im/workspace/{a.ws}/mini-app/{a.app}/app-build')
    try:
        click_text(t, '테스트')
        time.sleep(3)
        dlg = c.js_json(t, "var d=[...document.querySelectorAll('[role=dialog]')].pop();return d?d.innerText:''")
        link = re.search(r'intoss-private://\S+', dlg)
        print('LINK', link.group(0) if link else '')
        if not a.submit:
            print('RESULT: DRY_RUN 푸시 안 보냄')
            return
        c.js_json(t, "var d=[...document.querySelectorAll('[role=dialog]')].pop();[...d.querySelectorAll('button')].find(b=>b.innerText.trim()=='푸시 보내기').click();return 1")
        time.sleep(3)
        sent = c.js_json(t, "return performance.getEntriesByType('resource').some(e=>/bundles\\/test-push/.test(e.name))")
        print('RESULT:', 'PUSHED' if sent else 'PUSH_NOT_SEEN')
    finally:
        c.close_tab(t)


def cmd_meta(a):
    md = open(a.store).read()
    det = section(md, '상세 설명')
    kws = [k.strip() for k in bullet(section(md, '검색 키워드')).split(',') if k.strip()][:10]
    t = console_tab(f'https://apps-in-toss.toss.im/workspace/{a.ws}/mini-app/{a.app}/meta/edit?deploymentId={a.deployment}')
    try:
        c.js_json(t, "window.onbeforeunload=null;return 1")
        base = API.format(ws=a.ws) + '/mini-app/'
        r = c.js_json(t, SETV + """
          var x=new XMLHttpRequest();x.open('GET',%s,false);x.send();var em=JSON.parse(x.responseText).success.miniApp.csEmail;
          var q=s=>document.querySelector(s);
          __setv(q('[name="step1.titleEn"]'),%s); __setv(q('input[placeholder^="사용자가 얻는 가치"]'),%s);
          __setv(q('textarea'),%s); __setv(q('[name="releaseNote"]'),%s); if(em) __setv(q('[name="step1.csEmail"]'),em);
          return !!em""" % (json.dumps(base + a.cs_from), json.dumps(bullet(section(md, '영어 이름'))), json.dumps(bullet(section(md, '부제'))),
                            json.dumps(det), json.dumps(bullet(section(md, '출시 노트')))))
        print('CS_EMAIL_COPIED', r)
        for i, label in enumerate(a.category.split('/')):
            c.js_json(t, "var e=[...document.querySelectorAll('[role=combobox]')][%d];e.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerType:'mouse'}));e.click();return 1" % i)
            time.sleep(1.2)
            ok = c.js_json(t, "var o=[...document.querySelectorAll('[role=option]')].find(o=>o.innerText.trim()==%s);if(!o)return 0;o.dispatchEvent(new PointerEvent('pointerup',{bubbles:true}));o.click();return 1" % json.dumps(label))
            if not ok and c.js_json(t, "return [...document.querySelectorAll('[role=combobox]')][%d].innerText" % i).strip() != label:
                raise RuntimeError(f'category {label} 없음')
            time.sleep(1)
        click_text(t, '임시저장'); time.sleep(3)
        click_text(t, '다음'); time.sleep(3)
        # 로고: 올리면 그 input 이 사라져서 두 번째도 index 0
        for p in [a.icon, a.dark_icon or a.icon]:
            files_into(t, "[...document.querySelectorAll('input[type=file][accept*=png]')][0]", [p])
        c.js_json(t, "var e=[...document.querySelectorAll('*')].filter(e=>e.childElementCount==0&&e.textContent.trim()=='스크린샷 이미지 직접 올리기').pop();(e.closest('button')||e).click();return 1")
        time.sleep(2)
        files_into(t, "[...document.querySelectorAll('input[type=file]')].find(e=>e.multiple)", [os.path.expanduser(p) for p in a.shots.split(',')])
        have = c.js_json(t, "return [...document.querySelectorAll('[data-tds-desktop-multi-select-autocomplete-chip]')].map(e=>e.innerText.trim())")
        for k in kws:
            if k in have:
                continue  # 키워드 칸: 첫 칩이 생기면 placeholder 가 사라져서 label for 로 찾는다
            c.js_json(t, SETV + ";var l=[...document.querySelectorAll('label')].find(l=>l.textContent.trim()=='앱 검색 키워드');var e=document.getElementById(l.htmlFor);"
                      "e.focus();__setv(e,%s);['keydown','keypress','keyup'].forEach(t=>e.dispatchEvent(new KeyboardEvent(t,{key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true})));return 1" % json.dumps(k))
            time.sleep(0.5)
        if a.submit:
            c.js_json(t, "document.querySelectorAll('input[type=checkbox]').forEach(e=>{if(!e.checked)e.click()});return 1")
        click_text(t, '임시저장'); time.sleep(3)
        d = xhr(t, 'GET', base + a.app)['success']['draft']
        state = {'titleEn': d['titleEn'], 'desc': d['description'], 'detail': len(d['detailDescription'] or ''), 'cs': bool(d['csEmail']),
                 'icon': bool(d['iconUri']), 'dark': bool(d['darkModeIconUri']), 'images': len(d['images']),
                 'keywords': d['impression']['keywordList'], 'category': [p['subCategory']['name'] for p in d['impression']['categoryPaths'] if p.get('subCategory')]}
        print('DRAFT', json.dumps(state, ensure_ascii=False))
        if not a.submit:
            print('RESULT: DRY_RUN 임시저장까지')
            return
        click_text(t, '검토 요청하기', last=True)
        time.sleep(5)
        msg = c.js_json(t, "return [...document.querySelectorAll('[role=status],[role=alert],[role=dialog]')].map(e=>e.innerText).filter(Boolean).join(' | ')")
        print('MSG', msg)
        print('RESULT:', 'REVIEW_REQUESTED' if '검토 중' in msg else 'CHECK_SCREEN')
    finally:
        c.js_json(t, "window.onbeforeunload=null;return 1")
        c.close_tab(t)


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('cmd', choices=['create', 'push', 'meta'])
ap.add_argument('app')
ap.add_argument('title', nargs='?')
ap.add_argument('--ws', default='35273')
ap.add_argument('--game', action='store_true')
ap.add_argument('--submit', action='store_true')
ap.add_argument('--deployment')
ap.add_argument('--store')
ap.add_argument('--icon')
ap.add_argument('--dark-icon')
ap.add_argument('--shots')
ap.add_argument('--category', default='생활/콘텐츠/운세')
ap.add_argument('--cs-from', default='oneul-kkum')
a = ap.parse_args()
{'create': cmd_create, 'push': cmd_push, 'meta': cmd_meta}[a.cmd](a)
