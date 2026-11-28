#!/usr/bin/env python3
"""사용자가 읽는 글은 '짧은 제목' + '- 짧은 한 줄' 형식만(CLAUDE.md 최우선, 11/1 "내가 두번다시 이야기안한다").
11/28 M16(19회): CLAUDE.md엔 "보내기 전 코드 검사로 강제"라 적혔는데 검사가 없었다 → 이 파일.
check(text) -> 문제 목록(빈 목록이면 통과). CLI: fmt_check.py <파일|-> → RESULT: PASS|FAIL."""
import re, sys

MAXLEN = 90


def check(text):
    errs = []
    t = re.sub(r"```.*?```", "", text or "", flags=re.S)
    for bi, block in enumerate(re.split(r"\n\s*\n", t.strip())):
        lines = [l.rstrip() for l in block.splitlines() if l.strip()]
        for i, l in enumerate(lines):
            s = l.strip()
            if re.fullmatch(r"https?://\S+", s) or s.startswith("|"):
                continue  # 주소만 있는 줄·표
            body = re.sub(r"https?://\S+", "", s)
            if i == 0:
                if s.startswith("- "):
                    errs.append(f"{bi + 1}번째 덩어리: 제목 없이 '- ' 줄로 시작")
                if len(body) > MAXLEN:
                    errs.append(f"제목이 {len(body)}자(>{MAXLEN}): {s[:30]}…")
                if re.search(r"[가-힣](다|요|음|함)\.\s+\S", body):
                    errs.append(f"제목에 문장 두 개: {s[:30]}…")
                continue
            if l.startswith((" ", "\t")) and l.strip().startswith("- "):
                errs.append(f"들여쓴 목록 금지: {s[:30]}…")
            elif not s.startswith("- "):
                errs.append(f"'- ' 없는 줄: {s[:30]}…")
            if len(body) > MAXLEN:
                errs.append(f"줄이 {len(body)}자(>{MAXLEN}) — 의미 하나씩 나눠라: {s[:30]}…")
            if len(re.findall(r"[가-힣](다|요|음|함)\.\s+\S", body)) >= 1:
                errs.append(f"한 줄에 문장 두 개: {s[:30]}…")
    return errs


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "-"
    txt = sys.stdin.read() if src == "-" else open(src, encoding="utf-8").read()
    e = check(txt)
    for x in e:
        print("-", x)
    print("RESULT:", "PASS" if not e else "FAIL")
    sys.exit(0 if not e else 1)
