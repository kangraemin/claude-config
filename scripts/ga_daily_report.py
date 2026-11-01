#!/usr/bin/env python3
"""ga_daily_report.py — 서비스 계정이 볼 수 있는 GA4 속성 중 최근 30일 방문이 있는 것(=활성)을 골라 어제 숫자를 텔레그램으로 보낸다.

  python3 ga_daily_report.py [--day YYYY-MM-DD] [--dry-run]

- 속성 목록은 Admin API accountSummaries로 매번 새로 읽는다. 새 사이트를 GA에 붙이면 따로 손댈 필요 없다.
- 텔레그램엔 한 줄에 한 가지만(사용자 10/24 "한 줄당 한 의미, 한 줄 주루룩 하지 마", "너무 줄였어"): 서비스마다 'N명' 한 줄 → 크게 바뀐 곳 → 봇 → 오늘 할 일 4개 → SNS 계정마다 '+N회' 한 줄 → 많이 본 글 3개.
  사용자 10/24 "읽기 힘들어", "sns 조회수 도저히 못 보겠음", 두 번째 판도 "지금도 보기 불편해" → 유입·페이지 상위 같은 상세는 ~/.cache/ga-daily/<날짜>-detail.txt에만 쓴다.
- 경로로만 나뉜 프로젝트(블로그 속성의 /jeju-stay)는 SPLITS에 적어 따로 칸을 만든다.
- 텔레그램: ~/.claude/.env GA_TG_TOKEN(@ram_ga_bot) / GA_TG_CHAT_ID(없으면 getUpdates → 없으면 DAILY_TG_CHAT_ID로 시도 후 저장).
- 서비스 계정: ~/.claude/ai-paper-analytics-sa.json (GA 뷰어).
- launchd com.ram.ga-daily 08:00(사용자 10/28 "ga리포트 오전8시에").
- 사람에 가까운 수: GA4는 알려진 봇만 자동으로 뺀다. 그래서 '실제로 머문 방문'(참여 세션)과 1인 평균 참여 초를 같이 쓴다.
- 할 일 한 문장(claude -p 구독 로그인, API 키 아님, claude-p.sh가 한도 걸린 계정 건너뜀). 실패하면 숫자만. --no-ai로 끔.
- 강화 서바이버(이게 되네) 칸에 '포털' 줄: itch API 조회(~/.cache/game-stats/itch 스냅샷 대비)·CrazyGames 상태(10/31).
- 서비스마다 '웹' 한 덩어리: GA 방문 + 구글 검색(서치콘솔 가장 최근 하루, 2~3일 늦음, 그 전날 대비)과 많이 찾은 검색어 하나(사용자 11/1 '합쳐서', '왜 일주일치'). 먹맵은 국내·외국을 나눈다(SPLIT_KR). 7일 합계·검색어·페이지 상세는 detail 파일과 AI 할 일에 넘긴다.
- 끝에 SNS 조회수(쇼츠·릴스·스레드) 계정별 늘어난 수와 가장 많이 늘어난 글 하나. 수집은 my-sns sns_stats.py(th-notify tmux 루프) → ~/.cache/sns-stats/<날짜>.json.

출력 마지막 줄: RESULT: OK <속성 수> | FAIL <이유>
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Filter, RunRealtimeReportRequest, FilterExpression, FilterExpressionList, Metric, OrderBy, RunReportRequest
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


def run(cl, pid, start, end, metrics, dims=(), limit=0, order=None, path=None, skip=()):
    """path: 그 경로로 시작하는 것만. skip: 그 경로로 시작하는 것은 뺀다(같은 속성에 따로 칸이 있는 하위 사이트). localhost(개발 접속)는 늘 뺀다."""
    def starts(v):
        return Filter(field_name='pagePath', string_filter=Filter.StringFilter(match_type=Filter.StringFilter.MatchType.BEGINS_WITH, value=v))
    parts = [FilterExpression(not_expression=FilterExpression(filter=Filter(field_name='hostName', string_filter=Filter.StringFilter(value='localhost'))))]
    if path:
        parts.append(FilterExpression(filter=starts(path)))
    parts += [FilterExpression(not_expression=FilterExpression(filter=starts(v))) for v in skip]
    flt = FilterExpression(and_group=FilterExpressionList(expressions=parts))
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


def section(cl, pid, name, day, path=None, skip=()):
    y, y2, w = str(day), str(day - dt.timedelta(days=1)), str(day - dt.timedelta(days=6))
    if not run(cl, pid, str(day - dt.timedelta(days=29)), y, ['activeUsers'], path=path, skip=skip):
        # 새 속성은 하루치 집계가 1~2일 늦다(먹맵 10/19 생성 → 실시간 103명인데 일별 0). 실시간이라도 있으면 보낸다.
        if path:
            return None
        rt = cl.run_realtime_report(RunRealtimeReportRequest(property=f'properties/{pid}', metrics=[Metric(name='activeUsers')]))
        now = sum(float(x.metric_values[0].value) for x in rt.rows)
        return {'name': name, 'users': now, 'prev': None, 'engaged': None, 'per': 0, 'new': True,
                'detail': f'📊 {name}\n일별 집계 아직 없음(새 속성) · 지금 30분 실시간 {now:.0f}명', 'data': None} if now else None
    m = ['activeUsers', 'sessions', 'screenPageViews', 'engagedSessions', 'userEngagementDuration']
    cur = (run(cl, pid, y, y, m, path=path, skip=skip) or [([], [0] * 5)])[0][1]
    prev = (run(cl, pid, y2, y2, m, path=path, skip=skip) or [([], [0] * 5)])[0][1]
    week = (run(cl, pid, w, y, ['activeUsers'], path=path, skip=skip) or [([], [0])])[0][1][0]
    # GA4는 알려진 봇만 자동으로 뺀다. 우리 e2e·모르는 봇은 남는다 → '참여 세션'(10초+ 머묾·2페이지+·전환)을 사람에 가까운 수로 따로 보인다
    per = cur[4] / cur[0] if cur[0] else 0
    lines = [f'📊 {name}',
             f'어제 사용자 {cur[0]:.0f}{delta(cur[0], prev[0])} · 세션 {cur[1]:.0f} · 페이지뷰 {cur[2]:.0f}{delta(cur[2], prev[2])}',
             f'실제로 머문 방문 {cur[3]:.0f}{delta(cur[3], prev[3])}/{cur[1]:.0f}세션 · 1인 평균 {per:.0f}초',
             f'7일 사용자 {week:.0f}']
    hosts = run(cl, pid, y, y, ['activeUsers'], ['hostName'], 5, 'activeUsers', path=path, skip=skip)
    if len(hosts) > 1:
        lines.append('사이트: ' + ', '.join(f'{d[0]} {v[0]:.0f}' for d, v in hosts))
    src = run(cl, pid, y, y, ['sessions'], ['sessionSource'], 10, 'sessions', path=path, skip=skip)
    if src:
        lines.append('유입: ' + ', '.join(f'{d[0]} {v[0]:.0f}' for d, v in src[:3]))
    pages = run(cl, pid, y, y, ['screenPageViews'], ['pagePath'], 3, 'screenPageViews', path=path, skip=skip)
    if pages:
        lines.append('페이지: ' + ', '.join(f'{d[0][:40]} {v[0]:.0f}' for d, v in pages))
    days = run(cl, pid, w, y, ['activeUsers', 'engagedSessions', 'userEngagementDuration'], ['date'], path=path, skip=skip)
    src7 = run(cl, pid, w, y, ['sessions', 'engagedSessions'], ['sessionSource'], 6, 'sessions', path=path, skip=skip)
    data = {'7일 날짜별 [사용자, 참여세션, 총참여초]': {d[0]: v for d, v in sorted(days)},
            '7일 유입별 [세션, 참여세션]': {d[0]: v for d, v in src7}}
    return {'name': name, 'users': cur[0], 'prev': prev[0], 'engaged': cur[3], 'per': per, 'new': False, 'src': src, 'pid': pid, 'path': path, 'skip': skip,
            'detail': '\n'.join(lines), 'data': data}


SNS = HOME / '.cache/sns-stats'
SNS_NAME = {'yt': '유튜브', 'ig': '인스타', 'th': '스레드'}
WHO = {'dev_ram_kang': '개인', 'eodi_sseot': '어디썼', 'eodimeok': '어디먹', 'oguriworks': '오구리웍스', 'geulmagam': '글마감', 'mukmap.kr': '먹맵', 'mukmap_kr': '먹맵', 'ssum.pandok': '썸 판독기', 'eodimeok.kr': '어디먹', 'koubonoshiori': '公募の栞', 'nunsseolmi.kr': '오늘의 눈썰미', 'sharpeyesdaily': '오늘의 눈썰미'}  # 썸 판독기는 웹 칸 이름과 맞춘다(11/1 전엔 '썸판독기'로 따로 놀았다)
SPLIT_KR = {'먹맵'}  # 사용자 11/1 "먹맵 외국 / 국내 이렇게 분리해서 말해줘": 웹 사용자·구글 검색을 국내·외국으로
SNS_MIN = 50  # 하루에 이만큼 안 늘면 안 적는다


def sns_by_service():
    """가장 최근 수집 파일과 그 전날 파일을 비교해 서비스마다 'SNS' 줄({서비스: [줄]}, 못 읽은 곳)을 만든다. 늘어난 계정만, 많이 늘어난 글 하나를 붙인다."""
    files = sorted(SNS.glob('*.json'))
    if not files:
        return {}, []
    cur = json.loads(files[-1].read_text())
    errs = [e.split(':')[0] for e in cur.get('errors') or []]
    prev_f = SNS / f'{dt.date.fromisoformat(files[-1].stem) - dt.timedelta(days=1)}.json'
    if not prev_f.exists():
        return {}, errs + ['전날 기록 없음']
    prev = {(x['site'], x['id']): x['views'] for x in json.loads(prev_f.read_text())['items']}
    groups = {}
    for x in cur['items']:
        if x['views'] is not None:
            groups.setdefault((x['site'], x['handle']), []).append(x)
    out = {}
    for (site, handle), xs in groups.items():
        gain = {x['id']: max(0, x['views'] - (prev.get((site, x['id'])) or 0)) for x in xs}
        tot = sum(gain.values())
        if tot <= 0:
            continue
        line = f'- {SNS_NAME[site]} +{tot:,}회'
        best = max(xs, key=lambda x: gain[x['id']])
        if gain[best['id']] >= SNS_MIN:
            title = best['title'].replace('#shorts', '').split('\n')[0].strip()
            line += f' (많이 본 글: {title[:20] + "…" if len(title) > 20 else title} +{gain[best["id"]]:,}회)'
        out.setdefault(WHO.get(handle, handle), []).append((tot, line))
    return {k: [t for _, t in sorted(v, key=lambda u: -u[0])] for k, v in out.items()}, errs


TOSS = Path.home() / '.cache/toss-stats'  # my-sns eodi-sns/scripts/toss_stats.py 가 6시간마다 쓴다


def toss_by_service(day):
    """앱인토스 콘솔 숫자(사용자 10/28 "토스에서 나온 지표들도 ga 분석기에 합쳐"). ({앱: (사용자, [줄])}, 0명 앱, 오류)."""
    files = sorted(TOSS.glob('*.json'))
    if not files:
        return {}, [], None
    cur = json.loads(files[-1].read_text())
    if cur.get('error'):
        return {}, [], cur['error']
    d, p = str(day), str(day - dt.timedelta(days=1))
    rows, zero = {}, []
    for x in cur['apps']:
        if x.get('error'):
            rows[x['name']] = (0, ['- 못 읽음'])
            continue
        u, pu, n = x['au'].get(d, 0), x['au'].get(p, 0), x['new'].get(d, 0)
        if not u:
            zero.append(x['name'])
            continue
        lines = [f'- {u}명 (신규 {n}, 전날 {pu}명)']
        ref = sorted((x.get('referrer_by_day') or {}).get(d, {}).items(), key=lambda kv: -kv[1])[:3]
        if ref:
            lines.append('- ' + ' · '.join(f'{k} {v}' for k, v in ref))
        rows[x['name']] = (u, lines)
    return rows, zero, None


GAME = HOME / '.cache/game-stats'  # 포털판 게임 숫자(itch API 스냅샷)
GAME_SVC = '강화 서바이버'  # GA 속성 이름과 같은 칸에 붙인다(웹판 GA4 = 561399106)
ITCH_GAME = 5265293  # kangraemin.itch.io/wait-it-worked. itch판은 GA를 안 보내 API 누적값만 있다(브라우저 플레이는 downloads에 안 잡힘)
CRAZY_STATUS = '심사 중(공개 전)'  # 공개되면 developer.crazygames.com 대시보드 숫자로 바꾼다(API 없음, 로그인 CRAZYGAMES_EMAIL/PASSWORD)


def game_by_service(day):
    """사용자 10/31 "매일아침에 ga에 그것들도오는지 … 안오면오게해": itch 조회·다운로드(전날 스냅샷 대비)와 CrazyGames 상태. ({서비스: [줄]}, 오류)."""
    key = env('ITCH_API_KEY')
    lines = []
    if key:
        r = json.load(urllib.request.urlopen(f'https://itch.io/api/1/{key}/my-games', timeout=20))
        g = next((x for x in r.get('games', []) if x['id'] == ITCH_GAME), None)
        if g:
            cur = {'views': g.get('views_count', 0), 'downloads': g.get('downloads_count', 0)}
            d = GAME / 'itch'
            d.mkdir(parents=True, exist_ok=True)
            (d / f'{day + dt.timedelta(days=1)}.json').write_text(json.dumps(cur))  # 리포트 날(오늘 아침) 기준 누적
            prev = sorted(f for f in d.glob('*.json') if f.stem < str(day + dt.timedelta(days=1)))
            if prev:
                pv = json.loads(prev[-1].read_text())
                lines.append(f'- itch 조회 +{cur["views"] - pv["views"]}회 (누적 {cur["views"]}회, 다운로드 {cur["downloads"]})')
            else:
                lines.append(f'- itch 조회 누적 {cur["views"]}회 (다운로드 {cur["downloads"]}, 내일부터 전날 대비)')
    lines.append(f'- CrazyGames {CRAZY_STATUS}')
    return {GAME_SVC: lines}


AI_PROMPT = """아래는 서비스별 어제 숫자다(웹 GA4 방문·유입, 구글 서치콘솔 날짜별·7일·검색어·페이지, 토스앱, SNS 조회). 서비스마다 세 가지를 써라.

