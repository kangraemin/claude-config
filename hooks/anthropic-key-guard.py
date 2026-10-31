#!/usr/bin/env python3
"""Anthropic API 키는 정해진 레포에서만 쓴다(사용자 10/25 "썸이랑 상권.kr 만 내개인 api 키 쓰고 나머진 전부 못쓰도록").
- 개인 키: 썸판독기(money-web), 상권.kr(area-insight)
- 회사 키: ai-paper (사용자 10/25 "ai paper는 회사꺼쓰라고")
- 민구형 키: 먹맵(mukmap) 번역, 상권.kr(10/28부터), 강화 서바이버(defense-game) 번역(10/30, 상한 $100), youtubeScript 먹맵 추출·경제 요약(10/31), 오늘의 눈썰미(spot-difference) 13개 언어 번역(10/31, 상한 $50), my-sns 스레드 답글 생성(10/31, 키 다 쓰면 claude -p로)
그 밖의 곳에서 키를 넘기거나(export·$VAR·secret put), api.anthropic.com 을 직접 부르거나, sk-ant- 키를 파일에 쓰면 막는다.
사용자만 끌 수 있다: Claude Code 를 ANTHROPIC_KEY_GUARD_OFF=1 로 띄운다.
"""
import json
import os
import re
import sys

V = os.path.expanduser('~/programming/vibecoding/')
ALLOW = {
    V + 'money-web': {'SSUM_ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY'},
    # 상권.kr: 10/28부터 민구형 키 (사용자 10/28 "상권.kr 민구형 api 키값쓰도록바꿔주고")
    V + 'area-insight': {'AREA_INSIGHT_ANTHROPIC_API_KEY', 'MUKMAP_ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY'},
    V + 'ai-paper': {'AI_PAPER_GC_ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY'},
    # 먹맵 번역: 민구형 키 (사용자 10/25 "먹맵번역에쓸거라구", "ㅇㅇ 그렇게해")
    V + 'mukmap': {'MUKMAP_ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY'},
    # 강화 서바이버 번역: 민구형 키 상한 $100 (사용자 10/30 "민구형 api key활용해서 번역해 100달러상한으로")
    V + 'defense-game': {'MUKMAP_ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY'},
    # 먹맵 추출·경제 요약(youtubeScript): 민구형 키 (사용자 10/31 "민구형꺼쑤", "api key로 다해 한도없어 이번엔 그냥다써야함")
    # 오늘의 눈썰미 13개 언어 번역: 민구형 키 상한 $50 (사용자 10/31 "번역은전부민구형api key로", "오늘의눈썰미 저거 전부번역하자 13개언어로")
    V + 'spot-difference': {'MUKMAP_ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY'},
    V + 'youtubeScript': {'MUKMAP_ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY'},
    # my-sns 스레드 답글 생성: 민구형 키 (사용자 10/31 "댓글 생성하는거 claude -p 말고 api key로", "api 민구형꺼 다쓰면 그때 claude -p 로전환하자")
    V + 'my-sns': {'MUKMAP_ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY'},
}
NAME = r'([A-Z][A-Z0-9_]*_)?ANTHROPIC_API_KEY'
EXPAND = re.compile(r'\$\{?(' + NAME + r')\b')
ASSIGN = re.compile(r'(?:^|[\s;&|(])(?:export\s+)?(' + NAME + r')=', re.M)
SECRET = re.compile(r'(?:secret\s+(?:put|set)|env\s+add)\s+(' + NAME + r')\b')
SOURCE = re.compile(r'(?:^|[\s;&|(])(?:source|\.)\s+([^\s;&|)]+)', re.M)
CD = re.compile(r'(?:^|[\s;&|(])cd\s+([^\s;&|)]+)', re.M)
KEY = re.compile(r'sk-ant-[A-Za-z0-9_-]{8,}')
BARE = re.compile(r'^\s*(?:export\s+)?ANTHROPIC_API_KEY\s*=\s*["\']?sk-ant', re.M)


