#!/usr/bin/python3
"""PreToolUse(Bash|Write|Edit): ① 상한 없는 claude -p 스크립트 작성을 막는다 ② 에이전트가 가드를 끄거나 스스로 상한을 푸는 걸 막는다."""
import json, os, re, sys
try: d = json.load(sys.stdin)
except Exception: sys.exit(0)
t, i = d.get('tool_name'), d.get('tool_input') or {}
CALL = re.compile(r"""claude(-account|-p\.sh)?\b[^\n]{0,80}?(?:\s|['"],\s*['"])(?:-p|--print)\b|['"]claude(-account)?['"][^\n]{0,60}['"](?:-p|--print)['"]""")
GUARD = re.compile(r'headless-allow|\.headless-|headless_guard|headless_watch|claude_shim|headless-guard')
def block(m):
    print(m, file=sys.stderr); sys.exit(2)
def need_cap(text, path):
    if not CALL.search(text): return
    m = re.search(r'CLAUDE_P_MAX\s*=\s*(\d+)', text)
    if not m and path and os.path.exists(path):
        try: m = re.search(r'CLAUDE_P_MAX\s*=\s*(\d+)', open(path, errors='ignore').read())
        except Exception: pass
    if not m:
        block('[headless-guard] claude -p를 부르는 스크립트에 전체 호출 수 상한이 없다. 건수×반복×모델로 총 호출 수를 계산해 파일에 `CLAUDE_P_MAX=<수>` 주석을 넣고, 코드에서 그 수를 넘으면 멈추게 한 뒤 다시 써라. 11/4 젠더 측정이 상한 없이 약 2만 회를 불러 주간 한도 40%를 썼다.')
    if int(m.group(1)) > 100:
        block(f'[headless-guard] CLAUDE_P_MAX={m.group(1)}: 100회 초과. 서브에이전트나 모델 없는 방식으로 줄여라. 꼭 필요하면 호출 수·모델·예상 주간 한도 %를 사용자에게 보고하고, 사용자가 headless-allow를 직접 실행한 뒤 진행한다.')
if t in ('Write', 'Edit'):
    p = i.get('file_path', '')
    if GUARD.search(os.path.basename(p)) or p.endswith('/.local/bin/claude'):
        block('[headless-guard] 가드 파일은 에이전트가 고치지 않는다. 고칠 일이면 사용자에게 알린다.')
    if p.endswith(('.py', '.sh', '.js', '.mjs', '.ts', '.zsh', '.bash')) or '.' not in os.path.basename(p):
        txt = i.get('content') or i.get('new_string') or ''
        if '.local/share/claude/versions' in txt: block('[headless-guard] 스크립트에 실제 실행 파일 경로를 적지 않는다. `claude`로 부른다.')
        if GUARD.search(txt): block('[headless-guard] 가드 파일을 건드리는 스크립트는 에이전트가 쓰지 않는다.')
        need_cap(txt, p)
elif t == 'Bash':
    c = i.get('command', '')
    if GUARD.search(c) and not re.search(r'headless_watch\.py\s+--report', c) and re.search(r'headless-allow|launchctl\s+(unload|bootout|remove|disable)|\brm\b|\bmv\b|\bcp\b|sed\s+-i|>\s*\S*(headless|claude_shim)|\bchmod\b|\bunlink\b', c):
        block('[headless-guard] 가드를 끄거나 상한을 푸는 명령은 에이전트가 실행하지 않는다. 사용자가 터미널에서 직접 `! ...`로 실행한다.')
    if re.search(r'/\.local/share/claude/versions/\S+[^\n]*\s(-p|--print)\b', c):
        block('[headless-guard] 실제 실행 파일을 직접 불러 장부를 건너뛰지 않는다.')
    if re.search(r'(>|\btee\s+)\s*\S+\.(py|sh|js|mjs|ts|zsh|bash)\b', c): need_cap(c, None)
sys.exit(0)
