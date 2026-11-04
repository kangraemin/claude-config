#!/usr/bin/python3
"""launchd 5분마다: ① claude 업데이트로 앞단이 덮이면 다시 설치 ② 7일 사용량이 빨리 오르면 범인 목록과 함께 알림
③ 장부에 안 잡히는 -p 프로세스(우회) 알림. --report: 호출 집계 출력. --send: 텔레그램 전송."""
import collections, json, os, re, shutil, subprocess, sys, time, urllib.parse, urllib.request
H = os.path.expanduser('~/.claude')
BIN = os.path.expanduser('~/.local/bin/claude')
SHIM, REAL = H + '/scripts/claude_shim.sh', H + '/.headless-real'
LEDGER, HIST, STATE = H + '/.headless-ledger.jsonl', H + '/.headless-usage-hist', H + '/.headless-watch.json'
PIDS, VERS = H + '/.headless-pids', os.path.expanduser('~/.local/share/claude/versions/')
HEAD = re.compile(r'^\s*(\S*(?:/claude|/versions/[\d.]+))\s(?:.*\s)?(?:-[A-Za-z]*p[A-Za-z]*|--print)\s')
ALERTED = {}
RISE, WINDOW, COOLDOWN = 3.0, 3600, 3 * 3600  # 1시간에 3%p 이상이면 알림(11/4 사고 때 시간당 약 3%p)

def send(text):
    env = {}
    for l in open(H + '/.env'):
        m = re.match(r'(?:export\s+)?(RAM_NOTI_TG_\w+)=(.*)', l.strip())
        if m: env[m.group(1)] = m.group(2).strip('"\'')
    tok, chat = env.get('RAM_NOTI_TG_TOKEN'), env.get('RAM_NOTI_TG_CHAT_ID')
    if not tok or not chat: return
    urllib.request.urlopen(f'https://api.telegram.org/bot{tok}/sendMessage',
        urllib.parse.urlencode({'chat_id': chat, 'text': text}).encode(), timeout=20).read()

def rows(sec=86400):
    now, out = time.time(), []
    try:
        for l in open(LEDGER):
            try:
                r = json.loads(l)
                if now - r['t'] < sec: out.append(r)
            except Exception: pass
    except FileNotFoundError: pass
    return out

def live():
    r = subprocess.run(['ps', '-axo', 'pid=,etime=,command='], capture_output=True, text=True).stdout
    return [l.strip()[:90] for l in r.splitlines() if re.search(r'^\s*\d+\s+\S+\s+\S*(?:/claude|/versions/[\d.]+)\s(?:.*\s)?(?:-[A-Za-z]*p[A-Za-z]*|--print)\s', l + ' ')]

def report():
    out = ['claude -p 호출 집계']
    for name, sec in (('1시간', 3600), ('24시간', 86400)):
        rs = rows(sec)
        out.append(f'- {name} {len(rs)}회')
        for (c, m), n in collections.Counter((r['c'], r['m']) for r in rs).most_common(6):
            out.append(f'- {n}회 {c} {m}')
    out.append(f'- 지금 도는 -p {len(live())}개')
    return '\n'.join(out)

def ensure_shim():
    if os.path.islink(BIN):
        t = os.path.realpath(BIN)
        if 'versions' in t:
            open(REAL, 'w').write(t)
            os.unlink(BIN); shutil.copy2(SHIM, BIN); os.chmod(BIN, 0o755)
    elif open(BIN, 'rb').read() != open(SHIM, 'rb').read():
        os.unlink(BIN); shutil.copy2(SHIM, BIN); os.chmod(BIN, 0o755)

def once(key, text, sec=3600):
    now = time.time()
    if now - ALERTED.get(key, 0) < sec: return
    ALERTED[key] = now
    try: send(text)
    except Exception as e: print('send', e, file=sys.stderr)

