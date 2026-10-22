#!/usr/bin/env python3
"""update.sh의 append-only 정책 이력 기록과, 이 세션이 고친 파일 판정(stop_commit.py가 쓴다).

2026-10-22: 정책 파일을 고치면 이력 줄을 쓸 때까지 막던 Stop/SessionStart 검사는 뺐다.
누가·왜 바꿨는지는 git 커밋(세션 링크·메시지)에 남고, 이 검사가 만든 이력 정리 커밋이 라이브러리 커밋의 14%였다.
"""
import datetime
import json
import os
from pathlib import Path
import re
import sys

HOME = Path.home()
LIB = HOME / 'claude-library'
CLAUDE = HOME / '.claude'
SIDECARS = LIB / 'decisions/_global/changelog'


def read(path):
    return path.read_text() if path.is_file() else ''


def markdown_lines(text):
    # GUIDE의 코드 예시에 들어 있는 제목·항목은 실제 이력이 아니다.
    fence = None
    for i, line in enumerate(text.splitlines(keepends=True)):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None:
            yield i, line


def history(text):
    lines = text.splitlines(keepends=True)
    for i, line in markdown_lines(text):
        if line.rstrip() == '## 변경 이력':
            return ''.join(lines[:i]), ''.join(lines[i:])
    return text, ''


def location(path):
    if path == CLAUDE / 'CLAUDE.md':
        return SIDECARS / 'claude-md.md'
    if path.parent == CLAUDE / 'rules':
        return SIDECARS / ('rules-' + path.name)
    return path


def append(path, version, what):
    # 변경 이력은 메인테이너 전용이다. 일반 사용자 라이브러리에 _global/changelog 를 만들지 않는다.
    if os.environ.get('LEARNINGS_PROFILE', 'user') != 'maintainer':
        return
    dest = location(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = read(dest)
    if not text and dest != path:
        text = '---\ntype: Changelog\n---\n\n# 정책 변경 이력\n'
    if not history(text)[1]:
        text = text.rstrip() + '\n\n## 변경 이력\n'
    if not text.endswith('\n'):
        text += '\n'
    day = datetime.date.today().isoformat()
    sha = version.split('@', 1)[-1]
    evidence = f'commit:{sha}' if re.fullmatch(r'[0-9a-f]{7,40}', sha) else f'session:{day}/update.sh'
    text += f'- {day} · process:update.sh · {what} · 이유: learnings-for-claude {version} 템플릿 갱신 · 근거: {evidence}\n'
    dest.write_text(text)


def update_doc(src, dst, version):
    if not src.is_file():
        return
    before, template = read(dst), read(src)
    body, log = history(before)
    incoming, _ = history(template)
    if dst.is_file() and body.rstrip() == incoming.rstrip():
        return
    orig = Path(str(dst) + '.orig')
    if dst.is_file() and (not orig.is_file() or history(read(orig))[0].rstrip() != body.rstrip()):
        Path(str(dst) + '.new').write_text(template)
        print(f'  {dst.name} 수정본 유지 — .new 저장')
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_file():
        Path(str(dst) + '.bak').write_text(before)
    dst.write_text(incoming.rstrip() + '\n\n' + (log or history(template)[1]))
    append(dst, version, f'{dst.name} 템플릿 갱신')
    orig.write_text(read(dst))
    print(f'  {dst.name} 갱신 및 변경 이력 추가')


GENERIC = {'CLAUDE.md', 'GUIDE.md', 'TAXONOMY.md', 'README.md', 'index.md'}


def needles(path):
    # 이 세션의 도구 호출에 이 파일이 등장했는지 볼 이름들. 절대·~·라이브러리 기준 상대 경로, 고유한 파일명.
    forms = {str(path)}
    for base, prefix in ((HOME, '~/'), (LIB, ''), (CLAUDE, '.claude/')):
        try:
            forms.add(prefix + str(path.relative_to(base)))
        except ValueError:
            pass
    forms.add(path.name)
    return [f.encode() for f in forms if f and f not in GENERIC]


def transcripts(data):
    main = data.get('transcript_path')
    if not isinstance(main, str) or not os.path.isfile(main):
        return None
    files = [Path(main)]
    files += sorted((Path(main).with_suffix('') / 'subagents').glob('*.jsonl'))
    return files


EDITORS = {'Write', 'Edit', 'MultiEdit', 'NotebookEdit'}
# 셸에서 파일을 바꾸는 흔적. 2>&1 같은 리다이렉트는 쓰기가 아니다.
WRITES = re.compile(r'(?<![0-9&])>|sed -i|perl -i|\btee\b|\bmv\b|\bcp\b|\brm\b|write|git (?:checkout|restore|apply)|\bpatch\b|truncate')


def edited(line):
    # 도구 호출 입력 중 파일을 바꾸는 것만 돌려준다. 읽기나 차단 메시지에 경로가 나온 것으로는 이 세션 것으로 보지 않는다
    # (차단 사유에 남의 파일 경로가 적혀 transcript 에 남으면 그걸로 다시 이 세션 것으로 잡히는 순환이 있었다).
    try:
        content = json.loads(line).get('message', {}).get('content')
    except (ValueError, AttributeError):
        return []
    out = []
    for block in content if isinstance(content, list) else []:
        if not isinstance(block, dict) or block.get('type') != 'tool_use':
            continue
        inp = block.get('input') or {}
        if block.get('name') in EDITORS:
            out.append(str(inp.get('file_path') or inp.get('notebook_path') or ''))
        elif block.get('name') == 'Bash':
            # 파일이 쓰기 표시 뒤에 나올 때만 바꾼 것으로 본다. `cat 파일 > /tmp/x` 같은 읽기는 소유가 아니다.
            command = str(inp.get('command', ''))
            if '<<' in command:  # heredoc 스크립트는 경로와 쓰기가 다른 줄에 있을 수 있어 통째로 본다
                if WRITES.search(command):
                    out.append(command)
                continue
            for segment in re.split(r'&&|\|\||;|\|(?!\|)|\n', command):
                hit = WRITES.search(segment)
                if hit:
                    out.append(segment[hit.start():])
    return out


def mine(files, paths):
    # 다른 세션이 바꾼 파일로 이 세션을 막지 않는다(2026-10-21: 30여 개 세션이 남의 decisions 수정으로 계속 차단됨).
    # transcript 를 읽을 수 없으면 판단할 근거가 없다. 전부 이 세션 것으로 보면 남의 변경으로 막는 예전 버그가 되살아나므로
    # 검사하지 않는다(호출한 쪽이 경고를 띄운다).
    if files is None:
        return set()
    wanted = {p: needles(Path(p)) for p in paths}
    found = set()
    for file in files:
        try:
            with open(file, 'rb') as stream:
                for line in stream:
                    if len(found) == len(wanted):
                        return found
                    if b'"tool_use"' not in line:
                        continue
                    hits = [p for p, forms in wanted.items()
                            if p not in found and any(f in line for f in forms)]
                    if not hits:
                        continue
                    texts = [t.encode() for t in edited(line)]
                    found.update(p for p in hits if any(f in t for t in texts for f in wanted[p]))
        except OSError:
            continue
    return found


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == 'update-doc':
            update_doc(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4])
        elif sys.argv[1] == 'append':
            append(Path(sys.argv[2]), sys.argv[3], sys.argv[4])


if __name__ == '__main__':
    main()