def root(path):
    p = os.path.realpath(os.path.expanduser(path))
    for r in ALLOW:
        if p == r or p.startswith(r + os.sep):
            return r
    return None


def resolve(p, base):
    p = os.path.expanduser(p.strip('"\''))
    return p if os.path.isabs(p) else os.path.join(base, p)


QHEREDOC = re.compile(r"<<-?\s*(['\"])(\w+)\1[^\n]*\n.*?^\s*\2\s*$", re.S | re.M)


def check_bash(cmd, cwd):
    # 따옴표 친 heredoc 본문은 셸이 펼치지 않는 글자다(문서에 'secret put …'을 적다 막힌 오탐, 10/28)
    plain = QHEREDOC.sub('', cmd)
    # 키는 마지막 cd 뒤에서 쓰인다고 본다(앞의 cd 는 다른 일을 하러 간 것)
    # 상대 cd 는 바로 앞 cd 기준으로 푼다(cd area-insight && cd api 가 my-sns/api 로 잡혀 막힌 오탐, 10/28)
    dirs, cur = [], cwd
    for d in CD.findall(plain):
        cur = resolve(d, cur); dirs.append(cur)
    dirs = dirs or [cwd]
    r = root(dirs[-1])
    ok = ALLOW.get(r, set())
    used = {m[0] for m in EXPAND.findall(plain)} | {m[0] for m in ASSIGN.findall(plain)} | {m[0] for m in SECRET.findall(plain)}
    bad = sorted(n for n in used if n not in ok)
    if bad:
        return f'키 {", ".join(bad)} 를 이 위치({dirs[-1]})에서 쓰려 함'
    if 'api.anthropic.com' in cmd and not r:
        return 'api.anthropic.com 직접 호출'
    if KEY.search(cmd) and not r:
        return 'sk-ant- 키가 명령에 들어 있음'
    for f in SOURCE.findall(cmd):
        p = resolve(f, dirs[-1])
        try:
            txt = open(p, errors='ignore').read()
        except OSError:
            continue
        if BARE.search(txt) and not r and not re.search(r'(unset|env\s+-u)\s+ANTHROPIC_API_KEY', cmd):
            return f'{p} 를 불러오면 ANTHROPIC_API_KEY 가 넘어감'
    return None


def check_write(path, text):
    if root(path):
        return None
    if os.path.realpath(os.path.expanduser(path)) == os.path.realpath(os.path.expanduser('~/.claude/.env')):
        names = {m[0] for m in re.findall(r'^\s*(' + NAME + r')=', text, re.M)}
        allowed = set().union(*ALLOW.values()) - {'ANTHROPIC_API_KEY'}
        bad = sorted(names - allowed)
        return f'~/.claude/.env 에 허용 안 된 키 {", ".join(bad)}' if bad else None
    if KEY.search(text) or BARE.search(text):
        return f'{path} 에 Anthropic 키를 쓰려 함'
    return None


def main():
    if os.environ.get('ANTHROPIC_KEY_GUARD_OFF') == '1':
        return 0
    d = json.load(sys.stdin)
    t, i = d.get('tool_name', ''), d.get('tool_input') or {}
    cwd = d.get('cwd') or os.getcwd()
    if t == 'Bash':
        why = check_bash(i.get('command', ''), cwd)
    elif t in ('Edit', 'Write', 'MultiEdit'):
        text = i.get('content') or i.get('new_string') or ''.join(e.get('new_string', '') for e in i.get('edits') or [])
        why = check_write(i.get('file_path', ''), text)
    else:
        why = None
    if why:
        print(f'[anthropic-key-guard] 차단: {why}.\n'
              'Anthropic API 키는 썸판독기(money-web)·상권.kr(area-insight)=개인 키, ai-paper=회사 키만 쓴다(사용자 10/25).\n'
              '다른 곳은 claude -p(구독)·목업으로 한다. 키를 빼려면 unset ANTHROPIC_API_KEY / env -u ANTHROPIC_API_KEY.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
