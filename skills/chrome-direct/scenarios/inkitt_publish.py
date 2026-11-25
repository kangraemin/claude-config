#!/usr/bin/env python3
"""Inkitt 작품 게시 + 대회 참가 (실제 Chrome Profile 1, chromectl).

사용법:
  python3 inkitt_publish.py status --story-id 1959860
  python3 inkitt_publish.py publish --dir submission/강래민 --title "Rejected on Repeat" \
      --blurb blurb.md --cover cover.jpg [--notes notes.json] [--story-id N] \
      [--contest "A Novel Idea: First Draft 2026"] [--submit]

하는 일
- dir의 chNN.md(첫 줄 '# Chapter N: 제목', 장면 구분 '* * *', *기울임*)를 Quill 편집기에 붙여 넣는다.
- 장마다 이름·본문·작가 한마디(notes.json {"1":"..."})를 넣고 저장한다.
- 표지를 올린다: 업로드 → 배경 목록 마지막 칸 클릭 → SAVE.
- --submit이 있을 때만 장마다 Submit Chapter, 그 뒤 Settings > Participate in contest를 저장한다.
- 마지막에 API words_count 합계와 contest_entries를 출력한다.

멱등
- --story-id를 주면 이미 있는 장 수만큼 건너뛰고 남은 장만 만든다.
- Submitted 장은 다시 누르지 않는다.
- 이미 대회에 들어간 작품이면 대회를 다시 고르지 않는다.

사전 조건
- Profile 1에 Inkitt 로그인.
- 장르·태그·연령·AI 표시 같은 Settings 값은 사람이 정한다. 이 스크립트는 넣지 않는다(react-select, 작품마다 다름).

왜 화면 조작인가
- Inkitt에는 공개 작성 API가 없다. 내부 /api/3 은 읽기에만 쓴다.

함정
- 작가 한마디 편집기(.ql-editor 두 번째)는 앞 장 글이 남아 있다. 전체 선택 후 delete하고 붙인다.
- 장 이동 직후 작가 한마디 창이 이전 장 값을 보여 줄 수 있다. 확인은 /api/3/stories/<id>/chapters의 author_notes로 한다.
- 표지 업로드만 하면 반영이 안 된다. 배경 썸네일(.ve-background)을 눌러야 cover_settings가 저장된다.
- 대회 칸은 첫 장이 게시되기 전엔 'You must publish your story before you can participate!'로 잠겨 있다.
"""
import sys, os, json, re, time, argparse, html, subprocess
sys.path.insert(0, os.path.expanduser('~/.claude/skills/chrome-direct')); import chromectl as c
CTL = os.path.expanduser('~/.claude/skills/chrome-direct/chromectl.py')

def J(t, body, to=60):
    return c.js_json(t, body, timeout=to)

def load(path):
    lines = open(path).read().split('\n')
    title = re.sub(r'^#\s*Chapter\s+\d+:\s*', '', lines[0]).strip()
    blocks = [b.strip().replace('\n', ' ') for b in re.split(r'\n\s*\n', '\n'.join(lines[1:]).strip()) if b.strip()]
    segs = [[]]
    for b in blocks:
        if re.fullmatch(r'\*\s*\*\s*\*', b): segs.append([])
        else: segs[-1].append(b)
    inl = lambda s: re.sub(r'\*([^*\s][^*]*?)\*', r'<em>\1</em>', html.escape(s, quote=False))
    h = '<hr>'.join(''.join(f'<p>{inl(p)}</p>' for p in s) for s in segs)
    return title, h, sum(len(s) for s in segs), len(segs) - 1

PASTE = "const ed=document.querySelectorAll('.ql-editor')[%d]; ed.focus(); const dt=new DataTransfer(); dt.setData('text/html', %s); dt.setData('text/plain',''); ed.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true})); return 1"
SETV = "Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,%s); i.dispatchEvent(new Event('input',{bubbles:true})); i.dispatchEvent(new Event('change',{bubbles:true}));"
BTN = "const b=[...document.querySelectorAll('button')].filter(b=>b.innerText.trim()===%s&&b.getBoundingClientRect().width>0).pop(); if(!b) return 'NF'; b.click(); return 1"

def api_chapters(t, sid):
    return J(t, f"const x=new XMLHttpRequest(); x.open('GET','/api/3/stories/{sid}/chapters',false); x.send(); return JSON.parse(x.responseText).chapters.map(c=>({{n:c.chapter_number,name:c.name,status:c.status,words:c.words_count,note:(c.author_notes||'').replace(/<[^>]+>/g,'').replace(/\\ufeff/g,'')}}))")

