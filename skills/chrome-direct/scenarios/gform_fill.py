#!/usr/bin/env python3
"""[제출] 구글폼 채우기 → (--submit 일 때만) 제출. 기본은 dry-run: 모든 쪽을 채우며 넘기고 마지막 '제출'은 안 누름.

answers.json = {"질문 제목(일부)": 값}. 값: 글자 / 라디오 선택지 글자 / 체크박스는 [목록] / 날짜 "YYYY-MM-DD" /
드롭다운 선택지 / {"file": "/abs/path"} (파일 업로드는 Google Picker라 스크립트 불가 → Codex로 넘김).
개인정보는 값 안에 {name} {phone} {email} {birth} {birth_iso} {address} {affiliation} 자리표시자로만 쓴다
(제천 build_application.py INFO에서 채움, 출력 안 함). gform_read --skeleton 으로 키 틀을 먼저 만든다.

  gform_fill.py <url> answers.json                          # dry-run (탭은 --keep-tab 이면 남김)
  gform_fill.py <url> answers.json --submit --contest-id housing-survey-poster --proof _radar/board/pdf/x-proof.pdf
'응답 수정'은 수정 링크(viewform?edit2=...)를 url로 주면 같은 방식으로 덮어쓴다(새 응답 만들지 않음).
"""
import json
import time
from pathlib import Path

from _common import Blocked, emit, expand, guard_and_lock, mark_not_sent, parser, personal_info, run, tab
from _gform import fill_page, next_page, press_button, state
import chromectl as c

ap = parser(__doc__, submit=True)
ap.add_argument("url")
ap.add_argument("answers")
ap.add_argument("--proof", help="제출 완료 화면 저장 (.png/.pdf)")
a = ap.parse_args()
RAW = json.loads(Path(a.answers).read_text())


def main():
    answers = {k: expand(v, personal_info()) for k, v in RAW.items()}
    lock, report = None, []
    with tab(a.url, a) as tid:
        st = state(tid)
        if st["needsLogin"]:
            raise Blocked("LOGIN_REQUIRED 구글 로그인 필요 — Chrome Profile 1에서 직접")
        if st["closed"]:
            raise Blocked("CLOSED 폼이 응답을 받지 않음")
        if st["alreadyResponded"]:
            raise Blocked("ALREADY_RESPONDED 이 계정으로 이미 응답함 — 고치려면 응답 수정 링크로")
        for page in range(1, 21):
            res = fill_page(tid, answers)
            time.sleep(0.6)
            st = state(tid)
            files = [r for r in res if r["status"] == "file"] + \
                    [{"title": x["title"], "status": "file"} for x in st["items"] if x["kind"] == "file" and x["required"]]
            if files:
                raise RuntimeError("파일 업로드 질문: " + ", ".join(sorted({f["title"] for f in files})))
            bad = [r for r in res if r["status"] not in ("filled",)]
            missing = [x["title"] for x in st["items"] if x["required"] and not x["answered"]]
            report.append({"page": page, "filled": [r["key"] for r in res if r["status"] == "filled"],
                           "problems": bad, "requiredUnanswered": missing})
            if bad or missing:
                raise RuntimeError(f"{page}쪽 채우기 실패: {bad or ''} 필수 미응답 {missing}")
            if "다음" in st["buttons"] or "Next" in st["buttons"]:
                next_page(tid)
                continue
            break
        used = {k for r in report for k in r["filled"]}
        unused = [k for k in answers if k not in used]
        if not any(b in st["buttons"] for b in ("제출", "Submit")):
            raise RuntimeError(f"제출 버튼이 없음: {st['buttons']}")
        if not a.submit:
            emit({"url": st["url"], "account": st["account"], "pages": report, "unusedKeys": unused},
                 "DRY_RUN", "다 채움 — 제출 안 함 (--submit 으로 제출)")
            return
        if unused:
            raise RuntimeError(f"answers 키가 폼에 없음: {unused}")
        lock = guard_and_lock(a.contest_id)
        try:
            press_button(tid, "제출" if "제출" in st["buttons"] else "Submit")
        except Exception as e:
            mark_not_sent(lock, f"제출 버튼 누르기 실패: {e}")
            raise
        end = time.time() + 30
        while time.time() < end:
            time.sleep(1)
            st = state(tid)
            if st["confirmation"]:
                break
        else:
            raise Blocked("UNCONFIRMED 제출은 눌렀으나 '응답이 기록되었습니다' 확인 못 함 — 재제출 금지, 메일함 '양식 응답 확인'·폼 화면을 사람이/확인용으로 볼 것")
        proof = c.shot(tid, a.proof) if a.proof else None
        if lock:
            (lock / "SENT.txt").write_text(f"{time.strftime('%Y-%m-%d %H:%M:%S')} gform {st['url']}\n")
        emit({"url": st["url"], "account": st["account"], "pages": report, "editLink": st["editLink"], "proof": proof},
             "SUBMITTED", a.contest_id or "")


TASK = (f"구글폼 {a.url} 을 remin1994@gmail.com 로그인된 Chrome에서 채워라. 값은 {a.answers} (JSON, 키=질문 제목 일부). "
        "{name} {phone} {email} {birth} {address} {affiliation} 자리표시자는 "
        "/Users/ram/programming/vibecoding/공모전/2026-10_제천AI데이터분석/submission/build_application.py 의 INFO 값으로 바꿔 넣고 "
        "{\"file\": 경로} 값은 그 파일을 업로드. "
        + ("모두 채운 뒤 '제출'을 한 번만 누르고 '응답이 기록되었습니다' 화면을 확인·캡처" + (f"해 {a.proof} 로 저장" if a.proof else "")
           + ". 이미 응답했거나 제출 버튼을 이미 눌렀던 흔적이 있으면 다시 제출하지 말고 STATUS: NEEDS_OWNER."
           if a.submit else "모두 채우되 '제출'은 절대 누르지 마라(dry-run). 채운 결과만 보고."))
run(main, a, TASK)
