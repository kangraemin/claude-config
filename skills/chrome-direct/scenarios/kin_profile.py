#!/usr/bin/env python3
"""지식iN 프로필(별명·한줄 소개·상세 소개·연관 링크 1개) 채우고 저장한다.
사용: kin_profile.py --profile "Profile 5" --nick 오구리웍스 --summary "한 줄" --intro-file intro.txt \
        [--link-name "오늘꿈 생활 계산기" --link-url https://...] [--save]
  → 마지막 줄 RESULT: OK <프로필 주소> | SAME | DRY_RUN | FAIL <이유>

하는 일: kin.naver.com/myinfo/namecardProfileForm.naver를 새 탭으로 열고 → 값 채우기·동의 체크 2개 →
(--save) 저장 버튼 클릭 → 공개 프로필에서 값이 보이는지 확인.
사전 조건: 그 Chrome 프로필이 네이버에 로그인돼 있어야 한다(로그아웃이면 FAIL, naver_login 먼저).
왜 화면 조작인가: 지식iN 프로필 수정 API는 공개돼 있지 않다.
함정(2026-10-23)
- AppleScript `execute javascript`는 격리된 world라 페이지 변수(nhn, jindo)와 alert 덮어쓰기가 안 먹는다.
  저장 클릭은 <script> 태그를 넣어 페이지 world에서 해야 jindo 핸들러가 돈다.
- 별명·링크명은 한글·영문·숫자·공백만(가운뎃점 '·' 등 넣으면 alert로 막힘). 소개는 이모지만 막힌다.
- 네이버 서비스 최초 1회 동의가 안 돼 있으면 저장이 조용히 무시된다 →
  /myinfo/naverUserAgreedTermAjax.naver 가 false면 동의 페이지(commonTermAgree)를 먼저 연다.
- 모바일(m.kin) 프로필 화면엔 소개·링크 칸이 없다. PC 폼을 쓴다.
"""
import argparse, json, os, re, sys, time, urllib.parse
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

FORM = 'https://kin.naver.com/myinfo/namecardProfileForm.naver'
ALLOWED = re.compile(r'[^a-zA-Z0-9가-힣ㄱ-ㅎㅏ-ㅣ ]')


def page_js(t, code):
    c.js_json(t, "const s=document.createElement('script');s.textContent=%s;document.head.appendChild(s);return 1" % json.dumps(code, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', default='Profile 5')
    ap.add_argument('--nick', required=True)
    ap.add_argument('--summary', required=True)
    ap.add_argument('--intro-file', required=True)
    ap.add_argument('--link-name', default='')
    ap.add_argument('--link-url', default='')
    ap.add_argument('--save', action='store_true')
    a = ap.parse_args()
    intro = open(a.intro_file).read().strip()
    for name, v in (('별명', a.nick), ('링크명', a.link_name)):
        if ALLOWED.search(v):
            print('RESULT: FAIL', name, '에 한글·영문·숫자·공백 말고 다른 글자가 있음'); return
    if len(a.summary) > 30 or len(intro) > 200:
        print('RESULT: FAIL 한줄 30자·상세 200자 초과', len(a.summary), len(intro)); return
    t = c.new_tab(FORM, profile=a.profile)
    try:
        time.sleep(5)
        if 'namecardProfileForm' not in c.js_json(t, 'return location.href'):
            print('RESULT: FAIL 폼이 안 열림(로그아웃?)'); return
        cur = json.loads(c.js_json(t, "return JSON.stringify([...document.querySelectorAll('#nickname,#summaryIntroduction,#introduction,#urlDesc0,#url0')].map(e=>e.value))"))
        if cur == [a.nick, a.summary, intro, a.link_name or cur[3], a.link_url or cur[4]]:
            print('RESULT: SAME'); return
        agreed = c.js_json(t, "const x=new XMLHttpRequest();x.open('GET','/myinfo/naverUserAgreedTermAjax.naver',false);x.send();return x.responseText")
        if '"naverUserAgreedTerm":true' not in agreed:
            r = urllib.parse.quote(FORM, safe='')
            c.js_json(t, f"location.href='https://nid.naver.com/user2/help/commonTermAgree.nhn?cpcd=300&termcd=144&rurl={r}&curl={r}';return 1")
            time.sleep(7)
        vals = {'#nickname': a.nick, '#summaryIntroduction': a.summary, '#introduction': intro}
        if a.link_name:
            vals.update({'#urlDesc0': a.link_name, '#url0': a.link_url})
        code = """(function(){var log=[];var put=function(){document.body.setAttribute('data-kp',JSON.stringify(log))};
window.alert=function(m){log.push('A:'+m);put()};window.confirm=function(m){log.push('C:'+m);put();return true};
var V=%s;function setv(e,v){var p=e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;e.focus();
Object.getOwnPropertyDescriptor(p,'value').set.call(e,v);['input','change','keyup','blur'].forEach(function(x){e.dispatchEvent(new Event(x,{bubbles:true}))})}
var n2=document.querySelector('#set_nick2');if(!n2.checked)n2.click();for(var k in V)setv(document.querySelector(k),V[k]);
['agreeCheckProfileInfo','agreeCheckResponsibility'].forEach(function(id){var b=document.getElementById(id);if(!b.checked)b.click()});
log.push('filled');put();%s})();""" % (json.dumps(vals, ensure_ascii=False),
                                       "setTimeout(function(){document.querySelector('button._submit').click();log.push('clicked');put()},500);" if a.save else '')
        page_js(t, code)
        time.sleep(8 if a.save else 2)
        st = c.js_json(t, "return String(document.body.getAttribute('data-kp'))")
        if not a.save:
            print('STATE', st); print('RESULT: DRY_RUN'); return
        if 'A:' in st:
            print('RESULT: FAIL', st); return
        c.js_json(t, "location.href='https://kin.naver.com/myinfo/index.naver';return 1")
        time.sleep(6)
        txt = c.js_json(t, "return location.href+'\\n'+document.body.innerText")
        ok = a.nick in txt and a.summary in txt
        print('RESULT:', f'OK {txt.splitlines()[0]}' if ok else 'FAIL 저장 후 프로필에 안 보임')
    finally:
        c.close_tab(t)


if __name__ == '__main__':
    main()
