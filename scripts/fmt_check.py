#!/usr/bin/env python3
"""사용자가 읽는 글은 '짧은 제목' + '- 짧은 한 줄' 형식만(CLAUDE.md 최우선, 11/1 "내가 두번다시 이야기안한다").
11/28 M16(19회): CLAUDE.md엔 "보내기 전 코드 검사로 강제"라 적혔는데 검사가 없었다 → 이 파일.
check(text) -> 문제 목록(빈 목록이면 통과). CLI: fmt_check.py <파일|-> → RESULT: PASS|FAIL."""
import re, sys

MAXLEN = 90
# 11/28 "- 뿐만이아니라 한문장에 한줄": 문장 끝(마침표 없어도) 뒤에 말이 더 있거나, ' — '·';'로 두 말을 붙이면 두 문장
END = r"(?:어요|아요|해요|에요|예요|니다|했다|된다|한다|있다|없다|였다|었다|았다|했음|됐음|있음|없음|했어|됐어|돼요|세요)"
TWO = re.compile(END + r"(?:[.!?,]|\s*[—;:])?\s+(?=[가-힣A-Za-z0-9'\"(])")
JOIN = re.compile(r"\s—\s\S.{6,}|;\s+\S.{6,}")


def two_sentences(body):
    b = re.sub(r"\([^)]*\)|`[^`]*`|'[^']*'|\"[^\"]*\"", "", body)
    return bool(TWO.search(b) or re.search(r"[가-힣][.!?]\s+[가-힣]", b) or JOIN.search(b))


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
                if two_sentences(body):
                    errs.append(f"제목에 문장 두 개: {s[:30]}…")
                continue
            if l.startswith((" ", "\t")) and l.strip().startswith("- "):
                errs.append(f"들여쓴 목록 금지: {s[:30]}…")
            elif not s.startswith("- "):
                errs.append(f"'- ' 없는 줄: {s[:30]}…")
            if len(body) > MAXLEN:
                errs.append(f"줄이 {len(body)}자(>{MAXLEN}) — 의미 하나씩 나눠라: {s[:30]}…")
            if two_sentences(body[2:] if body.startswith("- ") else body):
                errs.append(f"한 줄에 문장 두 개 — 한 문장에 한 줄: {s[:30]}…")
    return errs



SPLIT = re.compile(r"(?<=[.!?])\s+(?!\d)|(?<=어요|아요|해요|에요|예요|니다|돼요|세요)\s+|\s+(?=[①②③④⑤⑥⑦⑧⑨⑩])|\s+·\s+|\s+/\s+|\s+—\s+|\s+→\s+|;\s+|\s+(?=\[(?:일부|틀림|맞음|미확인|해당없음)\])|\s+(?=[△⚠])")
ITEM_MAX = 90


def pieces(t, strip_label=True):
    """현황판·리스트가 '- ' 한 줄씩으로 나눠 보여 주는 조각(board.html sents()와 같은 규칙)."""
    m = re.match(r"^\s*[가-힣A-Za-z ]{1,8}:\s*", t or "") if strip_label else None
    body = (t or "")[m.end():] if m else (t or "")
    out = []
    for x in (y.strip() for y in SPLIT.split(body) if y and y.strip()):
        out += [z.strip() for z in re.split(r",\s+(?![^()]*\))|:\s+(?=\S)(?![^()]*\))", x) if z.strip()] if len(x) > 70 else [x]
    return out


def check_item(t, name=""):
    """카드·후보 칸 하나: 나눈 조각이 하나라도 ITEM_MAX자를 넘으면 문제(주소·괄호 속 주소는 길이에서 뺌)."""
    errs = []
    for x in pieces(t):
        n = len(re.sub(r"\(?https?://\S+\)?", "", x).strip())
        if n > ITEM_MAX:
            errs.append(f"{name} 한 줄 {n}자(>{ITEM_MAX}) — ' — '·' / '·'. '로 나눠 짧게: {x[:40]}…")
    return errs


def _wrap(x, n=ITEM_MAX):
    out = []
    while len(x) > n:
        cut = x.rfind(" ", 0, n)
        cut = cut if cut > 20 else n
        out.append(x[:cut].strip()); x = x[cut:].strip()
    return out + ([x] if x else [])


def fix(text):
    """자동 알림용: 아무 글이나 '제목 + - 줄' 모양으로 고친다(11/28 사람이 읽는 글 전부).
    빈 줄로 나뉜 덩어리마다 첫 줄=제목, 나머지는 pieces()로 나눠 '- ' 붙임. 주소만 있는 줄·표 줄은 그대로."""
    if not check(text):
        return text
    blocks, cur = [], []
    for l in (text or "").splitlines():
        if l.strip(): cur.append(l.strip())
        elif cur: blocks.append(cur); cur = []
    if cur: blocks.append(cur)
    out = []
    for b in blocks:
        head = re.sub(r"^[-•·*]\s+", "", b[0])
        hp = pieces(head, False) or [head]
        lines = [hp[0][:80]]
        rest = hp[1:] + b[1:]
        for l in rest:
            if re.match(r"^\s*(https?://\S+|\|)", l):
                lines.append(l); continue
            l = re.sub(r"^\s*[-•·*]\s+", "", l)
            for x in pieces(l, False) or [l]:
                lines += ["- " + y for y in _wrap(x, ITEM_MAX - 2)]
        out.append("\n".join(lines))
    return "\n\n".join(out)

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "--fix":
    sys.stdout.write(fix(sys.stdin.read())); sys.exit(0)
if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "-"
    txt = sys.stdin.read() if src == "-" else open(src, encoding="utf-8").read()
    e = check(txt)
    for x in e:
        print("-", x)
    print("RESULT:", "PASS" if not e else "FAIL")
    sys.exit(0 if not e else 1)
