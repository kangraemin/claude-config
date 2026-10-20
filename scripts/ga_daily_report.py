#!/usr/bin/env python3
"""ga_daily_report.py — 서비스 계정이 볼 수 있는 GA4 속성 중 최근 30일 방문이 있는 것(=활성)을 골라 어제 숫자를 텔레그램으로 보낸다. LLM 없음.

  python3 ga_daily_report.py [--day YYYY-MM-DD] [--dry-run]

- 속성 목록은 Admin API accountSummaries로 매번 새로 읽는다. 새 사이트를 GA에 붙이면 따로 손댈 필요 없다.
- 속성마다: 어제 사용자·세션·페이지뷰(그제 대비), 7일 사용자, 유입 상위 3, 페이지 상위 3. 한 속성에 사이트가 여럿이면 호스트별 사용자도.
- 경로로만 나뉜 프로젝트(블로그 속성의 /jeju-stay)는 SPLITS에 적어 따로 칸을 만든다.
- 텔레그램: ~/.claude/.env GA_TG_TOKEN(@ram_ga_bot) / GA_TG_CHAT_ID(없으면 getUpdates → 없으면 DAILY_TG_CHAT_ID로 시도 후 저장).
- 서비스 계정: ~/.claude/ai-paper-analytics-sa.json (GA 뷰어).
- launchd com.ram.ga-daily 09:00.
- 끝에 SNS 조회수(쇼츠·릴스·스레드)를 전날 대비 증감으로 붙인다. 수집은 my-sns sns_stats.py(th-notify tmux 루프) → ~/.cache/sns-stats/<날짜>.json.

출력 마지막 줄: RESULT: OK <속성 수> | FAIL <이유>
"""
import argparse
import datetime as dt
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Filter, RunRealtimeReportRequest, FilterExpression, Metric, OrderBy, RunReportRequest
from google.auth.transport.requests import Request
from google.oauth2 import service_account

HOME = Path.home()
ENV = HOME / '.claude/.env'
SA = HOME / '.claude/ai-paper-analytics-sa.json'
OUT = HOME / '.cache/ga-daily'
# 속성 안에 경로로만 나뉜 프로젝트는 따로 칸을 만든다: 속성 id → [(이름, 경로 앞부분)]
SPLITS = {'364443214': [('제주 숙소 (jeju-stay)', '/jeju-stay')]}


def env(name):
    for line in ENV.read_text().splitlines():
        if line.startswith(name + '='):
            return line.split('=', 1)[1].strip().strip('"')


def properties(cred):
    cred.refresh(Request())
    req = urllib.request.Request('https://analyticsadmin.googleapis.com/v1beta/accountSummaries?pageSize=200',
                                 headers={'Authorization': 'Bearer ' + cred.token})
    r = json.load(urllib.request.urlopen(req, timeout=30))
    return [(p['property'].split('/')[1], p['displayName']) for a in r.get('accountSummaries', []) for p in a.get('propertySummaries', [])]


def run(cl, pid, start, end, metrics, dims=(), limit=0, order=None, path=None):
    flt = FilterExpression(filter=Filter(field_name='pagePath', string_filter=Filter.StringFilter(
        match_type=Filter.StringFilter.MatchType.BEGINS_WITH, value=path))) if path else None
    r = cl.run_report(RunReportRequest(dimension_filter=flt,
        property=f'properties/{pid}', date_ranges=[DateRange(start_date=start, end_date=end)],
        metrics=[Metric(name=m) for m in metrics], dimensions=[Dimension(name=d) for d in dims],
        limit=limit or None, order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order), desc=True)] if order else None))
    return [([d.value for d in x.dimension_values], [float(m.value) for m in x.metric_values]) for x in r.rows]


def delta(cur, prev):
    if not prev:
        return ''
    p = round((cur - prev) / prev * 100)
    return f' ({"+" if p >= 0 else ""}{p}%)'


def section(cl, pid, name, day, path=None):
    y, y2, w = str(day), str(day - dt.timedelta(days=1)), str(day - dt.timedelta(days=6))
    if not run(cl, pid, str(day - dt.timedelta(days=29)), y, ['activeUsers'], path=path):
        # 새 속성은 하루치 집계가 1~2일 늦다(먹맵 10/19 생성 → 실시간 103명인데 일별 0). 실시간이라도 있으면 보낸다.
        if path:
            return None
        rt = cl.run_realtime_report(RunRealtimeReportRequest(property=f'properties/{pid}', metrics=[Metric(name='activeUsers')]))
        now = sum(float(x.metric_values[0].value) for x in rt.rows)
        return (f'📊 {name}\n일별 집계 아직 없음(새 속성) · 지금 30분 실시간 {now:.0f}명', now) if now else None
    m = ['activeUsers', 'sessions', 'screenPageViews']
    cur = (run(cl, pid, y, y, m, path=path) or [([], [0, 0, 0])])[0][1]
    prev = (run(cl, pid, y2, y2, m, path=path) or [([], [0, 0, 0])])[0][1]
    week = (run(cl, pid, w, y, ['activeUsers'], path=path) or [([], [0])])[0][1][0]
    lines = [f'📊 {name}',
             f'어제 사용자 {cur[0]:.0f}{delta(cur[0], prev[0])} · 세션 {cur[1]:.0f} · 페이지뷰 {cur[2]:.0f}{delta(cur[2], prev[2])}',
             f'7일 사용자 {week:.0f}']
    hosts = run(cl, pid, y, y, ['activeUsers'], ['hostName'], 5, 'activeUsers', path=path)
    if len(hosts) > 1:
        lines.append('사이트: ' + ', '.join(f'{d[0]} {v[0]:.0f}' for d, v in hosts))
    src = run(cl, pid, y, y, ['sessions'], ['sessionSource'], 3, 'sessions', path=path)
    if src:
        lines.append('유입: ' + ', '.join(f'{d[0]} {v[0]:.0f}' for d, v in src))
    pages = run(cl, pid, y, y, ['screenPageViews'], ['pagePath'], 3, 'screenPageViews', path=path)
    if pages:
        lines.append('페이지: ' + ', '.join(f'{d[0][:40]} {v[0]:.0f}' for d, v in pages))
    return '\n'.join(lines), cur[0]


