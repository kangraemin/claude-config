#!/usr/bin/env python3
"""프로젝트 세션 하나만 리모트로 연다. 다른 세션은 건드리지 않는다.

사용: open_session.py <프로젝트 키워드>      (예: "ai bouncer", mukmap, 공모전)
  - 명단(remotes.json)에 그 폴더 세션이 있으면 그 대화를 --resume으로 다시 붙인다(이어받기 프롬프트 없음).
  - 없으면 그 폴더에서 새 세션을 --remote-control로 띄우고 명단에 넣는다.
마지막 줄: RESULT OK <이름> <링크> | RESULT BLOCKED <이유>

2026-10-25 "ai bouncer 켜바"·"세션 연결좀해바"(=ai-bouncer 세션 하나)에 재부팅 재연결을 돌려
꺼진 세션 13개를 띄운 사고 뒤에 만들었다.
"""
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path.home() / '.codex/skills/claude-account-switch/scripts'))
import account  # noqa: E402
import remotes  # noqa: E402

BASE = Path.home() / 'programming/vibecoding'


def norm(s):
    return re.sub(r'[\s_\-]', '', unicodedata.normalize('NFC', s).lower())


def find_dir(key):
    k = norm(key)
    dirs = [d for d in BASE.iterdir() if d.is_dir()]
    exact = [d for d in dirs if norm(d.name) == k]
    if exact:
        return exact[0], []
    part = [d for d in dirs if k in norm(d.name)]
    return (part[0], []) if len(part) == 1 else (None, part)


def url_from_pane(name):
    m = re.search(r'https://claude\.ai/code/session_\w+', remotes.pane_text(name))
    return m.group(0) if m else None


def launch(cwd, name):
    if subprocess.run(['tmux', 'has-session', '-t', name], capture_output=True).returncode == 0:
        return None, f'tmux {name} 이미 있음 — 직접 확인 필요'
    args = ['tmux', 'new-session', '-d', '-s', name, '-x', '140', '-y', '45', '-c', str(cwd),
            'env', '-u', 'CLAUDE_CONFIG_DIR']
    if account.selected() == 'personal':
        args += ['CLAUDE_CONFIG_DIR=' + str(account.ROOT / 'personal')]
    args += [str(account.CLI), '--dangerously-skip-permissions', '--remote-control', name]
    subprocess.run(args, check=True)
    handled = set()
    for _ in range(60):
        url = url_from_pane(name)
        if url:
            remotes.discover()
            return url, None
        screen = remotes.pane_text(name)
        action = None
        if 'Settings Warning' in screen and '1. Continue' in screen:
            action = 'settings'
        elif 'Yes, I trust this folder' in screen and 'No, exit' in screen:
            action = 'trust'
        elif 'Enable Remote Control' in screen and 'Never mind' in screen:
            action = 'enable'
        if action and action not in handled:
            handled.add(action)
            remotes.key(name, *(['Down', 'Enter'] if action == 'trust' else ['Enter']))
        time.sleep(1)
    return None, f'시작 확인 안 됨 — tmux {name} 확인'


def main():
    if len(sys.argv) < 2:
        print('RESULT BLOCKED 프로젝트 키워드가 필요하다')
        return 2
    key = ' '.join(sys.argv[1:])
    cwd, many = find_dir(key)
    if not cwd:
        print('RESULT BLOCKED 폴더를 못 정함: ' + (', '.join(d.name for d in many) or '일치 없음'))
        return 2
    entries = [e for e in remotes.discover() if Path(e['cwd']).resolve() == cwd.resolve()]
    profile = account.selected()
    valid, auth = account.status(profile)
    if not valid:
        print('RESULT BLOCKED 선택된 계정이 로그인 안 됨')
        return 2
    if entries:
        # 같은 폴더 세션이 여럿이면 가장 최근 대화를 연다.
        entry = max(entries, key=lambda e: Path(e['transcript']).stat().st_mtime if Path(e['transcript']).exists() else 0)
        r = remotes.reconnect(entry, profile, auth['orgId'], resume=False)
        print(json.dumps(r, ensure_ascii=False))
        if r['status'] == 'connected':
            print(f"RESULT OK {r['name']} {r['url']}")
            return 0
        print(f"RESULT BLOCKED {r['name']} {r['status']} {r.get('reason', '')}")
        return 2
    url, err = launch(cwd, cwd.name)
    if url:
        print(f'RESULT OK {cwd.name} {url}')
        return 0
    print('RESULT BLOCKED ' + err)
    return 2


if __name__ == '__main__':
    sys.exit(main())
