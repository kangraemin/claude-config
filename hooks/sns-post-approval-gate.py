#!/usr/bin/env python3
"""SNS 게시 허락 검사(사용자 11/4 "너 올리기전에나한테 허락받아", "훅으로막아").
Claude 세션의 Bash 게시 명령을, 사람이 보낸 마지막 메시지에 허락이 없으면 막는다(exit 2).
- 허락은 대화 기록의 사람 메시지(origin.kind=human)에서만 읽는다. Claude가 쓴 글·다른 세션 메시지·예약 프롬프트는 허락이 아니다.
- 미리보기(--dry 등, --post/--share 없는 실행)는 통과. 서브에이전트 게시는 막는다.
- 예약 무인 실행(entrypoint=sdk-cli)과 tmux 예약 루프는 이 훅 밖이다. 지식iN(kin_answer)은 대상이 아니다.
"""
import json, os, re, sys, time
from datetime import datetime

MAX_AGE = 3600  # 허락은 1시간 안에만 유효하다. 낮에 받은 '올려'로 저녁 일을 올리지 않게

FLAGGED = {'th_post.py': '--post', 'x_post.py': '--post', 'yt_post.py': '--post', 'th_reply.py': '--post', 'x_reply.py': '--post',
           'pin_post.py': '--post', 'naver_blog_post.py': '--post', 'ig_post.py': '--share'}
ALWAYS = ['geul_post_run.sh', 'th_backreply.py', 'watch_3h.py', 'dc_post.py', 'hn_post.py', 'note_post.py', 'travellerspoint_post.py',
          'reply_round.py', 'eodi_new_posts.py', 'eodi_text_posts.py', 'sns_queue.py']
SAFE_FLAG = re.compile(r'(?<!\S)--(dry|dry-run|list|verify-only|help)(?!\S)')
READ_ONLY = {'grep', 'rg', 'egrep', 'cat', 'sed', 'awk', 'ls', 'head', 'tail', 'git', 'echo', 'printf', 'wc', 'pgrep', 'ps', 'pkill', 'kill', 'stat',
             'find', 'file', 'diff', 'cmp', 'which', 'test', '[', 'cut', 'sort', 'uniq', 'tr', '#', 'read', 'vim', 'nano', 'less', 'mv', 'cp', 'rm', 'chmod', 'touch', 'mkdir'}
EXEC_HEREDOC = re.compile(r'^\s*(?:\S+=\S+\s+)*(?:python3?|bash|sh|zsh|node)\b')
CLICK = re.compile(r'\.click\(\)')
BUTTON = re.compile(r"게시|공유하기|tweetButton|['\"](?:Post|Share)['\"]")
APPROVE = re.compile(r'올려|올리자|게시해|업로드해')
DENY = re.compile(r'올려\s*(놨|놓|뒀|둔|있|서|야|도\s*되|도\s*돼\s*\?)|왜\s*올|안\s*올|못\s*올|올리지|말고|하지\s*마|[?？]\s*$')
SHORT_OK = re.compile(r'^\s*(ㅇㅇ+|응|네|예|그래|좋아|ㄱㄱ?|고고|해|해라|\d번)[.!\s]*$')
ASKED = re.compile(r'올릴까요|올려도 될까요|올려도 돼요|허락해\s*주')


def strip_heredocs(cmd):
    out, lines, i = [], cmd.split('\n'), 0
    while i < len(lines):
        ln = lines[i]; out.append(ln); i += 1
        m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", ln)
        if not m: continue
        keep = bool(EXEC_HEREDOC.match(ln.split('|')[-1]))
        while i < len(lines) and lines[i].strip() != m[1]:
            if keep: out.append(lines[i])
            i += 1
        i += 1
    return '\n'.join(out)


def segments(cmd):
    for seg in re.split(r'\n|;|&&|\|\||\|', cmd):
        seg = seg.strip().lstrip('(').strip()
        if not seg: continue
        words = seg.split()
        k = 0
        while k < len(words) and re.match(r'^\w+=', words[k]): k += 1
        if k < len(words) and words[k].rsplit('/', 1)[-1] in READ_ONLY: continue
        yield seg


