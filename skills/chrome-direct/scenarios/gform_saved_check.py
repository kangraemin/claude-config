"""Read back a submitted Google Form response through '응답 수정' (edit2 link) and compare with answers.json.
Never presses 제출. For when the 응답 사본 메일 can't be received (e.g. mailbox over quota).
  gform_saved_check.py <form url> answers.json --profile "Profile 15" [--out saved.json] [--shot first.png]
Prints only key → MATCH/MISMATCH (values not printed). Last line RESULT: MATCH|MISMATCH|NO_RESPONSE|FAIL."""
import json
import re
import sys
import time

from _common import Blocked, emit, js, parser, run, tab
import _gform as g
import chromectl as c

ap = parser(__doc__)
ap.add_argument("url", help="폼 주소 또는 응답 수정(edit2) 링크")
ap.add_argument("answers")
ap.add_argument("--out", help="읽은 값 저장(json, 개인정보 포함 — 레포 밖에)")
ap.add_argument("--shot", help="응답 수정 첫 화면 캡처")
a = ap.parse_args()

VALUES = r"""
return [...document.querySelectorAll('div[role=listitem]')].filter(__vis).map(it => {
  const h = it.querySelector('[role=heading]');
  const title = h ? h.innerText.replace(/\s*\*\s*$/, '').trim() : '';
  const r = [...it.querySelectorAll('[role=radio][aria-checked=true],[role=checkbox][aria-checked=true]')]
    .map(e => e.getAttribute('data-value') || e.getAttribute('data-answer-value') || e.getAttribute('aria-label'));
  const t = [...it.querySelectorAll('input[type=text],input[type=email],input[type=date],input[type=number],input[type=tel],input:not([type]),textarea')]
    .filter(__vis).map(e => e.value).filter(Boolean);
  return {title, values: r.concat(t)};
}).filter(x => x.title);"""

norm = lambda s: re.sub(r"\s+", " ", str(s)).strip()


def main():
    answers = json.load(open(a.answers))
    with tab(a.url, a) as tid:
        st = g.state(tid, 40)
        if st["needsLogin"]:
            raise Blocked("LOGIN_REQUIRED")
        direct = "edit2=" in a.url  # 11/21 FiPA: 여러 번 응답 가능한 폼은 viewform에 '이미 응답' 표시가 없음 → edit2 링크를 바로 받음
        if not direct and not st["alreadyResponded"] and not st["editLink"]:
            emit({"url": st["url"]}, "NO_RESPONSE", "이 계정 응답 없음")
            return
        link = a.url if direct else js(tid, "const l=document.querySelector('a[href*=\"edit2=\"]'); return l ? l.href : null;")
        if not link:
            raise RuntimeError("응답 수정 링크 없음")
        if not direct:
            js(tid, f"location.href={json.dumps(link)}; return 1;")
            time.sleep(4)
            st = g.state(tid, 40)
        if a.shot:
            c.shot(tid, a.shot)
        saved = []
        for _ in range(15):
            saved += js(tid, VALUES)
            if "다음" not in st["buttons"] and "Next" not in st["buttons"]:
                break  # 마지막 쪽 — 제출은 누르지 않는다
            st = g.next_page(tid)
        if a.out:
            json.dump(saved, open(a.out, "w"), ensure_ascii=False, indent=1)
        res, ok = {}, True
        for k, v in answers.items():
            if k.startswith("__"):
                continue
            kk = re.sub(r"\s+", "", k)
            hit = [s for s in saved if re.sub(r"\s+", "", s["title"]).startswith(kk)]
            got = hit[0]["values"] if hit else []
            if isinstance(v, list):  # 11/21 FiPA: 체크박스 목록 값은 항목마다 대조
                m = all(norm(w) in [norm(x) for x in got] for w in v)
            else:
                want = norm(v)
                m = any(norm(x) == want or norm(x).replace("-", "") == want.replace("-", "") for x in got)
            res[k] = "MATCH" if m else ("MISSING" if not hit else "MISMATCH")
            ok &= m
        emit({"editUrl": link.split("edit2=")[0] + "edit2=…", "fields": res}, "MATCH" if ok else "MISMATCH")


run(main, a, "구글폼 응답 수정 화면에서 저장된 값 읽기(제출 금지)")
