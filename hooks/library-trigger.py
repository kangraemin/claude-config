"""필요한 순간에만 검색하며 외부 CLI 실행 시간을 제한한다."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

ERROR = re.compile(r'\b(?:\w*Error|Traceback|failed|failure|fatal|exception)\b', re.I)


def failed(response):
    if not isinstance(response, dict):
        return False
    for key in ('exit_code', 'exitCode', 'returncode'):
        if key in response and response[key] is not None:
            try:
                if int(response[key]) != 0:
                    return True
            except (ValueError, TypeError):
                pass
    return bool(ERROR.search(str(response.get('stderr', ''))))


# 셸 문법 실수·통과 로그는 라이브러리 지식과 무관하다.
SHELL_NOISE = re.compile(r'^(?:\(eval\):\d+:|zsh:|bash: line \d+:|✓|The above exception was|During handling of the above)')
# 내장 예외만 있는 실패는 대개 방금 쓴 코드의 버그다. 모듈·패키지 오류는 유지한다.
LOCAL_BUG = re.compile(r'^(?:TypeError|KeyError|ValueError|IndexError|AttributeError|NameError|'
                       r'UnboundLocalError|ZeroDivisionError|FileNotFoundError|SyntaxError|IndentationError|'
                       r'AssertionError|PermissionError|UnicodeDecodeError|'
                       r'(?:json\.(?:decoder\.)?)?JSONDecodeError)\b')
# 트레이스백에 찍힌 소스 줄은 오류 내용이 아니다(2026-10 오류 트리거 827회 중 주입 159회, 소스 줄 질의는 대부분 weak_evidence).
SOURCE_LINE = re.compile(r'^(?:raise |except\b|with |try:|return |File ")')


def result_rows(context):
    """주입한 문서 경로(와 중복 검사 점수)를 로그용으로 뽑는다. 검색·중복 검사 출력 형식을 모두 받는다."""
    rows = []
    for match in re.finditer(r'(library/\S+?\.md)(?: \((\d+(?:\.\d+)?)\))?', context):
        if match[1] not in [row['path'] for row in rows]:
            rows.append({'path': match[1], **({'score': float(match[2])} if match[2] else {})})
    return rows


def core_error(text):
    lines = [re.sub(r'\x1b\[[0-9;]*m', '', x).strip() for x in str(text).splitlines() if x.strip()]
    lines = [x for x in lines if not SHELL_NOISE.match(x)]
    # 오류 표식이 없는 줄(진행 로그 등)로는 검색하지 않는다.
    matches = [x for x in lines if (ERROR.search(x) or x.startswith('✗')) and not x.startswith('Traceback (')]
    matches = [x for x in matches if not SOURCE_LINE.match(x)]
    if not matches or all(LOCAL_BUG.match(x) for x in matches):
        return ''
    return '\n'.join(matches[-2:])[:2000]


def start_args(command):
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        parts = list(lexer)
        if parts[:2] == ['bouncer', 'start']:
            args = []
            # 파이프·리다이렉트 뒤는 작업 설명이 아니다.
            rest = parts[2:]
            for i, part in enumerate(rest):
                after = rest[i + 1] if i + 1 < len(rest) else ''
                if (set(part) <= set('|&;<>()') or re.fullmatch(r'\d*[<>].*', part)
                        or (part.isdigit() and after[:1] in '<>' and after)):
                    break
                args.append(part)
            return ' '.join(args)
    except (ValueError, TypeError):
        pass
    return ''


def library_path(value):
    root = Path(os.environ.get('LIBRARY_ROOT', Path.home() / 'claude-library')).resolve()
    path = Path(value).expanduser().resolve()
    if path.suffix == '.md' and path.is_relative_to(root / 'library') and path.name != 'index.md':
        return path
    return None


def cache_path(session, kind, value):
    folder = Path.home() / '.claude' / 'cache' / 'library-triggers'
    folder.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(json.dumps([session, kind, value]).encode()).hexdigest()
    return folder / key


def claim(session, kind, value):
    # 세션·문구 해시만 저장하며 원문과 경로는 캐시에 남기지 않는다.
    if not session:
        return True
    try:
        fd = os.open(cache_path(session, kind, value), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        return True
    except FileExistsError:
        return False


def new_document(payload):
    path = library_path((payload.get('tool_input') or {}).get('file_path', ''))
    response = payload.get('tool_response') or {}
    session = str(payload.get('session_id', ''))
    if path is None or not isinstance(response, dict):
        return None
    created = response.get('type') == 'create'
    if created and session:
        claim(session, 'created', str(path))
    if created or (session and cache_path(session, 'created', str(path)).exists()):
        return path
    return None


def command():
    override = os.environ.get('LIBRARY_KB_CMD')
    if override:
        return shlex.split(override)
    if shutil.which('claude-library-kb'):
        return ['claude-library-kb']
    spec = (Path.home() / '.claude/hooks/.learnings-kb-spec').read_text().strip()
    if not spec:
        raise ValueError('빈 CLI 설정')
    return ['uvx', '--with', 'mcp<2', '--from', spec, 'claude-library-kb']


def promote_pending(hooks=None):
    """업데이트 때 설치하지 못한 새 CLI 버전을 검색과 분리해 백그라운드로 설치하고, 성공하면 그 버전으로 바꾼다.

    방금 배포한 버전은 PyPI·uv 목록 캐시가 갱신될 때까지(수 분) 설치되지 않는다.
    hook 시간 안에서 기다리면 검색이 매번 시간 초과되므로 10분에 한 번만 따로 시도한다.
    """
    hooks = Path(hooks or Path.home() / '.claude/hooks')
    pending, stamp = hooks / '.learnings-kb-pending', hooks / '.learnings-kb-pending.tried'
    uvx = shutil.which('uvx')
    if not uvx or not pending.exists():
        return
    try:
        if stamp.exists() and time.time() - stamp.stat().st_mtime < 600:
            return
        stamp.touch()
        spec = pending.read_text().strip()
        script = ('"$0" --refresh-package claude-library-mcp --with "mcp<2" --from "$1" claude-library-kb --help >/dev/null 2>&1'
                  ' && [ "$(cat "$2" 2>/dev/null)" = "$1" ] && mv "$2" "$3" && rm -f "$4"')
        subprocess.Popen(['sh', '-c', script, uvx, spec, str(pending), str(hooks / '.learnings-kb-spec'), str(stamp)],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except Exception:
        pass


def run(payload):
    started = time.monotonic()
    promote_pending()
    tool = payload.get('tool_name')
    data = payload.get('tool_input') or {}
    response = payload.get('tool_response') or {}
    event = payload.get('hook_event_name', 'PostToolUse')
    kind, query = '', ''
    if tool == 'Bash':
        if event == 'PostToolUseFailure' and not payload.get('is_interrupt'):
            kind, query = 'error', core_error(payload.get('error', ''))
        elif failed(response):
            kind, query = 'error', core_error(response.get('stderr') or response.get('stdout', ''))
        elif event == 'PostToolUse':
            kind, query = 'start', start_args(data.get('command', ''))
    elif tool == 'Skill' and data.get('skill') == 'dev-bounce':
        kind, query = 'start', data.get('args', '')
    elif tool in ('Write', 'Edit'):
        # 생성 응답을 확인한 문서는 같은 세션의 후속 편집에서도 재검사한다.
        path = new_document(payload)
        if path:
            kind, query = 'write', str(path)
    cache_value = query
    if kind == 'write':
        cache_value += hashlib.sha256(Path(query).read_bytes()).hexdigest()
    if not query or not claim(str(payload.get('session_id', '')), kind, cache_value):
        return
    context, reason = '', None
    try:
        args = (['duplicates', query] if kind == 'write' else
                ['search', '--format', 'trigger', '--source', 'trigger:' + kind, '--', query])
        env = dict(os.environ, LIBRARY_SESSION_ID=str(payload.get('session_id', '')))
        if kind == 'write':
            env['LIBRARY_LOG'] = '0'
        proc = subprocess.Popen(command() + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True, env=env)
        try:
            stdout, _ = proc.communicate(timeout=max(.1, 3.0 - (time.monotonic() - started)))  # 2026-10-22: 4.5→3초(p90 3.3초, 동기 실행이라 매번 기다림)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            raise TimeoutError()
        if proc.returncode == 0:
            context = stdout.strip()
        else:
            reason = 'search_error'
    except Exception:
        reason = 'unavailable_or_timeout'
    # 검색이 성공하면 CLI 가 결과 경로·점수·gate 해시와 함께 기록한다.
    # 그 기록이 없는 경우(중복 검사, CLI 실패·시간 초과)만 여기서 남긴다. 기본 모드에서는 질의를 해시 처리한다.
    logged_by_cli = kind != 'write' and reason is None
    if not logged_by_cli and os.environ.get('LIBRARY_LOG') != '0' and os.environ.get('LIBRARY_USAGE_LOG') != 'off':
        try:
            import fcntl
            now = datetime.now(timezone.utc)
            root = Path(os.environ.get('LIBRARY_ROOT', Path.home() / 'claude-library')) / '.activity'
            root.mkdir(parents=True, exist_ok=True)
            record = dict(ts=now.isoformat(), action='inject', source='trigger:' + kind,
                          session_id=payload.get('session_id', ''), injected=bool(context),
                          results=result_rows(context),
                          skipped_reason=reason, latency_ms=(time.monotonic()-started)*1000)
            if os.environ.get('LIBRARY_USAGE_LOG') == 'full':
                record['query'] = query
            else:
                record.update(query_sha256=hashlib.sha256(query.encode()).hexdigest()[:16], query_len=len(query))
            version_file = Path.home() / '.claude/hooks/.learnings-version'
            spec_file = Path.home() / '.claude/hooks/.learnings-kb-spec'
            record['version'] = {'install': version_file.read_text().strip() if version_file.exists() else 'unknown',
                                 'kb_spec': spec_file.read_text().strip() if spec_file.exists() else 'unknown',
                                 'autoinject': os.environ.get('LIBRARY_AUTOINJECT', '0')}
            with (root / ('search-' + now.strftime('%Y-%m') + '.jsonl')).open('a') as stream:
                fcntl.flock(stream, fcntl.LOCK_EX)
                stream.write(json.dumps(record, ensure_ascii=False) + '\n')
        except Exception:
            pass
    # 같은 세션에서 이미 넣은 문서만 나왔으면 다시 넣지 않는다(같은 문서 17번 반복 주입이 있었다).
    sid = str(payload.get('session_id', ''))
    if context and kind != 'write' and sid:
        paths = [row['path'] for row in result_rows(context)]
        if paths and not [p for p in [claim(sid, 'doc', p) and p for p in paths] if p]:
            context = ''
    if context:
        print(json.dumps({'hookSpecificOutput': {'hookEventName': event, 'additionalContext': context}}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        run(json.load(sys.stdin))
    except Exception:
        pass
