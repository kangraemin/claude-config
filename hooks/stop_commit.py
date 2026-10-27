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
ACTIVE = 300  # 서브에이전트 transcript 가 이 시간(초) 안에 갱신됐으면 아직 작업 중으로 본다


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


def edit_times(pc, files, paths):
    # 파일마다 이 세션이 고친 시각들(epoch). transcript 줄의 timestamp 로 센다
    wanted = {p: pc.needles(Path(p)) for p in paths}
    times = {}
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
                            times.setdefault(p, []).append(ts)
        except OSError:
            continue
    return times


def still_mine(pc, files, paths):
    # 이 세션이 고친 뒤 다른 세션이 다시 바꾼 파일은 뺀다(2026-10-24: 하루 전 만든 블로그 파일을
    # 남의 세션이 고친 걸로 '커밋해라'가 6회 반복됨). 파일의 마지막 수정 시각이 이 세션 편집 시각 어느 것과도
    # 맞지 않으면 남의 것이다. 나중에 경로를 언급만 한 명령(디버그 스크립트·테스트 주석)으로는 다시 잡히지 않는다
    # (2026-10-25: 10/23 남이 고친 파일로 '커밋해라' 10회).
    times = edit_times(pc, files, paths)
    out = []
    for p in paths:
        try:
            mtime = os.path.getmtime(p)
        except OSError:
            continue
        if p in times and not any(ts - 5 <= mtime <= ts + SLACK for ts in times[p]):
            continue
        out.append(p)
    return out


def in_flight(pc, files, paths):
    # 백그라운드 서브에이전트가 아직 고치는 중인 파일은 뺀다(2026-10-28: 장별 검증 에이전트 11개가 책 파일을
    # 고치는 동안 에이전트 하나가 끝날 때마다 메인 턴이 끝나 '커밋해라'가 반복됨. 커밋하면 횟수가 0으로 돌아가
    # MAX_BLOCKS 도 안 걸렸다). 끝난 에이전트의 편집은 다음 Stop 에서 그대로 잡힌다.
    now = time.time()
    busy = [f for f in files if f.parent.name == 'subagents' and now - os.path.getmtime(f) < ACTIVE]
    return pc.mine(busy, paths) if busy else set()


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
    owned = pc.mine(files, dirty)
    mine = sorted(set(still_mine(pc, files, owned)) - in_flight(pc, files, owned))
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