- "요약": 이 서비스 어제를 한 문장으로(웹·검색·토스앱·SNS를 한데 보고 제일 중요한 것 하나). 35자 안팎. '자료가 없어 알 수 없음' 같은 말은 쓰지 말고 빈 문자열로 둔다.
- "검색": 구글 서치콘솔 해석 한 줄(자료가 없으면 빈 문자열). 무엇이 늘고 줄었는지, 노출 대비 클릭이 왜 적은지, 어느 검색어·페이지가 끄는지. 날짜별 노출이 갑자기 꺾였으면 그 날짜를 쓴다. 40자 안팎.
- "종합": 웹·검색·토스앱·SNS를 한데 본 인사이트 두 줄(배열 2개). 어디서 사람이 오고 어디서 끊기는지, 채널끼리 이어지는지(예: SNS 조회는 느는데 방문이 없다). 각 40자 안팎, 숫자는 자료에 있는 것만.
- "할일": 오늘 해 볼 일 한 문장, 25자 안팎, '~하기'로 끝낸다. 페이지 주소는 그대로 쓴다. 예: '스레드에 구좌읍 글 하나 더 올리기'.

규칙
- 쉬운 한국어. 영어·전문용어(CTR, 임프레션 등) 금지. 지어낸 숫자 금지.
- 웹 유입이 (direct)·(not set)뿐이고 1인 평균 몇 초면 "할일"에 '봇으로 보여 할 일 없음'이라고 쓴다.
- 출력은 JSON 하나만: {"<서비스 이름 그대로>": {"요약": "…", "검색": "…", "종합": ["…", "…"], "할일": "…"}}. 다른 말 금지.

