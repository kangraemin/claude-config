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
    for name, asks in sessions(start, end).items():
        if name in groups:
            continue  # 커밋이 있으면 커밋으로 충분
        raw.append(f'{name} (커밋 없음 — 사용자 요청 기준)')
        raw += [f'- 요청: {a}' for a in asks[:25]]
        raw.append('')
    raw = '\n'.join(raw).strip()
    body = (summarize(raw) if raw else None) or (short(groups) if groups else raw) or '커밋한 작업 없음'
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{d}.raw.txt').write_text(raw + '\n')
    f = OUT / f'{d}.txt'
    f.write_text(head + '\n\n' + body.strip() + '\n')
    return f


NOISE = re.compile(r'^(<|\[SYSTEM|\[Request interrupted|Stop hook|Caveat:|This session is being continued)')


def project_of(cwd):
    p = Path(cwd)
    for q in [p, *p.parents]:
        if (q / '.git').exists():
            return name_of(q)
    # git 없는 폴더: ~/programming/(vibecoding/)<프로젝트>/… 의 <프로젝트>로 묶는다. 그 밖(/tmp 등)은 뺀다.
    for base in (HOME / 'programming/vibecoding', HOME / 'programming'):
        try:
            return p.relative_to(base).parts[0]
        except (ValueError, IndexError):
            pass
    return None


def sessions(start, end):
    """커밋 안 하는 작업(이모티콘 그리기 등)도 잡으려고 Claude 세션 기록의 사용자 요청을 프로젝트별로 모은다."""
    t0, t1 = start.astimezone(dt.timezone.utc), end.astimezone(dt.timezone.utc)
    out = {}
    roots = [HOME / '.claude/projects', *HOME.glob('.config/claude-accounts/*/projects')]
    for root in roots:
        for f in root.glob('*/*.jsonl'):
            if dt.datetime.fromtimestamp(f.stat().st_mtime, dt.timezone.utc) < t0:
                continue
            try:
                for line in f.open(encoding='utf-8', errors='replace'):
                    if '"type":"user"' not in line:
                        continue
                    d = json.loads(line)
                    if d.get('isMeta') or not d.get('cwd'):
                        continue
                    ts = dt.datetime.fromisoformat(d.get('timestamp', '').replace('Z', '+00:00'))
                    c = d.get('message', {}).get('content')
                    if not (t0 <= ts < t1) or not isinstance(c, str):
                        continue
                    c = ' '.join(c.split())
                    if len(c) < 6 or NOISE.match(c):
                        continue
                    name = project_of(d['cwd'])
                    if not name or name == 'vibecoding':
                        continue
                    asks = out.setdefault(name, [])
                    if c[:100] not in asks:
                        asks.append(c[:100])
            except Exception:
                continue
    return out


PROMPT = '''아래는 하루 동안 레포(프로젝트)별 git 커밋 제목이다. 사용자가 아침에 텔레그램으로 읽을 하루 작업 정리로 줄여라.
형식(이것만 출력, 머리말·맺음말·마크다운 굵게 금지):
프로젝트이름
- 한 일 한 줄
- 한 일 한 줄

규칙:
- 프로젝트마다 2~5줄. 비슷한 커밋(오타 정정·이력 추가·되돌림)은 합쳐 결과만 쓴다. 되돌린 건 안 한 것으로 본다.
- 한 줄은 30자 안팎, 쉬운 한국어, '~함/~추가' 같은 짧은 끝맺음. 커밋에 없는 내용은 지어내지 않는다.
- 많이 한 프로젝트부터. claude-library(지식·결정 기록)와 claude-config(도구 설정)는 맨 끝에 각각 1~2줄로만.
- '커밋 없음 — 사용자 요청 기준' 프로젝트는 요청들을 보고 실제로 한 작업을 짐작해 1~3줄로 쓴다(질문·잡담만 있으면 그 프로젝트는 뺀다).\n- 프로젝트 사이엔 빈 줄 하나.

커밋:
'''


def summarize(raw):
    """claude -p(구독 로그인, API 키 아님)로 축약. claude-p.sh가 한도 걸린 계정은 건너뛴다. 실패하면 None → short()."""
    env = {k: v for k, v in os.environ.items() if k not in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL')}
    env['PATH'] = env.get('PATH', '') + ':/opt/homebrew/bin:/usr/local/bin:' + str(HOME / '.local/bin')
    try:
        r = subprocess.run([str(HOME / '.claude/scripts/claude-p.sh'), '-p', PROMPT + raw, '--system-prompt', '너는 커밋 목록을 짧게 요약하는 도구다.', '--tools', '',
                            '--strict-mcp-config', '--setting-sources', '', '--no-session-persistence', '--model', 'sonnet'],
                           capture_output=True, text=True, timeout=1200, env=env, cwd='/tmp')
        out = r.stdout.strip()
        return out if r.returncode == 0 and out.count('\n- ') >= 2 else None
    except Exception:
        return None


TOOLS = {'claude-library', 'claude-config', '.claude'}


def short(groups):
    """요약 실패 때: 커밋 제목을 다 보내면 수백 줄이 된다(10/20 663줄) → 프로젝트마다 개수 + 최근 3줄, 도구 레포는 개수만."""
    out, tools = [], []
    for name, subs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if name in TOOLS:
            tools.append(f'{name} {len(subs)}건')
            continue
        out.append(f'{name} ({len(subs)}건)')
        out += [f'- {re.sub(r"^[a-z]+(\([^)]*\))?!?: ?", "", x)[:40]}' for x in subs[-3:]]
        out.append('')
    if tools:
        out.append('기록·설정: ' + ', '.join(tools))
    return '(자동 요약 실패 — 최근 커밋 3개씩)\n\n' + '\n'.join(out).strip()


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
