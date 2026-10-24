#!/usr/bin/env python3
"""[제출] 이미 심사 요청한 LINE 스티커 세트의 그림을 통째로 바꾸고 다시 심사 요청한다.

  line_replace_images.py <sticker_id> <png_dir> [--submit]

- png_dir: 01~24.png + main.png + tab.png (line_sticker_upload.py 와 같은 규격).
- 순서: 상세 화면 'Revert to Edit' → OK(요청 취소, 편집 상태) → 이미지 화면에 zip 업로드 → 개수 24 확인 → --submit 이면 Request + I Agree + OK.
- 함정:
  - 심사 취소 후 재요청하면 'Waiting for Review' 맨 뒤로 간다(확인창 문구). 그림을 꼭 바꿔야 할 때만 쓴다.
  - 한 번 요청된 항목은 이미지 개수 칸이 사라진다 → line_sticker_upload.upload(replace=True)로 개수 선택을 건너뛴다.
  - 판매 중(Approved) 세트의 그림 교체는 별도 업데이트 심사라 이 스크립트 대상이 아니다(미검증).
"""
import argparse
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import line_sticker_upload as U  # noqa: E402

c = U.c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sid")
    ap.add_argument("png_dir")
    ap.add_argument("--submit", action="store_true")
    a = ap.parse_args()
    D = Path(a.png_dir).expanduser()
    files = [D / f"{i:02d}.png" for i in range(1, 25)] + [D / "main.png", D / "tab.png"]
    if [p for p in files if not p.exists()]:
        print("RESULT: BLOCKED 파일 없음")
        return
    t = c.new_tab(U.BASE, profile="Profile 1")
    try:
        time.sleep(5)
        root = U.my_root(t)
        if not root and U.jj(t, "return !!document.querySelector('input[name=tid]')"):
            U.login(t)
            c.goto(t, U.BASE)
            time.sleep(5)
            root = U.my_root(t)
        if not root:
            print("RESULT: BLOCKED 로그인 실패")
            return
        st, _ = U.status(t, root, a.sid)
        print("before", st)
        if "Waiting for Review" in " ".join(st) or "In Review" in " ".join(st):
            U.js(t, "(()=>{const a=[...document.querySelectorAll('a,button')].find(b=>b.innerText.trim()=='Revert to Edit');setTimeout(()=>a.click(),10);return 1})()")
            time.sleep(2)
            U.click_ok(t, "Revert to Edit")  # 본문 문구는 여러 노드로 쪼개져 잎 노드 검사에 안 걸린다
            time.sleep(6)
            st, _ = U.status(t, root, a.sid)
            print("reverted", st)
        if "Editing" not in " ".join(st):
            print("RESULT: BLOCKED 편집 상태 아님", st)
            return
        empty = U.upload(t, root, a.sid, files, replace=True)
        st, body = U.status(t, root, a.sid)
        m = re.search(r"No\. of Stickers per Set\s*(\d+)", body)
        print("empty slots", empty, "count", m and m.group(1), st)
        if empty or not m or m.group(1) != "24" or "required images have not been uploaded" in body:
            print("RESULT: BLOCKED 업로드 확인 실패", a.sid)
            return
        if not a.submit:
            print("RESULT: REPLACED", a.sid, "(--submit 없음)")
            return
        U.js(t, """(()=>{const a=[...document.querySelectorAll('a')].find(b=>b.innerText.trim()=='Request');
          setTimeout(()=>a.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true})),10);return 1})()""")
        time.sleep(5)
        U.js(t, """(()=>{const cb=[...document.querySelectorAll('input[type=checkbox]')].find(e=>(e.closest('label')||e.parentElement).innerText.trim()=='I Agree');
          if(!cb.checked)cb.click();let d=cb;while(d.parentElement&&!d.querySelector('button'))d=d.parentElement;
          const b=[...d.querySelectorAll('button')].find(b=>b.innerText.trim()=='OK');setTimeout(()=>b.click(),10);return 1})()""")
        time.sleep(6)
        st, _ = U.status(t, root, a.sid)
        print("RESULT:", "SUBMITTED " + a.sid if "Waiting for Review" in " ".join(st) else f"UNKNOWN {a.sid} {st}")
    finally:
        c.close_tab(t)


if __name__ == "__main__":
    main()
