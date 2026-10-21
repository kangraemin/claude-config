#!/usr/bin/env python3
"""decision-inject 본체: 현재 레포 + _global 의 확정 결정사항을 SessionStart 컨텍스트에 주입한다.

정책은 pull(검색)이 아니라 push(자동 주입)여야 지켜진다.
2026-10-22 감사: 7% 가 하니스 10KB 한도를 넘어 프리뷰만 들어갔고, 파일마다 도는 셸 루프로 2.5~3.7초 걸렸다.
  -> 한 번의 파이썬으로 읽고, 총 8KB 상한(넘치면 요약 -> 제목 순으로 줄임), compact 때는 제목만.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

LIB = Path(os.environ.get('LIBRARY_ROOT', Path.home() / 'claude-library'))
CLAUDE_MD = Path.home() / '.claude/CLAUDE.md'
LIMIT = int(os.environ.get('DECISION_INJECT_BYTES', 8000))
CATS = ('architecture', 'stack', 'convention', 'process', 'scope')
HEADER = ('아래는 **이미 결정된 사항**이다. 지식이 아니라 결정이다.\n'
          '새 제안을 하기 전에 여기서 이미 정해졌는지 확인하고, 뒤집으려면 이유를 먼저 밝혀라.\n'
          '전문은 decision_read("<경로>") 로 읽는다. 세션 중 추가된 결정은 decision_search 로 찾는다.')


def repo_name(cwd):
    def git(*a):
        try:
            return subprocess.run(['git', '-C', cwd, *a], capture_output=True, text=True, timeout=3).stdout.strip()
        except Exception:
            return ''
    url = git('remote', 'get-url', 'origin')
    if url:
        return re.sub(r'\.git$', '', url.rstrip('/').rsplit('/', 1)[-1].rsplit(':', 1)[-1])
    root = git('rev-parse', '--show-toplevel')
    return os.path.basename(root) if root else ''


def entries(folder, loaded):
    out = []
    for cat in CATS:
        for f in sorted((folder / cat).glob('*.md')):
            try:
                text = f.read_text(errors='ignore')
            except OSError:
                continue
            if not re.search(r'^status: *(stable|draft)', text, re.M):
                continue
            rel = 'decisions/' + str(f.relative_to(LIB / 'decisions'))
            if rel in loaded:  # CLAUDE.md 에 why 마커로 이미 실린 규칙
                continue
            title = next((l[2:].strip() for l in text.splitlines() if l.startswith('# ')), f.stem)
            m = re.search(r'^## Decision Outcome\s*\n+(.+)', text, re.M)
            if m:
                summary = m.group(1).strip()
            else:
                body = text.split('\n# ', 1)[-1].splitlines()[1:]
                summary = next((l.strip() for l in body if l.strip() and not l.startswith('#')), '')[:400]
            out.append((cat, title, rel, summary))
    return out


def render(items, with_summary):
    lines, last = [], None
    for cat, title, rel, summary in items:
        if cat != last:
            lines.append(f'\n## {cat}')
            last = cat
        lines.append(f'- **{title}** ({rel})')
        if with_summary and summary:
            lines.append('  ' + (summary if with_summary is True or len(summary) <= with_summary else summary[:with_summary] + '…'))
    return '\n'.join(lines)


def build(repo, local, glob, local_sum, glob_sum, cut=None):
    parts = [HEADER]
    if local:
        shown = local if cut is None else local[:cut]
        note = f' (전체 {len(local)}건 중 {len(shown)}건만 주입 — 나머지는 decision_list("{repo}") 로 확인하라)' if len(shown) < len(local) else ''
        parts.append(f'# 이 레포({repo})의 확정된 결정사항 {len(shown)}건{note}\n' + render(shown, local_sum))
    if glob:
        parts.append('# 모든 프로젝트 공통 결정사항 (CLAUDE.md 에 없는 것)\n' + render(glob, glob_sum))
    return '\n\n'.join(parts)


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    cwd = data.get('cwd') or os.getcwd()
    repo = repo_name(cwd)
    loaded = CLAUDE_MD.read_text(errors='ignore') if CLAUDE_MD.is_file() else ''
    local = entries(LIB / 'decisions' / repo, '') if repo and repo != '_global' else []
    glob = [e for e in entries(LIB / 'decisions/_global', '') if e[2] not in loaded]
    if not local and not glob:
        return
    compact = data.get('source') == 'compact'
    # 줄이는 순서: 공통 요약 80자 -> 레포 요약 80자 -> 공통 요약 빼기 -> 레포 요약 빼기 -> 레포 목록 자르기
    plans = [(True, True), (True, 80), (80, 80), (80, False), (False, False)]
    if compact:
        plans = [(False, False)]
    text = None
    for local_sum, glob_sum in plans:
        text = build(repo, local, glob, local_sum, glob_sum)
        if len(text.encode()) <= LIMIT:
            break
    cut = len(local)
    while len(text.encode()) > LIMIT and cut > 0:
        cut -= 1
        text = build(repo, local, glob, False, False, cut)
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': text}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
