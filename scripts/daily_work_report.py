#!/usr/bin/env python3
"""daily_work_report.py — 새벽 5시~다음 날 새벽 5시에 한 작업을 레포(프로젝트)별로 모아 텔레그램으로 보낸다. LLM 없음.

  python3 daily_work_report.py build [YYYY-MM-DD]   # 그날 05:00 ~ 다음 날 05:00 커밋 → ~/.cache/daily-work/<날짜>.txt
  python3 daily_work_report.py send  [YYYY-MM-DD]   # 만든 파일을 텔레그램으로(없으면 먼저 build)
  python3 daily_work_report.py show  [YYYY-MM-DD]   # 출력만

- 날짜를 안 주면 '어제'(지금이 05시 전이면 그제) 구간.
- 대상: ~/programming 아래 git 레포(깊이 4) + ~/claude-library + ~/.claude. 모든 브랜치 커밋 제목(머지·워크로그 자동 커밋 제외).
- 텔레그램: ~/.claude/.env DAILY_TG_TOKEN(@today_work_finish_bot), 받는 곳 DAILY_TG_CHAT_ID(없으면 getUpdates에서 찾아 저장).
- launchd: com.ram.daily-work-build(05:10) · com.ram.daily-work-send(09:00).
"""
import datetime as dt
import json
import os
import shutil
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HOME = Path.home()
ENV = HOME / '.claude/.env'
OUT = HOME / '.cache/daily-work'
SKIP = re.compile(r'^(Merge |chore: ?(워크로그|worklog)|docs: ?(워크로그|worklog)|.*\(auto\)$)', re.I)


def env(name):
    for line in ENV.read_text().splitlines():
        if line.startswith(name + '='):
            return line.split('=', 1)[1].strip().strip('"')


def repos():
    found = set()
    for g in HOME.glob('programming/**/.git'):
        if len(g.relative_to(HOME / 'programming').parts) <= 5 and 'node_modules' not in g.parts:
            found.add(g.parent)
    for p in (HOME / 'claude-library', HOME / '.claude'):
        if (p / '.git').exists():
            found.add(p)
    return sorted(found)


def day_range(arg):
    if arg:
        d = dt.date.fromisoformat(arg)
    else:
        now = dt.datetime.now()
        d = (now - dt.timedelta(days=1 if now.hour >= 5 else 2)).date()
    start = dt.datetime.combine(d, dt.time(5))
    return d, start, start + dt.timedelta(days=1)


def name_of(repo):
    try:
        url = subprocess.run(['git', '-C', str(repo), 'remote', 'get-url', 'origin'], capture_output=True, text=True).stdout.strip()
        if url:
            return re.sub(r'\.git$', '', url.rstrip('/').split('/')[-1])
    except Exception:
        pass
    return repo.name


def build(arg):
    d, start, end = day_range(arg)
    groups = {}
    for r in repos():
        out = subprocess.run(['git', '-C', str(r), 'log', '--all', '--no-merges', f'--since={start:%Y-%m-%d %H:%M}', f'--until={end:%Y-%m-%d %H:%M}',
                              '--pretty=%ad\t%s', '--date=format:%H:%M'], capture_output=True, text=True).stdout
        subs = []
        for line in reversed(out.splitlines()):  # 오래된 것부터
            _, s = line.split('\t', 1)
            s = re.sub(r'\s*Claude-Session:.*$', '', s).strip()
            if SKIP.match(s) or s in subs:
                continue
            subs.append(s)
        if subs:
            groups.setdefault(name_of(r), []).extend(x for x in subs if x not in groups.get(name_of(r), []))
    head = f'📋 {d:%m/%d}({"월화수목금토일"[d.weekday()]}) 05시 ~ 다음 날 05시 작업'
    raw = []
    for name, subs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        raw.append(f'{name} ({len(subs)})')
        raw += [f'- {re.sub(r"^[a-z]+(\([^)]*\))?!?: ?", "", s)}' for s in subs]
        raw.append('')
    raw = '\n'.join(raw).strip()
    body = (summarize(raw) if raw else None) or raw or '커밋한 작업 없음'
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{d}.raw.txt').write_text(raw + '\n')
    f = OUT / f'{d}.txt'
    f.write_text(head + '\n\n' + body.strip() + '\n')
    return f