def story(t, sid):
    return J(t, f"const x=new XMLHttpRequest(); x.open('GET','/api/stories/{sid}',false); x.send(); const s=JSON.parse(x.responseText); const t=s.story||s; return {{title:t.title, cover:t.cover_url, unpublished:t.unpublished, contests:(t.contest_entries||[]).map(e=>e.contest&&e.contest.name)}}")

def set_note(t, text):
    J(t, "const d=document.querySelector('.chapters-note > div'); ['mousedown','mouseup','click'].forEach(k=>d.dispatchEvent(new MouseEvent(k,{bubbles:true}))); return 1"); time.sleep(1.5)
    J(t, "const e=document.querySelectorAll('.ql-editor')[1]; e.focus(); const s=getSelection(); const r=document.createRange(); r.selectNodeContents(e); s.removeAllRanges(); s.addRange(r); document.execCommand('delete'); return 1")
    J(t, PASTE % (1, json.dumps('<p>' + html.escape(text, quote=False) + '</p>'))); time.sleep(0.8)
    J(t, "const e=document.querySelectorAll('.ql-editor')[1]; let p=e; for(let k=0;k<9&&p;k++){p=p.parentElement; if([...p.querySelectorAll('button')].some(b=>b.innerText.trim()==='Save')) break;} [...p.querySelectorAll('button')].find(b=>b.innerText.trim()==='Save').click(); return 1"); time.sleep(2)

