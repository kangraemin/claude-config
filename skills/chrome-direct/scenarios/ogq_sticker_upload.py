#!/usr/bin/env python3
"""[제출] OGQ 크리에이터 스튜디오에 스티커 세트(24개+main+tab) 업로드 폼 채우기.

  ogq_sticker_upload.py <png_dir> --title T --desc D --tags a,b,c [--ai none|part|all] [--submit]

- png_dir: 01.png..24.png(740×640) + main.png(240×240) + tab.png(96×74). drafts/set-v3/ogq 처럼.
- 제목·설명·태그를 넣고, 26장을 일괄 업로드 칸에 drop 하고, AI 활용 여부를 고른다.
- --submit 이 있을 때만 「판매 등록」(무료 심사)을 누른다. 「빠른 심사 등록」(유료 C)은 누르지 않는다.
- 사전 조건: Profile 1 크롬에서 creators.ogq.me 로그인(OGQ_EMAIL/OGQ_PASSWORD), **크리에이터 스튜디오** 휴대폰 인증 완료
  (통합계정 oid.ogq.me/me 휴대전화 인증과 별개다. pass_sms_verify.py ogq-open → send → code, 사람 몫은 문자 6자리뿐).
- 심사 영업일 최대 15일, 심사 중 수정 불가.
- 왜 화면 조작인가: OGQ는 업로드 공개 API가 없다. 파일 칸은 input 없이 drop 이벤트만 받아 DataTransfer로 넣는다.
"""
import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/.config/claude-accounts/personal/skills/chrome-direct"))
import chromectl as c  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("png_dir")
ap.add_argument("--title", required=True)
ap.add_argument("--desc", required=True)
ap.add_argument("--tags", required=True)
ap.add_argument("--ai", default="all", choices=["none", "part", "all"])
ap.add_argument("--submit", action="store_true")
ap.add_argument("--keep", action="store_true", help="끝나도 탭을 닫지 않음(사람이 확인)")
a = ap.parse_args()
D = Path(a.png_dir).expanduser()
TAG = "input[type=text].input:not(.input-show-length)"  # 첫 태그 뒤 placeholder가 사라진다
FILES = [D / f"{i:02d}.png" for i in range(1, 25)] + [D / "main.png", D / "tab.png"]


def push(t, p):
    """파일을 base64 조각으로 페이지에 올려 window.__files 에 File 로 쌓는다."""
    b = base64.b64encode(p.read_bytes()).decode()
    c.run_js(t, "window.__b=''")
    for i in range(0, len(b), 400000):
        c.run_js(t, f"window.__b+={json.dumps(b[i:i + 400000])};1")
    c.run_js(t, f"""(()=>{{const s=atob(window.__b),u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);
      (window.__files=window.__files||[]).push(new File([u],{json.dumps(p.name)},{{type:'image/png'}}));return 1}})()""")


def main():
    miss = [p.name for p in FILES if not p.exists()]
    if miss:
        print("RESULT: BLOCKED 파일 없음", miss)
        return
    t = c.new_tab("https://creators.ogq.me/upload/sticker", profile="Profile 1")
    try:
        time.sleep(4)
        if "oid.ogq.me" in c.run_js(t, "location.href"):
            print("RESULT: BLOCKED OGQ 로그아웃 — oid.ogq.me 로그인 필요")
            return
        c.wait(t, sel="input[placeholder^='스티커의 제목']", timeout=30)
        c.fill(t, "input[placeholder^='스티커의 제목']", a.title)
        c.fill(t, "input[placeholder^='스티커를 간단하게']", a.desc)
        for tag in [x.strip() for x in a.tags.split(",") if x.strip()]:
            c.fill(t, TAG, tag)
            c.run_js(t, """(()=>{const e=document.querySelector(%s);
              for(const k of ['keydown','keypress','keyup'])e.dispatchEvent(new KeyboardEvent(k,{key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true}));return 1})()""" % json.dumps(TAG))
            time.sleep(0.3)
        c.run_js(t, "window.__files=[]")
        for p in FILES:
            push(t, p)
        c.run_js(t, """(()=>{const z=document.querySelector('.bulk-upload-zone'),dt=new DataTransfer();window.__files.forEach(f=>dt.items.add(f));
          for(const k of ['dragenter','dragover','drop'])z.dispatchEvent(new DragEvent(k,{dataTransfer:dt,bubbles:true,cancelable:true}));return 1})()""")
        time.sleep(8)
        idx = {"none": 0, "part": 1, "all": 2}[a.ai]
        c.run_js(t, f"document.querySelectorAll('input[type=radio]')[{idx}].click()")
        # 가이드 체크칸은 누르면 「마지막으로 확인해주세요!」 창이 뜨고, 그 창의 '확인'을 눌러야 체크된다
        c.run_js(t, """(()=>{const e=document.querySelector('.checkbox-item');if(!e.classList.contains('is-checked'))e.click();return 1})()""")
        time.sleep(1.5)
        c.run_js(t, """(()=>{const m=[...document.querySelectorAll('*')].find(e=>e.children.length==0&&e.textContent.trim()=='마지막으로 확인해주세요!');
          if(!m)return 0;let r=m;while(r.parentElement&&!r.querySelector('button'))r=r.parentElement;
          const b=[...r.querySelectorAll('button')].find(b=>b.innerText.trim()=='확인');setTimeout(()=>b.click(),10);return 1})()""")
        time.sleep(1.5)
        state = c.js_json(t, """return {title: document.querySelector("input[placeholder^='스티커의 제목']").value,
          imgs: [...document.querySelectorAll('.section-upload img')].length,
          ai: [...document.querySelectorAll('input[type=radio]')].map(r=>r.checked),
          guide: document.querySelector('.checkbox-item').classList.contains('is-checked'),
          twofa: document.body.innerText.includes('2단계 인증을 완료'),
          text: document.querySelector('.section-upload') ? document.querySelector('.section-upload').innerText.slice(0,300) : ''}""")
        print(json.dumps(state, ensure_ascii=False))
        c.shot(t, str(D / "upload-form.png"))
        if not a.submit:
            print("RESULT: FILLED (--submit 없음, 판매 등록 안 누름)")
            return
        if state["twofa"] or not state["guide"]:
            print("RESULT: BLOCKED 2단계 인증 미완료(pass_sms_verify.py ogq-open) 또는 가이드 체크 실패")
            return
        c.run_js(t, "setTimeout(()=>[...document.querySelectorAll('button')].find(b=>b.innerText.trim()==='판매 등록').click(),10)")
        time.sleep(8)
        body = c.page_text(t)
        print("RESULT:", "SUBMITTED" if "성공적으로 등록" in body else "UNKNOWN " + body[-300:].replace("\n", " / "))
    finally:
        if not a.keep:
            c.close_tab(t)


main()