PROMPT = '''아래는 하루 동안 레포(프로젝트)별 git 커밋 제목이다. 사용자가 아침에 텔레그램으로 읽을 하루 작업 정리로 줄여라.
형식(이것만 출력, 머리말·맺음말·마크다운 굵게 금지):
프로젝트이름
- 한 일 한 줄
- 한 일 한 줄

규칙:
- 프로젝트마다 2~5줄. 비슷한 커밋(오타 정정·이력 추가·되돌림)은 합쳐 결과만 쓴다. 되돌린 건 안 한 것으로 본다.
- 한 줄은 30자 안팎, 쉬운 한국어, '~함/~추가' 같은 짧은 끝맺음. 커밋에 없는 내용은 지어내지 않는다.
- 많이 한 프로젝트부터. claude-library(지식·결정 기록)와 claude-config(도구 설정)는 맨 끝에 각각 1~2줄로만.
- 프로젝트 사이엔 빈 줄 하나.

커밋:
'''


def summarize(raw):
    """claude -p(구독 로그인, API 키 아님)로 축약. 실패하면 None → 커밋 목록 그대로 보낸다."""
    exe = shutil.which('claude') or str(HOME / '.local/bin/claude')
    env = {k: v for k, v in os.environ.items() if k not in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL')}
    env['CLAUDE_CONFIG_DIR'] = str(HOME / '.config/claude-accounts/personal')
    env['PATH'] = env.get('PATH', '') + ':/opt/homebrew/bin:/usr/local/bin:' + str(HOME / '.local/bin')
    try:
        r = subprocess.run([exe, '-p', PROMPT + raw, '--system-prompt', '너는 커밋 목록을 짧게 요약하는 도구다.', '--tools', '',
                            '--strict-mcp-config', '--setting-sources', '', '--no-session-persistence', '--model', 'sonnet'],
                           capture_output=True, text=True, timeout=600, env=env, cwd='/tmp')
        out = r.stdout.strip()
        return out if r.returncode == 0 and out.count('\n- ') >= 2 else None
    except Exception:
        return None


def chat_id(token):
    cid = env('DAILY_TG_CHAT_ID')
    if cid:
        return cid
    r = json.load(urllib.request.urlopen(f'https://api.telegram.org/bot{token}/getUpdates', timeout=20))
    ids = [(u.get('message') or {}).get('chat', {}).get('id') for u in r['result']]
    ids = [i for i in ids if i]
    if not ids:
        sys.exit('RESULT: BLOCKED 봇(@today_work_finish_bot)에 아무 메시지나 한 번 보내야 받는 곳을 알 수 있음')
    with ENV.open('a') as fp:
        fp.write(f'DAILY_TG_CHAT_ID={ids[-1]}\n')
    return str(ids[-1])


def send(arg):
    d, _, _ = day_range(arg)
    f = OUT / f'{d}.txt'
    if not f.exists():
        f = build(arg)
    token = env('DAILY_TG_TOKEN')
    cid = chat_id(token)
    text = f.read_text()
    chunks, cur = [], ''
    for para in text.split('\n\n'):  # 4096자 제한 → 프로젝트 단위로 나눈다
        if len(cur) + len(para) + 2 > 3900:
            chunks.append(cur)
            cur = ''
        cur += para + '\n\n'
    chunks.append(cur)
    for ch in chunks:
        if ch.strip():
            q = urllib.parse.urlencode({'chat_id': cid, 'text': ch[:4096]}).encode()
            urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage', q, timeout=20)
    print(f'RESULT: OK {d} {len(chunks)}개 메시지')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'show'
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    if cmd == 'build':
        print('RESULT: OK', build(arg))
    elif cmd == 'send':
        send(arg)
    else:
        print(build(arg).read_text())