def enforce():
    ps = subprocess.run(['ps', '-axo', 'pid=,ppid=,command='], capture_output=True, text=True).stdout
    procs = {}
    for l in ps.splitlines():
        p = l.split(None, 2)
        if len(p) == 3: procs[p[0]] = (p[1], p[2])
    sus = [(pid, v) for pid, v in procs.items() if HEAD.search(v[1] + ' ')]
    if not sus: return
    try: known = set(open(PIDS).read().split())
    except FileNotFoundError: known = set()
    for pid, (ppid, cmd) in sus:
        if pid in known: continue
        exe = cmd.split()[0]
        pexe = procs.get(ppid, ('', 'x'))[1].split()[0]
        if os.path.basename(pexe) == 'claude' or '/versions/' in pexe: continue  # Claude Code 내부 호출
        parent = procs.get(ppid, ('', '?'))[1][:80]
        if exe.startswith(VERS):
            os.kill(int(pid), 15)
            once('kill:' + parent, f'앞단 안 거친 claude -p 종료\n- PID {pid}\n- 부모: {parent}')
        else:
            once('other:' + exe, f'다른 경로의 claude -p 발견\n- {exe[:80]}\n- 부모: {parent}')

def tamper():
    import hashlib
    names = ['scripts/headless_guard.py', 'scripts/headless_watch.py', 'scripts/claude_shim.sh', 'scripts/headless-allow', 'hooks/headless-guard-hook.py']
    h = hashlib.sha256()
    for n in names: h.update(open(H + '/' + n, 'rb').read())
    try: st = json.load(open(STATE))
    except Exception: st = {}
    d = h.hexdigest()
    if st.get('hash') and st['hash'] != d: once('tamper', '가드 파일이 바뀜\n- 사용자 지시가 없었다면 확인 필요', 60)
    st['hash'] = d; json.dump(st, open(STATE, 'w'))
    if 'headless-guard-hook' not in open(H + '/settings.json').read(): once('nohook', '가드 훅이 설정에서 빠짐\n- 작성 검사가 꺼진 상태')

def daemon():
    n = 0
    while True:
        try:
            ensure_shim(); enforce()
            if n % 60 == 0: usage(); tamper()
            if n % 720 == 0 and os.path.exists(PIDS):
                keep = open(PIDS).read().split()[-3000:]
                open(PIDS, 'w').write('\n'.join(keep) + '\n')
        except Exception as e:
            print('watch', e, file=sys.stderr, flush=True)
        n += 1; time.sleep(5)

def usage():
    try: st = json.load(open(STATE))
    except Exception: st = {}
    now = time.time()
    try:
        ts, pct = open(H + '/.usage-rl').read().split()[:2]
        ts, pct = float(ts), float(pct)
    except Exception: return
    with open(HIST, 'a') as f: f.write(f'{round(now)} {round(ts)} {pct}\n')
    h = []
    for l in open(HIST):
        try:
            a, b, p = l.split(); h.append((float(b), float(p)))
        except Exception: pass
    h = [x for x in h if now - x[0] < 2 * WINDOW]
    with open(HIST, 'w') as f:
        for b, p in h: f.write(f'{round(now)} {round(b)} {p}\n')
    old = [p for b, p in h if ts - b >= WINDOW * 0.8]
    if old and pct - old[-1] >= RISE and now - st.get('rise', 0) > COOLDOWN:
        st['rise'] = now
        send(f'7일 사용량 빠르게 오름\n- 1시간 +{pct - old[-1]:.0f}%p, 지금 {pct:.0f}%\n' + report())
    # 우회: 장부에 30분간 기록이 없는데 -p가 돌고 있음
    lv = live()
    if lv and not rows(1800) and now - st.get('bypass', 0) > COOLDOWN:
        st['bypass'] = now
        send('장부에 안 잡히는 claude -p\n' + '\n'.join('- ' + x for x in lv[:5]))
    json.dump(st, open(STATE, 'w'))

if __name__ == '__main__':
    if '--send' in sys.argv: send(sys.argv[sys.argv.index('--send') + 1])
    elif '--report' in sys.argv: print(report())
    elif '--daemon' in sys.argv: daemon()
    else:
        ensure_shim(); enforce(); usage(); tamper()