SNS = HOME / '.cache/sns-stats'
SNS_NAME = {'yt': '유튜브 쇼츠', 'ig': '인스타 릴스', 'th': '스레드'}


def sns_section():
    """가장 최근 수집 파일과 그 전날 파일을 비교해 계정별 합계·글별 조회수 증감을 쓴다."""
    files = sorted(SNS.glob('*.json'))
    if not files:
        return None
    cur = json.loads(files[-1].read_text())
    prev_f = SNS / f'{dt.date.fromisoformat(files[-1].stem) - dt.timedelta(days=1)}.json'
    prev = {(x['site'], x['id']): x['views'] for x in json.loads(prev_f.read_text())['items']} if prev_f.exists() else {}
    def d(n, key):
        if not prev:
            return ''
        p = prev.get(key)
        return ' (새 글)' if p is None else f' ({"+" if n - p >= 0 else ""}{n - p:,})'
    lines = [f'🎬 SNS 조회수 ({cur["at"][5:10].replace("-", "/")} {cur["at"][11:]} 기준' + (', 전날 대비)' if prev else ', 비교할 전날 기록 없음)')]
    groups = {}
    for x in cur['items']:
        if x['views'] is not None:
            groups.setdefault((x['site'], x['handle']), []).append(x)
    for (site, handle), xs in groups.items():
        tot = sum(x['views'] for x in xs)
        ptot = sum(prev.get((site, x['id']), 0) or 0 for x in xs)
        lines.append(f'{SNS_NAME[site]} @{handle} 합계 {tot:,}' + (f' ({"+" if tot - ptot >= 0 else ""}{tot - ptot:,})' if prev else ''))
        for x in sorted(xs, key=lambda x: -x['views'])[:5]:
            lines.append(f'  · {x["title"][:24]} {x["views"]:,}{d(x["views"], (site, x["id"]))}')
    if cur.get('errors'):
        lines.append('⚠️ 못 읽음: ' + '; '.join(cur['errors']))
    return '\n'.join(lines)


def chat_id(token):
    cid = env('GA_TG_CHAT_ID')
    if cid:
        return cid
    r = json.load(urllib.request.urlopen(f'https://api.telegram.org/bot{token}/getUpdates', timeout=20))
    ids = [i for i in ((u.get('message') or {}).get('chat', {}).get('id') for u in r['result']) if i]
    cid = str(ids[-1]) if ids else env('DAILY_TG_CHAT_ID')  # 개인 채팅 id는 봇이 달라도 같다
    if not cid:
        raise RuntimeError('봇 @ram_ga_bot에 메시지를 한 번 보내야 함')
    return cid


def send(text):
    token = env('GA_TG_TOKEN')
    cid = chat_id(token)
    chunks, cur = [], ''
    for para in text.split('\n\n'):  # 4096자 제한 → 속성 단위로 나눈다
        if len(cur) + len(para) + 2 > 3900:
            chunks.append(cur)
            cur = ''
        cur += para + '\n\n'
    chunks.append(cur)
    for ch in chunks:
        if ch.strip():
            q = urllib.parse.urlencode({'chat_id': cid, 'text': ch, 'disable_web_page_preview': 'true'}).encode()
            urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage', q, timeout=20)
    if not env('GA_TG_CHAT_ID'):
        with ENV.open('a') as fp:
            fp.write(f'GA_TG_CHAT_ID={cid}\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--day')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    day = dt.date.fromisoformat(a.day) if a.day else dt.date.today() - dt.timedelta(days=1)
    cred = service_account.Credentials.from_service_account_file(str(SA), scopes=['https://www.googleapis.com/auth/analytics.readonly'])
    cl = BetaAnalyticsDataClient(credentials=cred)
    secs, errs = [], []
    for pid, name in properties(cred):
        try:
            for nm, path in [(name, None)] + SPLITS.get(pid, []):
                s = section(cl, pid, nm, day, path)
                if s:
                    secs.append(s)
        except Exception as e:
            errs.append(f'{name}: {str(e)[:80]}')
    secs.sort(key=lambda s: -s[1])  # 어제 사용자 많은 순
    text = f'📈 GA {day:%m/%d}({"월화수목금토일"[day.weekday()]}) 리포트\n\n' + '\n\n'.join(s[0] for s in secs)
    try:
        sns = sns_section()
    except Exception as e:
        sns = f'🎬 SNS 조회수 못 읽음: {str(e)[:80]}'
    if sns:
        text += '\n\n' + sns
    if errs:
        text += '\n\n⚠️ 못 읽음: ' + '; '.join(errs)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{day}.txt').write_text(text + '\n')
    print(text)
    if not a.dry_run:
        send(text)
    print(f'RESULT: OK {len(secs)}')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'RESULT: FAIL {e}')
        sys.exit(1)