자료:
"""


# 구글 서치콘솔(사용자 10/31 "ga 리포트줄때도 구글서치콘솔도 참고해서분석해서줘"). 같은 서비스 계정이 사이트 소유자다.
# 사이트 → 서비스 이름(short() 결과와 같게). 블로그는 하위 경로 사이트를 빼고 센다.
GSC = {'https://kangraemin.github.io/oneul-kkum/': '꿈해몽', 'https://kangraemin.github.io/jeju-stay/': '제주 숙소',
       'https://kangraemin.github.io/': '블로그', 'https://geulmagam.vercel.app/': '글마감', 'https://xn--ob0butqet42c6pmgpe.kr/': '글마감',
       'https://eodimeok.kr/': '어디먹', 'https://mukmap.kr/': '먹맵', 'https://xn--zf0b677a.kr/': '상권.kr',
       'https://ssum-pandok.remin1994.workers.dev/': '썸 판독기', 'https://oguriworks.com/': '오구리웍스',
       'https://eodisseot.pages.dev/': '어디썼', 'https://eodisseot.vercel.app/': '어디썼', 'sc-domain:paper-digest.app': 'ai-paper',
       'https://koubonoshiori.com/': '公募の栞', 'https://threads-unfollow.pages.dev/': '스레드언팔확인'}  # 11/1 일본판·언팔확인 빠져 있던 것
GSC_SKIP = {'https://kangraemin.github.io/': ['/oneul-kkum/', '/jeju-stay/']}


def gsc_by_service(day):
    """서비스마다 구글 검색 7일(노출·클릭·평균 순위)과 그 앞 7일 비교, 많이 찾은 검색어·페이지. 서치콘솔은 2~3일 늦어 마지막 날짜를 따로 적는다."""
    from google.auth.transport.requests import AuthorizedSession
    s = AuthorizedSession(service_account.Credentials.from_service_account_file(str(SA), scopes=['https://www.googleapis.com/auth/webmasters.readonly']))
    have = {x['siteUrl'] for x in s.get('https://www.googleapis.com/webmasters/v3/sites').json().get('siteEntry', [])}
    acc = {}
    for site, svc in GSC.items():
        if site not in have:
            continue
        url = f'https://www.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(site, safe="")}/searchAnalytics/query'
        flt = [{'filters': [{'dimension': 'page', 'operator': 'notContains', 'expression': p} for p in GSC_SKIP.get(site, [])]}] if site in GSC_SKIP else []
        q = lambda body: s.post(url, json={**body, 'dimensionFilterGroups': flt}).json().get('rows', [])
        rows = q({'startDate': str(day - dt.timedelta(days=20)), 'endDate': str(day), 'dimensions': ['date'], 'rowLimit': 30})
        if not rows:
            continue
        last = max(dt.date.fromisoformat(r['keys'][0]) for r in rows)
        w0, p0 = last - dt.timedelta(days=6), last - dt.timedelta(days=13)
        a = acc.setdefault(svc, {'last': last, 'cur': [0, 0, 0], 'prev': [0, 0], 'q': {}, 'p': {}, 'day': {}, 'cty': {}})
        a['last'] = max(a['last'], last)
        if svc in SPLIT_KR:  # 국내(kor)·외국 나눠 하루치
            for r in q({'startDate': str(last - dt.timedelta(days=1)), 'endDate': str(last), 'dimensions': ['date', 'country'], 'rowLimit': 500}):
                v = a['cty'].setdefault(r['keys'][0], {}).setdefault('국내' if r['keys'][1] == 'kor' else '외국', [0, 0])
                v[0] += r['impressions']; v[1] += r['clicks']
        for r in rows:
            d = dt.date.fromisoformat(r['keys'][0])
            v = a['day'].setdefault(r['keys'][0], [0, 0, 0])
            v[0] += r['impressions']; v[1] += r['clicks']; v[2] += r['position'] * r['impressions']
            if d >= w0:
                a['cur'][0] += r['impressions']; a['cur'][1] += r['clicks']; a['cur'][2] += r['position'] * r['impressions']
            elif d >= p0:
                a['prev'][0] += r['impressions']; a['prev'][1] += r['clicks']
        for dim, key in (('query', 'q'), ('page', 'p')):
            for r in q({'startDate': str(w0), 'endDate': str(last), 'dimensions': [dim], 'rowLimit': 10}):
                v = a[key].setdefault(r['keys'][0], [0, 0, 0])
                v[0] += r['impressions']; v[1] += r['clicks']; v[2] += r['position'] * r['impressions']
    gd = lambda c, p: (f' (전주 {p:,.0f})' if p < 30 else delta(c, p)) if p else ''  # 앞 주가 작으면 % 대신 수
    out = {}
    for svc, a in acc.items():
        imp, clk, pos = a['cur']
        if not imp and not a['prev'][0]:
            continue
        top = lambda d, n: sorted(d.items(), key=lambda kv: -kv[1][0])[:n]
        # 사용자 11/1 "서치콘솔은 왜 일주일치를 줘": 하루치(서치콘솔이 2~3일 늦어 가장 최근 날)를 그 전날과 비교. 7일 합계는 AI·상세 파일에만
        L, L1 = str(a['last']), str(a['last'] - dt.timedelta(days=1))
        dc, dp = a['day'].get(L, [0, 0, 0]), a['day'].get(L1, [0, 0, 0])
        avg = f' · 평균 {dc[2] / dc[0]:.0f}위' if dc[0] else ''
        pd_ = lambda c, p: f' (전날 {p:,.0f})'
        lines = [f'- 구글 검색 {a["last"]:%m/%d} 하루: 노출 {dc[0]:,.0f}{pd_(dc[0], dp[0])} · 클릭 {dc[1]:,.0f}{pd_(dc[1], dp[1])}{avg}']
        if svc in SPLIT_KR:
            for k in ('국내', '외국'):
                c, pv = a['cty'].get(L, {}).get(k, [0, 0]), a['cty'].get(L1, {}).get(k, [0, 0])
                lines.append(f'  · {k}: 노출 {c[0]:,.0f} (전날 {pv[0]:,.0f}) · 클릭 {c[1]:,.0f} (전날 {pv[1]:,.0f})')
        tq = top(a['q'], 1)
        if tq:
            k, v = tq[0]
            lines.append(f'- 이번 주 많이 찾은 말: {k} (노출 {v[0]:,.0f} · 클릭 {v[1]:,.0f})')
        det = [f'🔎 {svc} 구글 검색 {a["last"] - dt.timedelta(days=6):%m/%d}~{a["last"]:%m/%d}', f'7일 노출 {imp:,.0f}{gd(imp, a["prev"][0])} · 클릭 {clk:,.0f}{gd(clk, a["prev"][1])}', lines[0][2:]]
        det.append('검색어: ' + ', '.join(f'{k} {v[0]:.0f}/{v[1]:.0f}/{v[2] / v[0]:.0f}위' for k, v in top(a['q'], 8) if v[0]))
        det.append('페이지: ' + ', '.join(f'{k} {v[0]:.0f}/{v[1]:.0f}' for k, v in top(a['p'], 5)))
        out[svc] = {'lines': lines, 'detail': '\n'.join(det), 'day': (a['last'], dc, dp, {k: a['cty'].get(L, {}).get(k, [0, 0]) for k in ('국내', '외국')}),
                    'data': {'날짜별 [노출, 클릭]': {k: v[:2] for k, v in sorted(a['day'].items())}, '구글 검색 7일 [노출, 클릭, 평균순위]': [imp, clk, round(pos / imp, 1) if imp else None], '그 앞 7일 [노출, 클릭]': a['prev'],
                             '검색어 [노출, 클릭, 평균순위]': {k: [v[0], v[1], round(v[2] / v[0], 1)] for k, v in top(a['q'], 10) if v[0]},
                             '페이지 [노출, 클릭]': {k: v[:2] for k, v in top(a['p'], 8)}}}
    return out


def ai_notes(svc):
    """claude -p(구독 로그인, API 키 아님)로 서비스별 검색 해석·종합 두 줄·할 일. 실패하면 {} → 숫자만 보낸다."""
    src = {}
    for name, v in svc.items():
        d = {}
        if 'web' in v:
            d['웹 어제 요약'] = v['web']['detail'].split('\n', 1)[1]
            d.update(v['web']['data'] or {})
        if v.get('gsc_data'):
            d['구글 검색'] = v['gsc_data']
        if 'toss' in v:
            d['토스앱'] = v['toss'][1]
        if v.get('sns'):
            d['SNS'] = v['sns']
        if d:
            src[name] = d
    env = {k: v for k, v in os.environ.items() if k not in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL')}
    env['PATH'] = env.get('PATH', '') + ':/opt/homebrew/bin:/usr/local/bin:' + str(HOME / '.local/bin')
    try:
        r = subprocess.run([str(HOME / '.claude/scripts/claude-p.sh'), '-p', AI_PROMPT + json.dumps(src, ensure_ascii=False),
                            '--system-prompt', '너는 서비스 방문 통계를 짧게 분석하는 도구다. JSON만 출력한다.', '--tools', '',
                            '--strict-mcp-config', '--setting-sources', '', '--no-session-persistence', '--model', 'sonnet'],
                           capture_output=True, text=True, timeout=900, env=env, cwd='/tmp')
        out = r.stdout.strip()
        notes = json.loads(out[out.find('{'):out.rfind('}') + 1])
        return {k: v for k, v in notes.items() if isinstance(v, dict)}
    except Exception as e:
        print(f'AI 분석 실패: {str(e)[:120]}', file=sys.stderr)
        return {}


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


def short(name):
    """'제주 숙소 (jeju-stay)'·'Ram's tech blog - GA4' 같은 꼬리를 뗀다."""
    n = re.sub(r'\s*(\([^)]*\)|- GA4)$', '', name) or name
    n = re.sub(r'(?<=[가-힣])\s+[A-Za-z][\w-]*$', '', n)
    return {'MukMap': '먹맵', "Ram's tech blog": '블로그', '오늘꿈해몽': '꿈해몽'}.get(n, n)


