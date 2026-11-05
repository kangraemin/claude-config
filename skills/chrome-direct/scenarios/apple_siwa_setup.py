#!/usr/bin/env python3
"""Sign in with Apple 웹 로그인 준비: App ID + Services ID(도메인·Return URL) + 키(.p8).

사용: apple_siwa_setup.py <bundle_id> <app_name> <service_id> <domain> <return_url> <key_name> --out <p8경로> [--submit]
  --submit 없으면 현재 상태만 출력한다(만들지 않음). 있으면 빠진 것만 만든다(멱등).

전제: Chrome Profile 1에 Apple Developer 로그인. 로그아웃이면 RESULT: BLOCKED login.
  로그인 순서(2026-11-05 확인): idmsa 화면에서 '패스키로 로그인' 실제 클릭 → Mac 시트 '계속'.
  이메일칸 드롭다운은 패스키 항목을 눌러도 시트가 안 뜰 수 있고, 저장 비밀번호가 채워지면 틀린 값일 수 있다.
  Mac 패스키 시트가 cliclick 클릭을 무시하면 `cliclick kp:return`으로 확인한다(2026-11-06 확인).
왜 화면 조작: Sign in with Apple 설정은 App Store Connect API로 만들 수 없다.
함정:
  - 키 주소는 keys/가 아니라 authkeys/. 키 파일은 한 번만 받을 수 있어 받자마자 --out으로 옮긴다(600).
  - 키 이름에 - . 금지. Configure 버튼은 체크박스를 켠 뒤 다시 그려져 id가 바뀌므로 줄/글자로 찾는다.
  - App ID 폼은 체크박스 수가 많고, 입력은 native setter를 쓴다. const를 전역에 두면 두 번째 실행에서 오류가 나므로 IIFE로 감싼다.
  - 앱 ID는 Services ID 설정의 Primary App ID가 되므로 먼저 만든다.
"""
import argparse, json, os, shutil, sys, time
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

BASE = 'https://developer.apple.com/account/resources/'
SET = ("const S=(i,v,P)=>{i.focus();Object.getOwnPropertyDescriptor(P.prototype,'value').set.call(i,v);"
       "['input','change','blur'].forEach(n=>i.dispatchEvent(new Event(n,{bubbles:true})));};")
TEXT_ROW = ("const R=(t,sel)=>{const w=document.createTreeWalker(document.querySelector('main'),NodeFilter.SHOW_TEXT);let n;"
            "while(n=w.nextNode()){if(n.textContent.trim()===t){let e=n.parentElement;while(e&&!e.querySelector(sel))e=e.parentElement;return e}}return null};")


