#!/usr/bin/env python3
"""[읽기] 구글폼 구조 덤프 — 쪽별 질문 제목·필수·종류·선택지, 로그인 계정, 마감/이미 응답/응답 수정 여부.
'다음'은 필수 질문이 없는 쪽에서만 누른다(아무것도 입력·제출 안 함). gform_fill 의 answers.json 키를 정할 때 쓴다.

  gform_read.py https://forms.gle/XXXX
  gform_read.py <url> --skeleton answers.json      # 질문 제목을 키로 한 빈 answers 틀 저장
"""
import json
from pathlib import Path

from _common import Blocked, emit, parser, run, tab
from _gform import next_page, state

ap = parser(__doc__)
ap.add_argument("url")
ap.add_argument("--skeleton", help="answers.json 틀 저장 경로")
a = ap.parse_args()


def main():
    with tab(a.url, a) as tid:
        st = state(tid)
        if st["needsLogin"]:
            raise Blocked("LOGIN_REQUIRED 이 폼은 구글 로그인이 필요 — Chrome Profile 1에서 직접 로그인")
        info = {k: st[k] for k in ("url", "title", "account", "closed", "alreadyResponded", "confirmation", "editLink")}
        pages, stop = [], ""
        for _ in range(15):
            pages.append({"items": st["items"], "buttons": [b for b in st["buttons"] if b in ("다음", "뒤로", "제출", "Next", "Back", "Submit")]})
            if not any(b in st["buttons"] for b in ("다음", "Next")):
                stop = "마지막 쪽(제출 버튼)" if any(b in st["buttons"] for b in ("제출", "Submit")) else "다음 버튼 없음"
                break
            if any(x["required"] and not x["answered"] for x in st["items"]):
                stop = "이 쪽에 필수 질문 — 이후 쪽은 답을 넣어야 보임 (gform_fill dry-run으로 확인)"
                break
            st = next_page(tid)
        info["pages"], info["stoppedBecause"] = pages, stop
        if a.skeleton:
            sk = {x["title"]: (x["options"][:1] if x["kind"] == "checkbox" else x["options"][0] if x["options"] else "")
                  if x["kind"] != "file" else {"file": ""} for p in pages for x in p["items"] if x["kind"] not in ("section",)}
            Path(a.skeleton).write_text(json.dumps(sk, ensure_ascii=False, indent=1))
            info["skeleton"] = a.skeleton
        emit(info, "OK", f"{len(pages)} pages, {sum(len(p['items']) for p in pages)} items")


run(main, a, f"READ ONLY. 구글폼 {a.url} 을 열어 쪽마다 질문 제목·필수 여부·종류·선택지를 출력. 아무것도 입력·제출하지 마라(필수 질문 있는 쪽에서 멈춤).")
