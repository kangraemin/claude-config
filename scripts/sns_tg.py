#!/usr/bin/env python3
"""SNS 알림 전용 봇(@sns_daily_noti_bot)으로 보낸다. 올린 뒤 '업로드 완료'와 올리기 전 '게시 확인 요청' 둘 다 여기로.
- 사용자 지시(2026-10-22): 내 컴퓨터에서 올리는 SNS 게시는 전부 이 봇으로, 무엇을 올렸는지 본문·사진까지.
- 게시 스크립트(th_post·ig_post·x_post·yt_post·th_reply)가 성공하면 uploaded()를 부른다.
CLI: sns_tg.py done|ask --msg "요약/링크" [--text-file f ...] [사진·영상 ...]
     sns_tg.py check --account oguriworks   # 오늘 이미 올렸나(ALREADY_TODAY n | FREE)
     sns_tg.py log --service 인스타 --account oguriworks --url URL   # 손으로 올린 것 기록
키: ~/.claude/.env SNS_UPLOAD_TG_TOKEN / SNS_UPLOAD_TG_CHAT_ID
"""
import argparse, datetime, json, os, subprocess

LEDGER = os.path.expanduser('~/.cache/sns-ledger.jsonl')  # 모든 세션의 게시 기록 → 하루 1개 규칙 확인용

VIDEO = ('.mp4', '.mov', '.m4v')


def _env():
    e = {}
    for l in open(os.path.expanduser('~/.claude/.env'), encoding='utf-8'):
        l = l.strip().removeprefix('export ')
        if '=' in l and not l.startswith('#'):
            k, v = l.split('=', 1)
            e[k] = v.strip('"\'')
    return e['SNS_UPLOAD_TG_TOKEN'], e['SNS_UPLOAD_TG_CHAT_ID']


def _call(tok, method, args):
    out = subprocess.run(['curl', '-s', *args, f'https://api.telegram.org/bot{tok}/{method}'],
                         capture_output=True, text=True).stdout
    try:
        return bool(json.loads(out).get('ok'))
    except ValueError:
        return False


def send(msg, texts=(), media=()):
    """msg + texts[(이름, 글)] 를 글로, media(사진·영상 경로)를 묶음으로 보낸다. 실패해도 게시 흐름은 막지 않는다."""
    try:
        tok, chat = _env()
        text = msg + ''.join(f'\n\n— {n} —\n{t.strip()}' for n, t in texts if t and t.strip())
        oks = [_call(tok, 'sendMessage', ['-d', f'chat_id={chat}', '--data-urlencode', f'text={text[i:i + 4000]}'])
               for i in range(0, len(text), 4000)]
        media = [m for m in media if m and os.path.isfile(m)]
        for i in range(0, len(media), 10):  # 미디어 묶음은 10개까지
            grp = media[i:i + 10]
            if len(grp) == 1:
                kind = 'video' if grp[0].lower().endswith(VIDEO) else 'photo'
                oks.append(_call(tok, 'send' + kind.capitalize(), ['-F', f'chat_id={chat}', '-F', f'{kind}=@{grp[0]}']))
                continue
            items = [{'type': 'video' if p.lower().endswith(VIDEO) else 'photo', 'media': f'attach://m{j}'} for j, p in enumerate(grp)]
            args = ['-F', f'chat_id={chat}', '-F', 'media=' + json.dumps(items)]
            for j, p in enumerate(grp):
                args += ['-F', f'm{j}=@{p}']
            oks.append(_call(tok, 'sendMediaGroup', args))
        return all(oks)
    except Exception as e:  # noqa: BLE001
        print(f'[sns_tg] 알림 실패: {e}')
        return False


def log(service, account, url, what=''):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'at': datetime.datetime.now().isoformat(timespec='minutes'), 'service': service,
                            'account': account.lstrip('@'), 'url': url, 'what': what[:80]}, ensure_ascii=False) + '\n')


def today(account):
    """오늘 이 계정에 올라간 게시 목록(서비스 무관)."""
    if not os.path.exists(LEDGER):
        return []
    d = datetime.date.today().isoformat()
    rows = [json.loads(l) for l in open(LEDGER, encoding='utf-8') if l.strip()]
    return [r for r in rows if r['at'].startswith(d) and r['account'] == account.lstrip('@')]


def uploaded(service, account, url, texts=(), media=()):
    log(service, account, url, next((t.strip().splitlines()[0] for _, t in texts if t and t.strip()), ''))
    return send(f'[업로드 완료] {service} {account}\n{url}', texts, media)


def ask(title, texts=(), media=()):
    return send(f'[게시 확인 요청] {title}', texts, media)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=['done', 'ask', 'check', 'log'])
    ap.add_argument('--msg', default='')
    ap.add_argument('--service', default='')
    ap.add_argument('--account', default='')
    ap.add_argument('--url', default='')
    ap.add_argument('--what', default='', help='무엇을 올렸나(앱·주제 한 줄)')
    ap.add_argument('--text-file', action='append', default=[])
    ap.add_argument('media', nargs='*')
    a = ap.parse_args()
    if a.kind == 'check':  # 오늘 이 계정에 이미 올렸는지(서비스 무관, 하루 1개 규칙)
        rows = today(a.account)
        for r in rows:
            print(r['at'], r['service'], r['url'], r.get('what', ''))
        print('RESULT:', f'ALREADY_TODAY {len(rows)}' if rows else 'FREE')
        raise SystemExit(0)
    if a.kind == 'log':  # 스크립트 밖에서 손으로 올린 게시를 기록
        log(a.service, a.account, a.url, a.what)
        print('RESULT: LOGGED')
        raise SystemExit(0)
    texts = [(os.path.basename(f), open(f, encoding='utf-8').read()) for f in a.text_file]
    head = '[업로드 완료] ' if a.kind == 'done' else '[게시 확인 요청] '
    print('RESULT:', 'OK' if send(head + a.msg, texts, a.media) else 'FAIL')
