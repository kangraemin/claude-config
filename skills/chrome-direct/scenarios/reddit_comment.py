#!/usr/bin/env python3
"""Reddit 글에 댓글 달기 (old.reddit.com, 실제 Chrome).

사용법:
  python3 reddit_comment.py <글 URL> <본문.txt> [--profile "Profile 5"] [--user oguriworks] [--submit]
  python3 reddit_comment.py --bio <소개.txt> [--profile ...] [--submit]   # 프로필 소개(about) 바꾸기

- 기본은 dry-run: 입력칸에 채우고 캡처까지만 한다(--submit일 때만 save 클릭).
- 멱등: 그 글에 --user가 이미 댓글을 달았으면 SKIP_EXISTS.
- 새 reddit(shreddit)은 댓글 입력칸이 높이 0인 contenteditable이라 JS 입력이 안 먹었다(11/6).
  old.reddit은 평범한 textarea + save 버튼이라 그쪽을 쓴다.
- 사전 조건: 그 Chrome 프로필이 reddit에 로그인돼 있어야 한다(아니면 BLOCKED).
마지막 줄: RESULT: OK <댓글 링크> | DRY_RUN <캡처> | SKIP_EXISTS | BLOCKED <이유> | FAIL <이유>
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.expanduser('~/.config/claude-accounts/personal/skills/chrome-direct'))
import chromectl as c

ap = argparse.ArgumentParser()
ap.add_argument('url', nargs='?')
ap.add_argument('textfile', nargs='?')
ap.add_argument('--profile', default='Profile 5')
ap.add_argument('--user', default='oguriworks')
ap.add_argument('--bio')
ap.add_argument('--submit', action='store_true')
ap.add_argument('--shot', default='/tmp/reddit_comment.png')
a = ap.parse_args()


def old(u):
    u = u.split('?')[0]
    for h in ('https://www.reddit.com', 'https://reddit.com', 'https://new.reddit.com'):
        if u.startswith(h):
            return 'https://old.reddit.com' + u[len(h):]
    return u


def logged_in(t):
    u = c.js_json(t, "const u=document.querySelector('#header .user a');return u&&u.textContent")
    return u


def do_comment(t):
    body = open(a.textfile).read().strip()
    c.goto(t, old(a.url)); time.sleep(6)
    who = logged_in(t)
    if not who or who.lower() != a.user.lower():
        return f'BLOCKED 로그인 계정 {who!r}'
    st = c.js_json(t, "return {mine:[...document.querySelectorAll('.comment .tagline a.author')].filter(x=>x.textContent.toLowerCase()==%s).length,"
                      "ta:!!document.querySelector('.commentarea > form.usertext textarea[name=text]'),"
                      "locked:!!document.querySelector('.locked-infobar, .archived-infobar')}" % json.dumps(a.user.lower()))
    if st['mine']:
        return 'SKIP_EXISTS'
    if not st['ta'] or st['locked']:
        return 'BLOCKED 댓글 칸 없음(잠김·보관·가입 필요)'
    c.js_json(t, "const ta=document.querySelector('.commentarea > form.usertext textarea[name=text]');"
                 "Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(ta,%s);"
                 "ta.dispatchEvent(new Event('input',{bubbles:true}));ta.dispatchEvent(new Event('change',{bubbles:true}));ta.focus();return 1" % json.dumps(body))
    if not a.submit:
        c.shot(t, a.shot)
        return f'DRY_RUN {a.shot}'
    c.js_json(t, "document.querySelector('.commentarea > form.usertext button[type=submit].save, .commentarea > form.usertext .usertext-buttons button.save').click();return 1")
    for _ in range(15):
        time.sleep(2)
        r = c.js_json(t, "const e=document.querySelector('.commentarea > form.usertext .error:not([style*=\"none\"])');"
                         "const m=[...document.querySelectorAll('.comment')].find(x=>{const au=x.querySelector('.tagline a.author');return au&&au.textContent.toLowerCase()==%s});"
                         "return {err:e&&e.textContent.trim(),link:m&&(m.querySelector('a.bylink')||{}).href}" % json.dumps(a.user.lower()))
        if r['link']:
            return f"OK {r['link'].replace('old.reddit.com','www.reddit.com')}"
        if r['err']:
            return f"FAIL {r['err'][:120]}"
    return 'FAIL 저장 확인 안 됨(내 댓글이 안 보임)'


def do_bio(t):
    bio = open(a.bio).read().strip()
    c.goto(t, 'https://www.reddit.com/settings/profile'); time.sleep(7)
    cur = c.js_json(t, "const ta=[...document.querySelectorAll('textarea')][0];return ta?ta.value:null")
    if cur is None:
        c.shot(t, a.shot)
        return f'FAIL 소개 칸 못 찾음 {a.shot}'
    if cur.strip() == bio:
        return 'SKIP_EXISTS'
    c.js_json(t, "const ta=[...document.querySelectorAll('textarea')][0];"
                 "Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(ta,%s);"
                 "ta.dispatchEvent(new Event('input',{bubbles:true}));ta.dispatchEvent(new Event('change',{bubbles:true}));ta.blur();ta.dispatchEvent(new Event('blur',{bubbles:true}));return 1" % json.dumps(bio))
    c.shot(t, a.shot)
    return f'DRY_RUN {a.shot}' if not a.submit else 'CHECK'


t = c.new_tab('https://old.reddit.com/', profile=a.profile)
res = 'FAIL'
try:
    res = do_bio(t) if a.bio else do_comment(t)
except Exception as e:
    res = f'FAIL {e}'
finally:
    if not res.startswith(('DRY_RUN', 'CHECK')):
        c.close_tab(t)
print('RESULT:', res)
