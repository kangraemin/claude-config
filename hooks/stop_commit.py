#!/usr/bin/env python3
"""Stop hook: 이 세션이 고친 추적 파일이 커밋 안 된 채 끝나면 "커밋하고 푸시해줘"로 한 번 막는다.

2026-10-22 감사(02-global-hooks.md)에서 고친 것
  - 남의 세션 변경·자동 갱신 파일(.claude/ai-bouncer, .update-check)에 반응해 "커밋할 게 없다" 헛돌기 914회
    -> transcript 로 이 세션이 고친 파일만 본다(policy-changelog.py 의 소유 판정 재사용).
  - 377회까지 가던 연속 차단 -> 같은 세션 3회부터는 경고만.
  - .pending 마커 1.2만 개를 jq 로 도느라 28% 가 10초 시간초과 -> 워크로그 부분 삭제.
"""
import importlib.util
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
COUNTERS = HOOKS / '.counters'
SKIP = ('.worklogs/', '.claude/ai-bouncer/', '.ai-bouncer/', '.update-check')
MAX_BLOCKS = 3
SLACK = 120  # 편집 도구 기록과 실제 파일 저장 사이 차이(초)


def git(cwd, *args):
    try:
        return subprocess.run(['git', '-C', cwd, *args], capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return ''


def policy():
    spec = importlib.util.spec_from_file_location('policy_changelog', HOOKS / 'policy-changelog.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def last_edits(pc, files, paths):
    # 파일마다 이 세션이 마지막으로 고친 시각(epoch). transcript 줄의 timestamp 로 센다
    wanted = {p: pc.needles(Path(p)) for p in paths}
    last = {}
    for file in files:
        try:
            with open(file, 'rb') as stream:
                for line in stream:
                    if b'"tool_use"' not in line:
                        continue
                    hits = [p for p, forms in wanted.items() if any(f in line for f in forms)]
                    if not hits:
                        continue
                    texts = [t.encode() for t in pc.edited(line)]
                    try:
                        ts = datetime.fromisoformat(json.loads(line)['timestamp'].replace('Z', '+00:00')).timestamp()
                    except (ValueError, KeyError, TypeError, AttributeError):
                        continue
                    for p in hits:
                        if any(f in t for t in texts for f in wanted[p]):
                            last[p] = max(last.get(p, 0), ts)
        except OSError:
            continue
    return last


def still_mine(pc, files, paths):
    # 이 세션이 고친 뒤 다른 세션이 다시 바꾼 파일은 뺀다(2026-10-24: 하루 전 만든 블로그 파일을
    # 남의 세션이 고친 걸로 '커밋해라'가 6회 반복됨). 마지막 수정 시각이 이 세션의 마지막 편집보다 SLACK 넘게 늦으면 남의 것이다
    last = last_edits(pc, files, paths)
    out = []
    for p in paths:
        try:
            mtime = os.path.getmtime(p)
        except OSError:
            continue
        if p in last and mtime > last[p] + SLACK:
            continue
        out.append(p)
    return out


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    if data.get('stop_hook_active') or os.environ.get('WORKLOG_TIMING') == 'manual':
        return
    cwd = data.get('cwd') or ''
    top = git(cwd, 'rev-parse', '--show-toplevel').strip()
    if not top:
        return
    # ai-bouncer 작업 중이면 커밋 시점은 bouncer finalize 가 정한다.
    if any((Path(top) / '.ai-bouncer/tasks').glob('*/.active')):
        return
    interval = os.environ.get('STOP_COMMIT_INTERVAL_MIN')
    if interval and interval.isdigit():
        last = git(top, 'log', '-1', '--format=%ct').strip()
        if last.isdigit() and time.time() - int(last) < int(interval) * 60:
            return
    dirty = []
    for line in git(top, 'status', '--porcelain').splitlines():
        if line.startswith('??') or len(line) < 4:
            continue
        rel = line[3:].split(' -> ')[-1].strip('"')
        if not any(s in rel for s in SKIP):
            dirty.append(str(Path(top) / rel))
    if not dirty:
        (COUNTERS / f".stop-commit-{data.get('session_id', 'unknown')}").unlink(missing_ok=True)
        return
    pc = policy()
    files = pc.transcripts(data)
    if files is None:
        return
    mine = sorted(still_mine(pc, files, pc.mine(files, dirty)))
    sid = str(data.get('session_id', 'unknown'))
    counter = COUNTERS / f'.stop-commit-{sid}'
    if not mine:
        counter.unlink(missing_ok=True)  # 커밋했으면 연속 차단 횟수를 되돌린다
        return
    COUNTERS.mkdir(exist_ok=True)
    try:
        blocks = int(counter.read_text())
    except (OSError, ValueError):
        blocks = 0
    blocks += 1
    counter.write_text(str(blocks))
    names = '\n'.join('- ' + os.path.relpath(p, top) for p in mine[:15])
    reason = f'이 세션이 고친 파일이 커밋 안 됐다. 이 파일만 개별 git add 해서 커밋하고 푸시해줘:\n{names}'
    if blocks <= MAX_BLOCKS:
        print(json.dumps({'decision': 'block', 'reason': reason}, ensure_ascii=False))
    else:
        print(json.dumps({'systemMessage': f'경고 (커밋 요청 {blocks}회째): ' + reason}, ensure_ascii=False))


if __name__ == '__main__':
    main()