def main():
    p = argparse.ArgumentParser()
    for a in ('bundle_id', 'app_name', 'service_id', 'domain', 'return_url', 'key_name'):
        p.add_argument(a)
    p.add_argument('--out', required=True)
    p.add_argument('--submit', action='store_true')
    a = p.parse_args()
    t = c.new_tab(BASE + 'identifiers/list', 'Profile 1')

    def J(code):
        return c.run_js(t, code)

    def go(path, wait=7):
        J(f"location.href={json.dumps(BASE + path)};1")
        time.sleep(wait)

    def btn(label):
        return J(f"(()=>{{const b=[...document.querySelectorAll('button,a')].find(x=>x.textContent.trim()==={json.dumps(label)}&&!x.disabled);if(!b)return 'NOBTN';b.click();return 'ok'}})()")

    def has(text):
        return J(f"String(document.body.innerText.includes({json.dumps(text)}))") == 'true'

    def fill(el, value, proto='HTMLInputElement'):
        return J(f"(()=>{{{SET}S(document.getElementById({json.dumps(el)}),{json.dumps(value)},{proto});return 1}})()")

    try:
        time.sleep(8)
        if 'idmsa.apple.com' in J('location.href'):
            print('RESULT: BLOCKED login')
            return 2

        have_app = has(a.bundle_id + '\n')
        print('APPID:', 'have' if have_app else 'missing')
        go('identifiers/list/serviceId')
        have_svc = has(a.service_id)
        print('SERVICE:', 'have' if have_svc else 'missing')
        go('authkeys/list')
        have_key = has(a.key_name)
        print('KEY:', 'have' if have_key else 'missing')
        if not a.submit:
            print('RESULT: DRY_RUN')
            return 0

        if not have_app:
            go('identifiers/add/bundleId')
            btn('Continue'); time.sleep(3)
            J(f"(()=>{{{TEXT_ROW}R('App','input[type=radio]').querySelector('input[type=radio]').click();return 1}})()")
            btn('Continue'); time.sleep(4)
            fill('description', a.app_name); fill('identifier', a.bundle_id)
            J(f"(()=>{{{TEXT_ROW}R('Sign In with Apple','input[type=checkbox]').querySelector('input[type=checkbox]').click();return 1}})()")
            time.sleep(1); btn('Continue'); time.sleep(4); btn('Register'); time.sleep(6)

        if not have_svc:
            go('identifiers/add/bundleId')
            J(f"(()=>{{{TEXT_ROW}R('Services IDs','input[type=radio]').querySelector('input[type=radio]').click();return 1}})()")
            btn('Continue'); time.sleep(4)
            fill('description', a.app_name + ' Web'); fill('identifier', a.service_id)
            time.sleep(1); btn('Continue'); time.sleep(4); btn('Register'); time.sleep(6)
            go('identifiers/list/serviceId')
            J(f"(()=>{{const e=[...document.querySelectorAll('*')].find(x=>x.children.length===0&&x.textContent.trim()==={json.dumps(a.service_id)});(e.closest('a')||e).click();return 1}})()")
            time.sleep(5)
            J("(()=>{const c=document.getElementById('APPLE_ID_AUTH');if(!c.checked)c.click();return 1})()")
            time.sleep(1); btn('Configure'); time.sleep(3)
            fill('domainsInput', a.domain, 'HTMLTextAreaElement'); fill('urlsInput', a.return_url, 'HTMLTextAreaElement')
            time.sleep(1); J("(()=>{document.getElementById('action-save').click();return 1})()"); time.sleep(3)
            btn('Done'); time.sleep(2); btn('Continue'); time.sleep(4); btn('Save'); time.sleep(5)

        if not have_key:
            go('authkeys/add')
            fill('name', a.key_name)
            J("(()=>{const c=document.getElementById('APPLE_ID_AUTH_KEY_CONFIGURATION');if(!c.checked)c.click();return 1})()"); time.sleep(1)
            J("(()=>{let e=document.getElementById('APPLE_ID_AUTH_KEY_CONFIGURATION');while(e&&!e.querySelector('button'))e=e.parentElement;e.querySelector('button').click();return 1})()"); time.sleep(4)
            J("(()=>{const i=document.querySelector('input[id^=react-select]');i.closest('[class*=control]').dispatchEvent(new MouseEvent('mousedown',{bubbles:true,button:0}));return 1})()"); time.sleep(2)
            picked = J(f"(()=>{{const o=[...document.querySelectorAll('[role=option],[id*=-option-]')].find(x=>x.textContent.includes({json.dumps(a.bundle_id)}));if(!o)return 'NO';o.click();return 'ok'}})()")
            if picked != 'ok':
                print('RESULT: FAIL primary app id not listed')
                return 1
            time.sleep(2); btn('Save'); time.sleep(3); btn('Continue'); time.sleep(4); btn('Register'); time.sleep(6)
            kid = J("(()=>{const m=document.body.innerText.match(/Key ID:\\s*([A-Z0-9]{10})/);return m?m[1]:''})()")
            if not kid:
                print('RESULT: FAIL no key id')
                return 1
            btn('Download'); time.sleep(6)
            src = os.path.expanduser(f'~/Downloads/AuthKey_{kid}.p8')
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            shutil.move(src, a.out); os.chmod(a.out, 0o600)
            print('KEY_ID:', kid)
        print('RESULT: OK')
        return 0
    finally:
        try:
            c.close_tab(t)
        except Exception:
            pass


if __name__ == '__main__':
    sys.exit(main())
