#!/usr/bin/env python3
"""움직이는 스티커를 '부품 그림 + 코드로 회전·이동 조립'으로 만들려 하면 막는다 (11/28 사용자 "코덱스로만하라고", "훅으로박아").
팔·몸 부품을 코드로 돌려 붙이면 팔이 몸과 따로 놀고 길이가 늘었다 줄었다 한다. 프레임은 Codex가 장면마다 몸 전체를 그린다.
막는 것 (스티커·이모티콘 작업 자리에서만):
- rig.py·rig2.py·motions.py 실행·작성
- Codex 지시문(FIX*.md·TASK*.md·NEXT*.md·codex exec 프롬프트)에 부품 시트·부품 조립·팔 회전 지시
- 코드에서 팔·부품을 rotate/affine으로 돌려 붙이기
허용: Codex가 그린 완성 프레임을 잘라(slice) 순서대로 잇기, 크기 맞추기, APNG/GIF 저장."""
import json, re, sys

PLACE = re.compile(r"kakao-emoticon|drafts/anim|line-anim-sticker|sticker|emoticon|스티커|이모티콘", re.I)
RIG_SCRIPT = re.compile(r"\b(rig2?|motions)\.py\b")
PROMPT_FILE = re.compile(r"/(FIX|TASK|NEXT|NEW)[^/]*\.md$", re.I)
PART_WORDS = re.compile(
    r"부품\s*(시트|조립|교체|을|를|으로|들)|parts?\s*sheet|part[- ]?based|assembl\w*\s+(the\s+)?(frames|parts)|"
    r"(팔|arm)\S*\s*(부품|part)|(팔|arm)\S*\s*(회전|rotate)|부품.{0,20}(회전|이동|붙여|조립)|"
    r"조립\s*(한다|해|하라|방식)|\brig\b|rigging|puppet|cut-?out\s+anim", re.I)
NEGATED = re.compile(r"(부품|parts?|rig|조립|회전)[^\n]{0,30}(금지|하지\s*마|않는다|말고|폐기|따르지|쓰지\s*않|\bno\b|\bnot\b|never|don't)", re.I)
CODE_ROT = re.compile(r"(arm|팔|part|부품)\w*[^\n]{0,80}\.(rotate|transform)\(|affine.{0,40}(arm|part|팔|부품)", re.I)


def blocked(text):
    for line in text.splitlines():
        if PART_WORDS.search(line) and not NEGATED.search(line):
            return line.strip()[:120]
    return None


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return 0
    ti = d.get("tool_input") or {}
    path = ti.get("file_path") or ""
    body = ti.get("command") or ti.get("content") or ti.get("new_string") or ""
    body = body.replace("block-sticker-part-rig", "")
    if "/.claude/hooks/" in path or "/claude-library/" in path or "/memory/" in path:
        return 0
    if not PLACE.search(path + "\n" + body):
        return 0
    why = None
    if RIG_SCRIPT.search(path) or re.search(r"python3?\s+\S*\b(rig2?|motions)\.py", body):
        why = "부품 조립 스크립트(rig.py·motions.py) 사용"
    elif PROMPT_FILE.search(path) or "codex exec" in body or "codex_console" in body:
        hit = blocked(body)
        if hit:
            why = f"Codex 지시에 부품 조립·회전 지시: '{hit}'"
    elif CODE_ROT.search(body):
        why = "코드로 팔·부품을 돌려 붙임"
    if not why:
        return 0
    sys.stderr.write(
        f"⛔ 움직이는 스티커를 부품+코드 조립으로 만들려 한다({why}). 11/28 사용자 '코덱스로만하라고'. "
        "Codex가 장면마다 몸 전체(팔·몸·표정이 한 덩어리)를 새로 그리게 지시하라. "
        "코드는 Codex가 그린 완성 프레임을 자르고·잇고·저장하는 것만 한다. "
        "부품 조립을 '하지 않는다'고 쓰려면 같은 줄에 '금지/하지 마/않는다'를 넣어라.\n")
    return 2


sys.exit(main())
