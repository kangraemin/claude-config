#!/usr/bin/env python3
"""[제출] 판매 중인 LINE 스티커에 언어(제목·설명)를 더해 업데이트 심사를 요청한다.

  line_add_language.py <sticker_id> --lang zh-Hant --title T --desc D [--submit]

- 상세 「Edit」(= /sticker/<id>/update_request) 폼에서 언어 추가 → 제목·설명 → 자동 판매(is-auto-release on) → 저장 → Request.
- --submit 이 없으면 폼만 채우고 저장하지 않는다(dry-run).
- 멱등: 상세 페이지에 그 언어 제목이 이미 있으면 아무것도 하지 않는다.
- 왜 화면 조작인가: LINE Creators Market은 API가 없다. 폼은 Vue라 setter+input 이벤트로 넣는다.
- 함정: 저장 확인창(Save this form?)은 [data-test=dialog-btn-ok]로 안 잡힌다 → U.click_ok.
- 함정: 판매 중 항목 업데이트는 심사 통과 시 자동 반영(그동안 기존 정보로 계속 판매). Request 창엔 I Agree 체크가 없다.
- 함정: 이미지는 판매 중 수정 불가. 텍스트·지역 수정은 업데이트 심사(update review)를 다시 받는다.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import line_sticker_upload as U  # noqa: E402

c = U.c
NAMES = {"zh-Hant": "Chinese (Traditional)", "zh-Hans": "Chinese (Simplified)", "ko": "Korean"}


def request(t, root, sid):
    """상세 페이지 Request(button) → 「Request Review」 창 OK. 업데이트 심사엔 I Agree 체크가 없다."""
    U.js(t, """(()=>{const a=[...document.querySelectorAll('a,button')].find(b=>b.offsetParent&&b.innerText.trim()=='Request');
      if(!a)return 0;setTimeout(()=>a.click(),10);return 1})()""")
    time.sleep(4)
    # click_ok(문구)로는 안 잡혔다 → 보이는 확인창 기본 버튼을 누른다
    U.js(t, "(()=>{const b=[...document.querySelectorAll('.cm-confirm-button-primary')].filter(b=>b.offsetParent).pop();if(!b)return 0;setTimeout(()=>b.click(),10);return 1})()")
    time.sleep(6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sid")
    ap.add_argument("--lang", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--desc", required=True)
    ap.add_argument("--submit", action="store_true")
    a = ap.parse_args()
    t = c.new_tab("https://creator.line.me/my/", profile="Profile 1")
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
        st, body = U.status(t, root, a.sid)
        if a.title.replace(" ", "") in body.replace(" ", ""):
            if "Editing" in " ".join(st) and a.submit:  # 저장만 되고 심사 요청 전
                request(t, root, a.sid)
                st, body = U.status(t, root, a.sid)
            print("RESULT: SKIP 이미 들어가 있음", " ".join(st))
            return
        c.goto(t, f"{U.BASE}{root}/sticker/{a.sid}/update_request")
        time.sleep(6)
        U.close_notices(t)
        if not U.jj(t, f"return !!document.querySelector('[name=\"meta[{a.lang}][title]\"]')"):
            U.select(t, "select-language", a.lang)
            U.js(t, "setTimeout(()=>document.querySelector('[data-test=btn-add-language]').click(),300);1")
            time.sleep(2)
        print("fill", U.set_values(t, {f"meta[{a.lang}][title]": a.title, f"meta[{a.lang}][description]": a.desc}))
        U.js(t, "(()=>{const e=document.querySelector('[data-test=is-auto-release-on] input')||document.querySelector('[data-test=is-auto-release-on]');e&&e.click();return 1})()")
        got = U.jj(t, f"return [document.querySelector('[name=\"meta[{a.lang}][title]\"]')?.value, document.querySelector('[name=\"meta[{a.lang}][description]\"]')?.value]")
        print("form", got)
        if got != [a.title, a.desc]:
            print("RESULT: BLOCKED 입력 불일치")
            return
        if not a.submit:
            print("RESULT: DRY-RUN 저장 안 함")
            return
        U.js(t, "setTimeout(()=>document.querySelector('[data-test=btn-save]').click(),300);1")
        time.sleep(3)
        U.click_ok(t, "Save this form")
        time.sleep(7)
        err = U.jj(t, "return [...document.querySelectorAll('[class*=rror]')].filter(e=>e.offsetParent&&e.innerText.trim()).map(e=>e.innerText.trim())")
        if "update_request" in U.js(t, "location.href") and err:
            print("RESULT: BLOCKED 저장 실패", err)
            return
        st, body = U.status(t, root, a.sid)
        print("after save:", " ".join(st))
        request(t, root, a.sid)
        st, body = U.status(t, root, a.sid)
        print("RESULT:", a.sid, " ".join(st))
    finally:
        c.close_tab(t)


if __name__ == "__main__":
    main()
