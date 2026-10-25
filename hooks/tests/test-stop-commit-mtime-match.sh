#!/bin/bash
# 이 세션 편집 시각과 파일 수정 시각이 맞을 때만 이 세션 파일로 본다(2026-10-25: 10/23 남이 고친 파일을
# 이 세션 디버그 스크립트가 경로를 언급할 때마다 '커밋해라'가 10회 반복됨).
set -e
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
mkdir -p "$T/repo"; git -C "$T/repo" init -q
touch "$T/repo/other.tsx" "$T/repo/mine.tsx"
python3 - "$T" <<'PY'
import importlib.util, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
t = sys.argv[1]
other, mine = f'{t}/repo/other.tsx', f'{t}/repo/mine.tsx'
def use(ts, cmd):
    return json.dumps({'type': 'assistant', 'timestamp': ts,
                       'message': {'content': [{'type': 'tool_use', 'name': 'Bash', 'input': {'command': cmd}}]}})
lines = [use('2026-10-23T08:55:00Z', f"sed -i '' s/a/b/ {other}"),          # 실제 편집, 뒤에 남이 다시 고침
         use('2026-10-25T03:00:00Z', f"python3 - <<'PY'\np='{other}'\nopen('/tmp/x','w').write(p)\nPY"),  # 경로 언급만
         use('2026-10-25T03:00:00Z', f"sed -i '' s/a/b/ {mine}")]
open(f'{t}/tr.jsonl', 'w').write('\n'.join(lines) + '\n')
ep = lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()
os.utime(other, (ep('2026-10-23T12:48:59'),) * 2)
os.utime(mine, (ep('2026-10-25T03:00:05'),) * 2)
hooks = Path.home() / '.claude/hooks'
s = importlib.util.spec_from_file_location('sc', hooks / 'stop_commit.py'); sc = importlib.util.module_from_spec(s); s.loader.exec_module(sc)
pc = sc.policy()
files = [Path(f'{t}/tr.jsonl')]
got = sc.still_mine(pc, files, pc.mine(files, [other, mine]))
assert other not in got, f'FAIL: 남이 마지막으로 고친 파일을 경로 언급만으로 이 세션 것으로 봄 {got}'
assert mine in got, f'FAIL: 직접 고친 파일을 놓침 {got}'
print('PASS')
PY