def channel(src):
    """GA sessionSource → 사람이 바로 알아듣는 길 이름. 모르는 사이트는 '다른 사이트'."""
    x = src.lower()
    for keys, name in [(('(direct)',), '직접 접속'), (('(not set)',), '출처 모름'),
                       (('chatgpt', 'perplexity', 'claude.ai', 'gemini', 'copilot'), 'AI 답변'),
                       (('kin.naver',), '지식iN'), (('cafe.naver', 'blog.naver'), '네이버 카페·블로그'),
                       (('naver',), '네이버 검색'), (('google',), '구글 검색'), (('bing', 'daum', 'duckduckgo'), '다른 검색'),
                       (('threads',), '스레드'), (('instagram',), '인스타'), (('youtube',), '유튜브'), (('t.co', 'x.com', 'twitter'), 'X'),
                       (('kangraemin.github.io',), '개발 블로그'), (('toss',), '토스')]:
        if any(k in x for k in keys):
            return name
    return '다른 사이트'


def src_line(x):
    """사용자 10/26 "어느 채널에서 들어왔는지도 서비스별로" + "정성스럽게" → 길별로 묶어 비중(방문 10번 이상) 또는 횟수로."""
    tot = sum(v[0] for _, v in x['src'])
    by = {}
    for d, v in x['src']:
        by[channel(d[0])] = by.get(channel(d[0]), 0) + v[0]
    top = sorted(by.items(), key=lambda kv: -kv[1])[:3]
    if tot >= 10:
        return '- ' + ' · '.join(f'{k} {v / tot:.0%}' for k, v in top)
    return '- ' + ' · '.join(f'{k} {v:.0f}번' for k, v in top)