def open_ch(t, n):
    J(t, "const b=[...document.querySelectorAll('button')].find(b=>{const L=b.innerText.trim().split('\\n').map(s=>s.trim()); return L.length>=2&&L[L.length-1]==='Chapter %d'}); if(!b) return 'NF'; b.click(); return 1" % n); time.sleep(4)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['status', 'publish'])
    ap.add_argument('--story-id'); ap.add_argument('--dir'); ap.add_argument('--title'); ap.add_argument('--blurb')
    ap.add_argument('--cover'); ap.add_argument('--notes'); ap.add_argument('--contest'); ap.add_argument('--submit', action='store_true')
    a = ap.parse_args()
    t = None
    try:
        if a.cmd == 'status':
            t = c.new_tab(f'https://www.inkitt.com/edit/{a.story_id}', profile='Profile 1'); time.sleep(8)
            chs = api_chapters(t, a.story_id); st = story(t, a.story_id)
            for x in chs: print(x['n'], x['status'], x['words'], x['name'], ('note=' + x['note']) if x['note'] else '')
            print(json.dumps(st, ensure_ascii=False)); print('TOTAL_WORDS', sum(x['words'] or 0 for x in chs))
            print('RESULT: OK'); return
        files = sorted(f for f in os.listdir(a.dir) if re.fullmatch(r'ch\d+\.md', f))
        notes = json.load(open(a.notes)) if a.notes else {}
        sid = a.story_id
        if not sid:
            t = c.new_tab('https://www.inkitt.com/manage-stories', profile='Profile 1'); time.sleep(8)
            if J(t, f"return document.body.innerText.includes({json.dumps(a.title)})"):
                print('RESULT: EXISTS (--story-id 로 이어서)'); return
            J(t, BTN % json.dumps('Create New')); time.sleep(8)
            sid = J(t, "return (location.pathname.match(/edit\\/(\\d+)/)||[])[1]")
            J(t, BTN % json.dumps('Edit Title')); time.sleep(1.5)
            J(t, "const m=[...document.querySelectorAll('*')].filter(e=>e.innerText&&e.innerText.startsWith('Change Story Title')&&e.querySelector('input')).pop(); const i=m.querySelector('input'); " + SETV % json.dumps(a.title) + " [...m.querySelectorAll('button')].find(b=>b.innerText.trim()==='Save').click(); return 1"); time.sleep(2)
        else:
            t = c.new_tab(f'https://www.inkitt.com/edit/{sid}', profile='Profile 1'); time.sleep(8)
        print('STORY', sid)
        have = api_chapters(t, sid)
        for idx, f in enumerate(files, 1):
            title, h, np, nhr = load(os.path.join(a.dir, f))
            if idx <= len(have) and (have[idx-1]['words'] or have[idx-1]['name'] == title): print('SKIP', idx); continue
            if idx == 1:
                pass  # 새 작품의 빈 Chapter 1 을 그대로 쓴다
            else:
                J(t, "const i=[...document.querySelectorAll('input[name=itemName]')].find(e=>e.placeholder==='Enter Chapter Name'); " + SETV % json.dumps(title) + " [...document.querySelectorAll('button')].find(b=>b.innerText.trim()==='Create Chapter').click(); return 1"); time.sleep(5)
            if not J(t, "return document.querySelector('.ql-editor').classList.contains('ql-blank')"): print('RESULT: FAIL editor not blank ch', idx); return
            J(t, PASTE % (0, json.dumps(h)), 90); time.sleep(2.5)
            got = J(t, "const ed=document.querySelector('.ql-editor'); return [ed.querySelectorAll('p').length, ed.querySelectorAll('hr').length]")
            if got != [np, nhr]: print('RESULT: FAIL count ch', idx, got, [np, nhr]); return
            J(t, BTN % json.dumps('Save')); time.sleep(3)
            if idx == 1:
                J(t, BTN % json.dumps('Rename')); time.sleep(1.2)
                J(t, "const i=[...document.querySelectorAll('input[name=itemName]')].find(e=>e.getBoundingClientRect().width>0&&e.placeholder!=='Enter Chapter Name'); " + SETV % json.dumps(title) + " i.closest('form').querySelector('button').click(); return 1"); time.sleep(2.5)
            if str(idx) in notes: set_note(t, notes[str(idx)])
            print('CH', idx, title, np, nhr)
        if a.blurb or a.cover:
            pass
        if a.cover and not story(t, sid)['cover']:
            J(t, "const p=document.querySelector('.vertical-cover__panel'); ['mouseover','mousedown','mouseup','click'].forEach(k=>p.dispatchEvent(new MouseEvent(k,{bubbles:true}))); return 1"); time.sleep(2)
            subprocess.run(['python3', CTL, 'upload', a.cover, '--match', t, '--sel', 'input[name=image]'], check=True); time.sleep(5)
            J(t, "const bg=[...document.querySelectorAll('.ve-background')].pop(); ['mousedown','mouseup','click'].forEach(k=>bg.dispatchEvent(new MouseEvent(k,{bubbles:true}))); return 1"); time.sleep(1.5)
            J(t, BTN % json.dumps('SAVE')); time.sleep(8)
            print('COVER', story(t, sid)['cover'])
        if a.blurb:
            print('NOTE: 요약·장르·태그·연령·AI 표시는 Settings에서 직접 넣는다(이 스크립트 범위 밖)')
        if not a.submit:
            print('RESULT: DRY_RUN', sid); return
        for x in api_chapters(t, sid):
            if x['status'] == 'public': continue
            J(t, BTN % json.dumps('Done')); open_ch(t, x['n']); J(t, BTN % json.dumps('Submit Chapter')); time.sleep(3.5)
            print('SUBMIT', x['n'])
        J(t, BTN % json.dumps('Done'))
        st = story(t, sid)
        if a.contest and a.contest not in st['contests']:
            J(t, 'location.reload(); return 1'); time.sleep(9)
            J(t, BTN % json.dumps('Settings')); time.sleep(3)
            J(t, "const s=[...document.querySelectorAll('.react-select__control')].filter(e=>e.getBoundingClientRect().width>0).pop(); const i=s.querySelector('.react-select__dropdown-indicator')||s; ['mousedown','mouseup','click'].forEach(k=>i.dispatchEvent(new MouseEvent(k,{bubbles:true,button:0}))); return 1"); time.sleep(1)
            r = J(t, "const o=[...document.querySelectorAll('.react-select__option')].find(o=>o.innerText.trim()===%s); if(!o) return 'NF'; ['mousedown','mouseup','click'].forEach(k=>o.dispatchEvent(new MouseEvent(k,{bubbles:true,button:0}))); return 1" % json.dumps(a.contest))
            if r == 'NF': print('RESULT: FAIL contest option not found'); return
            time.sleep(1); J(t, BTN % json.dumps('Save')); time.sleep(4)
            st = story(t, sid)
        chs = api_chapters(t, sid)
        print('TOTAL_WORDS', sum(x['words'] or 0 for x in chs), 'CONTESTS', st['contests'])
        print(f'RESULT: OK https://www.inkitt.com/stories/{sid}')
    finally:
        if t:
            try: c.close_tab(t)
            except Exception: pass

if __name__ == '__main__':
    main()
