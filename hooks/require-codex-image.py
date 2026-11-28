#!/usr/bin/env python3
"""그림(캐릭터·이모티콘·스티커·삽화·마스코트·표지·스프라이트)을 코드로 그리면 막는다 (11/28 M10, 27회 — "이미지생성같은건 코덱스로만").
Bash·Write 내용에 그리기 코드(ImageDraw·cairo·svgwrite·<svg·matplotlib patches)가 있고 대상 경로가 그림 자리인데,
이번 사용자 말 뒤에 codex 실행이 없으면 막는다. 흐름·비교 도식(diagram·figure·chart·도식)은 코드로 그려도 된다."""
import json, re, sys
DRAW = re.compile(r"ImageDraw|\bcairo\b|svgwrite|<svg[\s>]|patches\.(Circle|Ellipse|Polygon)|draw\.(ellipse|polygon|pieslice)")
ART = re.compile(r"sprite|emoticon|sticker|character|illust|mascot|cover|thumbnail|캐릭터|이모티콘|스티커|삽화|마스코트|표지|썸네일", re.I)
OK = re.compile(r"diagram|figure|fig\d|chart|도식|표\d|flow|graph|qr", re.I)


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return 0
    ti = d.get("tool_input") or {}
    body = ti.get("command") or ti.get("content") or ti.get("new_string") or ""
    where = (ti.get("file_path") or "") + "\n" + body
    if not DRAW.search(body) or not ART.search(where) or OK.search(ti.get("file_path") or ""):
        return 0
    try:
        lines = open(d["transcript_path"], encoding="utf-8").read().splitlines()[-500:]
    except Exception:
        return 0
    for l in reversed(lines):
        try:
            e = json.loads(l)
        except Exception:
            continue
        if e.get("type") == "user" and isinstance((e.get("message") or {}).get("content"), str):
            break
        if "codex exec" in l or "codex_console" in l or "codex-img" in l:
            return 0
    sys.stderr.write("⛔ 그림 자리(캐릭터·스티커·표지 등)를 코드로 그리려 한다(11/28 M10, '이미지생성같은건 코덱스로만'). "
                     "Codex(codex exec 그림 job)로 그린다. Codex가 막혔으면 log/codex-image-todo.md에 '- [ ] 코덱스 필요: <자리>'와 프롬프트를 적고 멈춘다. "
                     "흐름·비교 도식이면 파일 이름에 diagram/도식을 넣어라.\n")
    return 2


sys.exit(main())
