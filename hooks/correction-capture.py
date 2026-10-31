#!/usr/bin/env python3
"""UserPromptSubmit hook: 사용자가 화내거나 교정할 때, 같은 일이 또 안 나게 할 일을 주입한다.

2026-10-31 최근 3주 교정·욕설 메시지 442건 분석에서 반복된 유형:
  1. "먼말이여", "한글로 말해"            -> 영어·내부 용어 섞인 답
  2. "전에도", "몇 번 말해", "~하기로 했잖아" -> 이미 한 지적·결정을 잊음
  3. "내가 언제 이걸로 정했음"            -> Claude가 고른 걸 사용자가 정한 것처럼 말함
  4. 욕설 전반                              -> 확인 없이 넘김, 시킨 것 일부만 함
끄려면 CORRECTION_CAPTURE=off.
"""
import json
import os
import re
import sys

CONFUSED = re.compile(r"(먼말|뭔말|무슨 ?말|먼소리|뭔소리|뭔말하노|한글로|한국어로|이해가 ?안)")
REPEAT = re.compile(
    r"(전에도|전에 ?이렇게|전부터|전애부터|아까|몇 ?번|또 |또$|했잖|햇잖|했자나|햇자나|하기로 ?(했|햇|하지)|"
    r"않았|않앗|안 ?했|안 ?햇|분명히|이미 ?말|말했|말햇|기록 ?안)"
)
NOT_MINE = re.compile(r"내가 ?언제|누가 ?정했|누가 ?정햇|내가 ?그런 ?규칙")
ANGRY = re.compile(r"(씨발|시발|ㅅㅂ|ㅆㅂ|병신|개새|씹|좆|ㅈㄴ|미친|또라이|개소리|지랄|호로)")


def main():
    if os.environ.get("CORRECTION_CAPTURE", "on") == "off":
        return
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    p = (data.get("prompt") or "").strip()
    if not p or p.startswith("<") or len(p) > 1500:
        return
    notes = []
    if CONFUSED.search(p[:80]):
        notes.append(
            "직전 답을 사용자가 이해하지 못했다. 물은 것에 대한 결론 한 줄부터, 쉬운 한국어로 다시 말한다. "
            "영어·약어·내부 이름(파일명, 단계명, 도구명)은 빼거나 풀어 쓴다. 같은 말을 길게 반복하지 않는다."
        )
    if NOT_MINE.search(p):
        notes.append(
            "Claude가 고른 것을 사용자가 정한 것처럼 말했다. 그 결정을 사용자 결정으로 다루지 말고, "
            "'제가 고른 추천안'이라고 정정한 뒤 사용자 말에 맞게 바로 고친다. 앞으로 직접 고른 건 '추천안으로 진행'이라고 쓴다."
        )
    if REPEAT.search(p):
        notes.append(
            "사용자가 이미 한 지적·결정을 다시 말하고 있다. 고치기 전에 decision_search, 이 프로젝트 transcript"
            "(~/.claude/projects/*/*.jsonl, ~/.config/claude-accounts/*/projects/*/*.jsonl)에서 이전 지적을 찾아 "
            "원래 요구를 정확히 확인한다. 고친 뒤 실제로 실행·화면 확인으로 같은 문제가 없어졌는지 본다. "
            "이 교정은 decisions/<레포>/에 남긴다(이미 있으면 왜 안 지켜졌는지 한 줄 추가)."
        )
    if ANGRY.search(p) and not notes:
        notes.append(
            "사용자가 화났다. 사과·변명은 한 줄 이내. 무엇을 잘못했는지 한 줄, 바로 고치고, "
            "직접 실행·화면으로 확인한 결과로 보고한다. 시킨 것 중 빠진 게 없는지 원문과 대조한다."
        )
    if notes:
        ctx = "[correction-capture] " + " / ".join(notes)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}},
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
