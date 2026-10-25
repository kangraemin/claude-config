#!/bin/bash
# 다른 폴더의 같은 이름 파일(page.tsx)을 고친 기록으로 남의 파일을 '이 세션이 고친 것'으로 잡지 않는지 본다(2026-10-25:
# mukmap app/blog/page.tsx 를 남이 고쳤는데 이 세션이 app/[lang]/page.tsx 를 고쳐서 '커밋해라'가 5회 반복됨).
set -e
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
mkdir -p "$T/repo/app/blog" "$T/repo/app/lang"
touch "$T/repo/app/blog/page.tsx" "$T/repo/app/lang/page.tsx" "$T/repo/hooks_x.py"
git -C "$T/repo" init -q
python3 - "$T" <<'PY'
import json, sys
t = sys.argv[1]
def use(name, inp):
    return json.dumps({'type': 'assistant', 'timestamp': '2026-10-25T01:00:00Z',
                       'message': {'content': [{'type': 'tool_use', 'name': name, 'input': inp}]}})
lines = [use('Edit', {'file_path': f'{t}/repo/app/lang/page.tsx', 'old_string': 'a', 'new_string': 'b'}),
         use('Bash', {'command': 'sed -i "" s/a/b/ hooks_x.py'})]
open(f'{t}/tr.jsonl', 'w').write('\n'.join(lines) + '\n')
PY
python3 - "$T" <<'PY'
import importlib.util, sys
from pathlib import Path
t = sys.argv[1]
s = importlib.util.spec_from_file_location('pc', Path.home() / '.claude/hooks/policy-changelog.py')
pc = importlib.util.module_from_spec(s); s.loader.exec_module(pc)
blog, lang, uniq = f'{t}/repo/app/blog/page.tsx', f'{t}/repo/app/lang/page.tsx', f'{t}/repo/hooks_x.py'
got = pc.mine([Path(f'{t}/tr.jsonl')], [blog, lang, uniq])
assert blog not in got, f'FAIL: 다른 폴더 page.tsx 편집으로 blog/page.tsx 가 잡힘 {got}'
assert lang in got, f'FAIL: 직접 고친 파일을 못 잡음 {got}'
assert uniq in got, f'FAIL: 고유한 파일명(cd 후 이름만)으로 고친 걸 못 잡음 {got}'
print('PASS')
PY