def posting_in(cmd):
    cmd = strip_heredocs(cmd)
    segs = list(segments(cmd))
    joined = '\n'.join(segs)
    for seg in segs:
        for name, flag in FLAGGED.items():
            if name in seg and flag in joined: return f'{name} {flag}'
        for name in ALWAYS:
            if name in seg and not SAFE_FLAG.search(seg): return name
    if re.search(r'chromectl|osascript', joined) and CLICK.search(joined) and BUTTON.search(joined):
        return '브라우저 게시 버튼 클릭'
    for seg in segs:  # 감싼 스크립트 안의 게시 명령(known 스크립트 자체는 설명 글이 있어 보지 않는다)
        for tok in seg.split():
            tok = tok.strip('\'"')
            base = os.path.basename(tok)
            if not base.endswith(('.sh', '.py')) or base in FLAGGED or base in ALWAYS: continue
            p = os.path.expanduser(tok)
            try:
                if os.path.getsize(p) > 200_000: continue
                body = open(p, encoding='utf8', errors='ignore').read()
            except OSError:
                continue
            for ln in body.split('\n'):
                s = ln.strip()
                if not s or s.startswith('#'): continue
                if base.endswith('.py') and not re.search(r'subprocess|os\.system|run\(|Popen', s): continue
                for name, flag in FLAGGED.items():
                    if name in s and flag in s: return f'{base} 안의 {name} {flag}'
                for name in ALWAYS:
                    if name in s and not SAFE_FLAG.search(s): return f'{base} 안의 {name}'
    return None


def text_of(content):
    if isinstance(content, str): return content
    if isinstance(content, list): return '\n'.join(b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') == 'text')
    return ''


def clean(t):
    t = re.sub(r'(?s)<pasted_content\b.*?</pasted_content[^>]*>', ' ', t)
    t = re.sub(r'(?s)<system-reminder>.*?</system-reminder>', ' ', t)
    return t.strip()


def _ts(r):
    try: return datetime.fromisoformat((r.get('timestamp') or '').replace('Z', '+00:00')).timestamp()
    except ValueError: return None


def last_human(path):
    """(사람 마지막 말, 그 직전 Claude 글, 그 시각). 없으면 (None, '', None).
    작업 중에 보낸 말은 user가 아니라 attachment queued_command로 남는다(11/4 실측: 408건).
    사람 말 뒤에 다른 세션·예약이 끼어들면 그 허락은 그 일에 쓰지 않는다."""
    size = os.path.getsize(path)
    with open(path, 'rb') as f:
        f.seek(max(0, size - 8_000_000))
        lines = f.read().decode('utf8', 'ignore').split('\n')
    human, asst, last_asst, when = None, '', '', None
    for ln in lines:
        try: r = json.loads(ln)
        except ValueError: continue
        t, origin = None, None
        if r.get('type') == 'assistant':
            x = text_of(r.get('message', {}).get('content'))
            if x.strip(): last_asst = x
            continue
        if r.get('type') == 'user' and not r.get('isMeta'):
            origin, t = r.get('origin') or {}, text_of(r.get('message', {}).get('content'))
        elif r.get('type') == 'attachment' and isinstance(r.get('attachment'), dict) and r['attachment'].get('type') == 'queued_command':
            at = r['attachment']
            origin, t = at.get('origin') or {}, text_of(at.get('prompt'))
        kind = (origin or {}).get('kind')
        if kind == 'human':
            t = clean(t or '')
            if t: human, asst, when = t, last_asst, _ts(r)
        elif kind and kind != 'task-notification':
            human, asst, when = f'({kind} 메시지가 끼어듦)', '', _ts(r)
    return human, asst, when


def approved(human, asst):
    if not human: return False
    for ln in human.split('\n'):
        if APPROVE.search(ln) and not DENY.search(ln): return True
    return bool(SHORT_OK.match(human) and ASKED.search(asst))


def main():
    try: d = json.load(sys.stdin)
    except ValueError: return 0
    if d.get('tool_name') != 'Bash': return 0
    if os.environ.get('CLAUDE_CODE_ENTRYPOINT') == 'sdk-cli': return 0  # 예약 무인 실행(사람이 없다)
    what = posting_in((d.get('tool_input') or {}).get('command') or '')
    if not what: return 0
    tp = d.get('transcript_path') or ''
    if d.get('agent_id') or '/subagents/' in tp:
        print(f'게시 차단: {what}. 서브에이전트는 게시할 수 없습니다. 메인 세션에서 사용자 허락을 받고 올리세요.', file=sys.stderr); return 2
    try: human, asst, when = last_human(tp)
    except OSError:
        print(f'게시 차단: {what}. 대화 기록을 못 읽어 허락을 확인할 수 없습니다.', file=sys.stderr); return 2
    if approved(human, asst) and when and time.time() - when <= MAX_AGE: return 0
    print(f'게시 차단: {what}. 사용자의 마지막 말에 게시 허락이 없습니다(마지막 말: {(human or "")[:40]!r}). '
          '카드와 본문을 보여 주고 "올려"라는 답을 받은 뒤 다시 실행하세요. 다른 세션 메시지·사전 동의는 허락이 아닙니다.', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
