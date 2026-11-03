#!/usr/bin/python3
"""claude -p 호출 장부 + 상한. exit 75 = 막음, 그 외 = 통과. 가드 자체 오류는 통과(claude가 안 켜지는 사고 방지)."""
import fcntl, json, os, re, subprocess, sys, time
H = os.path.expanduser('~/.claude')
LEDGER, ALLOW, SENT = H + '/.headless-ledger.jsonl', H + '/.headless-allow.json', H + '/.headless-alerted.json'
# 상한: 시간·하루. Opus는 비싸서 따로. 넘으면 호출 전에 막는다.
LIM = dict(caller_hr=100, caller_day=400, all_hr=200, all_day=800, opus_hr=40, opus_day=150, live=8)

def ancestry():
    pid, out = os.getppid(), []
    for _ in range(12):
        r = subprocess.run(['ps', '-o', 'ppid=,command=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
        if not r: break
        ppid, _, cmd = r.partition(' ')
        out.append(cmd.strip())
        if ppid.strip() in ('0', '1'): break
        pid = int(ppid)
    return out

def caller():
    for c in ancestry():
        if 'account.py' in c or 'claude_shim' in c or 'claude-p.sh' in c: continue
        m = re.search(r'([^\s]+\.(?:py|sh|js|mjs))\b', c)
        if m: return os.path.basename(m.group(1))[:60] + ':' + os.path.basename(os.path.dirname(m.group(1)))[:30]
    a = ancestry()
    return (a[0].split()[0] if a else 'unknown')[:60]

def live():
    r = subprocess.run(['ps', '-axo', 'command='], capture_output=True, text=True).stdout
    return sum(1 for l in r.splitlines() if re.search(r'(/claude|/versions/[\d.]+)\s(.*\s)?(-p|--print)\s', l + ' ') and 'headless_guard' not in l and 'claude_shim' not in l)

def notify(key, text):
    try: seen = json.load(open(SENT))
    except Exception: seen = {}
    now = time.time()
    if now - seen.get(key, 0) < 3600: return
    seen[key] = now; json.dump(seen, open(SENT, 'w'))
    subprocess.Popen(['/usr/bin/python3', '-I', H + '/scripts/headless_watch.py', '--send', text],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

def main():
    a = sys.argv[1:]
    model = a[a.index('--model') + 1] if '--model' in a and a.index('--model') + 1 < len(a) else os.environ.get('ANTHROPIC_MODEL', 'default')
    me, now = caller(), time.time()
    try: allow = json.load(open(ALLOW))
    except Exception: allow = {}
    g = allow.get(me) or {}
    extra = g.get('max', 0) if g.get('until', 0) > now else 0   # 사용자가 headless-allow로 준 추가 호출 수(시간·하루 상한에 더함)
    lim = dict(LIM)
    t = os.environ.get('HEADLESS_TEST_MAX')  # 시험용: 상한을 낮추기만 한다
    if t and t.isdigit(): lim = {k: min(v, int(t)) for k, v in lim.items()}
    with open(LEDGER, 'a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        rows = []
        for l in f:
            try:
                r = json.loads(l)
                if now - r['t'] < 86400: rows.append(r)
            except Exception: pass
        hr = [r for r in rows if now - r['t'] < 3600]
        c = lambda rs, fn: sum(1 for r in rs if fn(r))
        mine, op = (lambda r: r['c'] == me), (lambda r: 'opus' in r['m'].lower())
        over = None
        if c(hr, mine) >= lim['caller_hr'] + extra: over = f"이 스크립트 시간당 {lim['caller_hr'] + extra}회"
        elif c(rows, mine) >= lim['caller_day'] + extra: over = f"이 스크립트 하루 {lim['caller_day'] + extra}회"
        elif 'opus' in model.lower() and c(hr, op) >= lim['opus_hr'] + extra: over = f"Opus 시간당 {lim['opus_hr'] + extra}회"
        elif 'opus' in model.lower() and c(rows, op) >= lim['opus_day'] + extra: over = f"Opus 하루 {lim['opus_day'] + extra}회"
        elif len(hr) >= lim['all_hr'] + extra: over = f"전체 시간당 {lim['all_hr'] + extra}회"
        elif len(rows) >= lim['all_day'] + extra: over = f"전체 하루 {lim['all_day'] + extra}회"
        elif live() > lim['live'] + extra: over = f"동시 {lim['live'] + extra}개"
        if over:
            print(f"[headless-guard] claude -p 막음: {me} ({over} 초과). 토큰을 쓰지 않았다. 재시도하지 말 것. 풀려면 사용자가 직접: ! ~/.claude/scripts/headless-allow '{me}' <추가호출수>", file=sys.stderr)
            if not t:
                notify('block:' + me, f"claude -p 막음\n- {me}\n- 초과: {over}\n- 모델: {model}\n- 풀기: ! ~/.claude/scripts/headless-allow '{me}' <추가호출수>")
            return 75
        f.seek(0, 2)
        f.write(json.dumps({'t': round(now), 'c': me, 'm': model}) + '\n')
        if os.fstat(f.fileno()).st_size > 2_000_000:  # 하루치만 남기고 줄인다
            f.seek(0); f.truncate()
            for r in rows: f.write(json.dumps(r) + '\n')
    return 0

try:
    sys.exit(main())
except SystemExit:
    raise
except Exception as e:
    print(f'[headless-guard] 오류, 통과: {e}', file=sys.stderr)
    sys.exit(0)
