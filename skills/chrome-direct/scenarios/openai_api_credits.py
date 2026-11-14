"""ChatGPT Pro 구독 API 크레딧 받기·잔액 확인 (kangaiai1994, Chrome Profile 1) — 2026-11-14 처음 받음 $56, 매달 1일 $100.
사용: python3 openai_api_credits.py claim | balance | key
- claim: chatgpt.com/settings/billing '조직 연결' → 계속 → '연결하고 크레딧 받기'(이미 연결됐으면 그대로 끝)
- balance: platform 결제 화면의 API credit balance 출력
- key: 새 비밀 키(만료 안 함) 만들어 ~/.claude/.env OPENAI_API_KEY로 저장(값 출력 안 함)
주의: 크레딧을 받은 조직의 API 키로는 Codex를 못 씀(구독 Codex는 상관없음). 크레딧은 결제 주기 끝(매달 1일)에 사라짐.
"""
import os, re, subprocess, sys, time
CC = os.path.expanduser('~/.claude/skills/chrome-direct/chromectl.py')

def cc(*a):
    return subprocess.run(['python3', CC, *a], capture_output=True, text=True).stdout.strip()

def tab(url):
    out = cc('newtab', url); m = re.search(r'id:\d+', out); time.sleep(15); return m.group(0)

CLICK = "(()=>{const t=[...document.querySelectorAll('%s')].find(x=>x.innerText.trim()==='%s');if(!t)return 'none';['pointerdown','mousedown','pointerup','mouseup','click'].forEach(e=>t.dispatchEvent(new PointerEvent(e,{bubbles:true,button:0,pointerType:'mouse'})));return 'ok'})()"

def click(tid, text, sel='button'):
    r = cc('js', CLICK % (sel, text), '--match', tid); time.sleep(4); return r

def claim():
    t = tab('https://chatgpt.com/settings/billing')
    if click(t, '조직 연결') == 'none': print('RESULT: OK 이미 연결됨'); return
    click(t, '계속'); click(t, '연결하고 크레딧 받기')
    txt = cc('js', "(document.querySelector('[role=dialog]')||document.body).innerText.slice(0,300)", '--match', t)
    print('RESULT:', 'OK' if '연결되었습니다' in txt else 'FAIL ' + txt[:120])

def balance():
    t = tab('https://platform.openai.com/settings/organization/billing/overview')
    txt = cc('js', "document.body.innerText", '--match', t)
    m = re.search(r'API credit balance\s*(US\$[\d.,]+)', txt)
    print('RESULT:', ('OK ' + m.group(1)) if m else 'FAIL 잔액 못 읽음')

def key():
    t = tab('https://platform.openai.com/api-keys')
    click(t, 'Create new secret key')
    cc('js', CLICK % ('[role=button][aria-haspopup=dialog]', '만료\n만료일 선택').replace("innerText.trim()==='만료\n만료일 선택'", "innerText.includes('만료일')"), '--match', t)
    time.sleep(2); click(t, '만료 안 함', '[data-radix-popper-content-wrapper] div')
    click(t, 'Create secret key'); time.sleep(4)
    k = cc('js', "(()=>{const d=document.querySelector('[role=dialog]');return [...d.querySelectorAll('input,textarea')].map(x=>x.value).find(x=>/^sk-/.test(x))||(d.innerText.match(/sk-[A-Za-z0-9_\\-]{20,}/)||[''])[0]})()", '--match', t)
    if not k.startswith('sk-'): print('RESULT: FAIL 키 못 읽음'); return
    env = os.path.expanduser('~/.claude/.env'); s = open(env).read()
    s = re.sub(r'(?m)^OPENAI_API_KEY=.*\n?', '', s); s += ('' if s.endswith('\n') else '\n') + 'OPENAI_API_KEY=' + k + '\n'
    open(env, 'w').write(s); print('RESULT: OK 저장(길이 %d)' % len(k))

{'claim': claim, 'balance': balance, 'key': key}[sys.argv[1] if len(sys.argv) > 1 else 'balance']()