def bot(x):
    """5명 이상 왔는데 머문 방문이 1할도 안 되고 1인 평균 5초 미만이면 봇·자동 테스트로 본다."""
    return x['engaged'] is not None and x['users'] >= 5 and x['engaged'] < x['users'] * 0.1 and x['per'] < 5


def kr_split(cl, x, day, raw=False):
    """어제·그제 방문을 국내(South Korea)·외국으로."""
    def one(d):
        r = {'국내': 0, '외국': 0}
        for k, v in run(cl, x['pid'], str(d), str(d), ['activeUsers'], ['country'], path=x['path'], skip=x['skip']):
            r['국내' if k[0] == 'South Korea' else '외국'] += v[0]
        return r
    if raw:
        return one(day)
    c, p = one(day), one(day - dt.timedelta(days=1))
    return [f'  · {k}: {c[k]:.0f}명 (전날 {p[k]:.0f}명)' for k in ('국내', '외국')]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--day')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-ai', action='store_true', help='프로젝트별 AI 분석(claude -p) 없이')
    a = ap.parse_args()
    day = dt.date.fromisoformat(a.day) if a.day else dt.date.today() - dt.timedelta(days=1)
    cred = service_account.Credentials.from_service_account_file(str(SA), scopes=['https://www.googleapis.com/auth/analytics.readonly'])
    cl = BetaAnalyticsDataClient(credentials=cred)
    secs, errs = [], []
    for pid, name in properties(cred):
        try:
            for nm, path in [(name, None)] + SPLITS.get(pid, []):
                s = section(cl, pid, nm, day, path, () if path else [q for _, q in SPLITS.get(pid, [])])
                if s:
                    secs.append(s)
        except Exception as e:
            errs.append(f'{name}: {str(e)[:80]}')
    secs.sort(key=lambda s: -s['users'])  # 어제 사용자 많은 순
    live = [x for x in secs if x['users'] >= 1]
    dead = [x['name'] for x in secs if x['users'] < 1]
    real = [x for x in live if not bot(x)]
    try:
        gsc = gsc_by_service(day)
    except Exception as e:
        gsc, errs = {}, errs + [f'서치콘솔: {str(e)[:80]}']
    # 사용자 10/28: 서비스마다 '어디먹 / 웹 - … / 토스앱 - …'처럼 묶는다
    try:
        toss, toss_zero, toss_err = toss_by_service(day)
    except Exception as e:
        toss, toss_zero, toss_err = {}, [], str(e)[:80]
    try:
        sns, sns_err = sns_by_service()
    except Exception as e:
        sns, sns_err = {}, [str(e)[:80]]
    try:
        game = game_by_service(day)
    except Exception as e:
        game = {GAME_SVC: [f'- itch 못 읽음: {str(e)[:60]}', f'- CrazyGames {CRAZY_STATUS}']}
    svc = {}
    for x in real:
        svc.setdefault(short(x['name']), {})['web'] = x
    for k in toss:
        svc.setdefault(k, {})['toss'] = toss[k]
    for k in sns:
        svc.setdefault(k, {})['sns'] = sns[k]
    for k in game:
        svc.setdefault(k, {})['game'] = game[k]
    for k in gsc:
        svc.setdefault(k, {})['gsc'] = gsc[k]['lines']
        svc[k]['gsc_data'] = gsc[k]['data']
    notes = {} if a.no_ai else ai_notes(svc)
    for k, v in list(svc.items()):  # AI가 봇이라고 본 웹은 빼고 목록에 표시
        if 'web' in v and '할 일 없음' in str(notes.get(k, {}).get('할일', '')):
            v.pop('web')['ai_bot'] = True
            notes[k].pop('할일', None)
            if not any(v.get(c) for c in ('gsc', 'toss', 'sns', 'game')):
                svc.pop(k)
    bots = [x for x in live if bot(x) or x.get('ai_bot')]
    total = lambda v: (v['web']['users'] if 'web' in v else 0) + (v['toss'][0] if 'toss' in v else 0)
    # 사용자 11/1 "이거 읽기가 진짜 너무 힘들어": 텔레그램엔 서비스당 세 줄(숫자 한 줄·요약·할 일), 조용한 곳은 한 줄로. 긴 판은 -full 파일
    out, quiet = [f'어제 {day:%m/%d}({"월화수목금토일"[day.weekday()]})'], []
    for name, v in sorted(svc.items(), key=lambda kv: -total(kv[1])):
        n, parts = notes.get(name, {}), []
        if 'web' in v:
            x = v['web']
            t = f'방문 {x["users"]:.0f}명' + (f' (전날 {x["prev"]:.0f}명)' if x['prev'] is not None else '')
            if name in SPLIT_KR and x.get('pid'):
                try:
                    c = kr_split(cl, x, day, raw=True)
                    t += f', 국내 {c["국내"]:.0f}명·외국 {c["외국"]:.0f}명'
                except Exception:
                    pass
            parts.append(t)
        g = gsc.get(name, {}).get('day')
        if g and (g[1][0] or g[2][0]):
            t = f'구글 {g[0]:%m/%d} 노출 {g[1][0]:,.0f} (전날 {g[2][0]:,.0f}), 클릭 {g[1][1]:,.0f}'
            if name in SPLIT_KR:
                t += f', 외국 노출 {g[3]["외국"][0]:,.0f}'
            parts.append(t)
        if 'toss' in v:
            parts.append(f'토스 {v["toss"][0]:.0f}명')
        for l in v.get('sns') or []:
            parts.append(l.lstrip('- ').split(' (')[0])
        if v.get('game'):
            parts.append(v['game'][0].lstrip('- ').split(' (')[0])
        if total(v) < 5 and not (g and g[1][1]) and not any('+' in p and int(re.sub(r'\D', '', p.split('+')[1].split('회')[0]) or 0) >= 100 for p in parts if '+' in p):
            quiet.append(name)
            continue
        # 사용자 11/1 "ㅁㄴㅇㄹ / - ㅁㄴㅇㄹ 이런 식으로 보내라고": 제목 줄 + '- ' 줄, 한 줄에 하나
        out += ['', name] + [f'- {p}' for p in parts]
        if n.get('요약'):
            out.append(f'- {n["요약"]}')
        if n.get('할일'):
            out.append(f'- 할 일: {n["할일"]}')
    if quiet:
        out += ['', '조용한 곳: ' + ', '.join(quiet)]
    full = [f'어제 {day:%m/%d}({"월화수목금토일"[day.weekday()]}) 서비스별 (긴 판)']
    for name, v in sorted(svc.items(), key=lambda kv: -total(kv[1])):
        out_ = full
        out_ += ['', name]
        n = notes.get(name, {})
        if n.get('종합'):  # 사용자 11/1 "서비스마다 종합적인 인사이트 두 줄"
            full += [f'💡 {t}' for t in n['종합'][:2] if t]
        # 사용자 11/1 "서치콘솔 / ga 합쳐서 달라니까": GA 방문과 구글 검색을 '웹' 한 덩어리로
        if 'web' in v or v.get('gsc'):
            full.append('웹')
        if 'web' in v:
            x = v['web']
            prev = f' (전날 {x["prev"]:.0f}명)' if x['prev'] is not None else ''
            full.append(f'- 방문 {x["users"]:.0f}명{prev}')
            if name in SPLIT_KR and x.get('pid'):
                try:
                    full += kr_split(cl, x, day)
                except Exception as e:
                    full.append(f'  · 국내·외국 못 읽음: {str(e)[:40]}')
            if x.get('src'):
                full.append(src_line(x))
        if v.get('gsc'):
            full += v['gsc']
            if n.get('검색'):  # 사용자 11/1 "분석 그대로도 주고"
                full.append(f'- 검색 해석: {n["검색"]}')
        if n.get('할일'):
            full.append(f'- 할 일: {n["할일"]}')
        if 'toss' in v:
            full += ['토스앱'] + v['toss'][1]
        if v.get('game'):
            full += ['포털'] + v['game']
        if v.get('sns'):
            full += ['SNS'] + v['sns']
    zero = []
    if dead:
        zero.append(f'웹 {len(dead)}곳')
    if toss_zero:
        zero.append(f'토스앱 {len(toss_zero)}개')
    if zero:
        out += ['어제 0명: ' + ', '.join(zero)]
    if bots:
        out += ['봇으로 보여 뺀 곳: ' + ', '.join(f'{short(x["name"])} {x["users"]:.0f}명' for x in bots)]
    if toss_err:
        out += ['', f'토스 콘솔 못 읽음: {toss_err}']
    if sns_err:
        out += ['', 'SNS 못 읽은 곳: ' + ', '.join(sns_err)]
    if not a.no_ai and not notes:  # 11/1: 분석이 빠진 걸 사용자가 몰랐다("서치콘솔도 주기로 하지 않음?")
        out += ['', '⚠️ 오늘은 분석(할 일·서치콘솔 해석)이 빠졌어요. AI 사용 한도에 걸려 숫자만 보냈어요.']
    text = '\n'.join(out)
    if errs:
        text += '\n\nGA 못 읽은 곳\n' + '\n'.join(f'- {e}' for e in errs)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{day}.txt').write_text(text + '\n')
    (OUT / f'{day}-full.txt').write_text('\n'.join(full) + '\n')
    (OUT / f'{day}-detail.txt').write_text('\n\n'.join([x['detail'] for x in secs] + [g['detail'] for g in gsc.values()]) + '\n')  # 유입·페이지 상세는 파일로만
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
