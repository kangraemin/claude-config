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
import statistics
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


CREATED = {}


def properties(cred):
    cred.refresh(Request())
    req = urllib.request.Request('https://analyticsadmin.googleapis.com/v1beta/accountSummaries?pageSize=200',
                                 headers={'Authorization': 'Bearer ' + cred.token})
    r = json.load(urllib.request.urlopen(req, timeout=30))
    for a in r.get('accountSummaries', []):  # 만든 날(새 속성은 일별 집계가 1~2일 늦어 빈 칸 대신 '아직 없음'을 보인다)
        q = urllib.request.Request(f"https://analyticsadmin.googleapis.com/v1beta/properties?filter=parent:{a['account']}&pageSize=200",
                                   headers={'Authorization': 'Bearer ' + cred.token})
        for x in json.load(urllib.request.urlopen(q, timeout=30)).get('properties', []):
            CREATED[x['name'].split('/')[1]] = x.get('createTime', '')[:10]
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


def baseline(vals):
    """'평소' 기준 하나: 앞 7일 하루값의 중앙값. 모든 서비스·모든 날 같은 식(11/6)."""
    v = list(vals)[-7:]
    v += [0] * (7 - len(v))  # GA가 안 준 날은 0명
    return float(statistics.median(v))


def section(cl, pid, name, day, path=None, skip=()):
    y, y2, w = str(day), str(day - dt.timedelta(days=1)), str(day - dt.timedelta(days=6))
    m30 = run(cl, pid, str(day - dt.timedelta(days=29)), y, ['activeUsers'], path=path, skip=skip)
    if not m30:
        # 새 속성은 하루치 집계가 1~2일 늦다(먹맵 10/19 생성 → 실시간 103명인데 일별 0). 실시간이라도 있으면 보낸다.
        if path:
            return None
        rt = cl.run_realtime_report(RunRealtimeReportRequest(property=f'properties/{pid}', metrics=[Metric(name='activeUsers')]))
        now = sum(float(x.metric_values[0].value) for x in rt.rows)
        fresh = CREATED.get(pid, '') >= str(day - dt.timedelta(days=3))
        return {'name': name, 'users': now, 'prev': None, 'engaged': None, 'per': 0, 'new': True,
                'detail': f'{name}\n- 새로 붙인 GA라 일별 집계 아직 없음\n- 지금 30분 실시간 {now:.0f}명', 'data': None} if now or fresh else None
    m = ['activeUsers', 'sessions', 'screenPageViews', 'engagedSessions', 'userEngagementDuration']
    cur = (run(cl, pid, y, y, m, path=path, skip=skip) or [([], [0] * 5)])[0][1]
    prev = (run(cl, pid, y2, y2, m, path=path, skip=skip) or [([], [0] * 5)])[0][1]
    week = (run(cl, pid, w, y, ['activeUsers'], path=path, skip=skip) or [([], [0])])[0][1][0]
    # GA4는 알려진 봇만 자동으로 뺀다. 우리 e2e·모르는 봇은 남는다 → '참여 세션'(10초+ 머묾·2페이지+·전환)을 사람에 가까운 수로 따로 보인다
    per = cur[4] / cur[0] if cur[0] else 0
    lines = [f'📊 {name}',
             f'어제 사용자 {cur[0]:.0f}{delta(cur[0], prev[0])} · 세션 {cur[1]:.0f} · 페이지뷰 {cur[2]:.0f}{delta(cur[2], prev[2])}',
             f'실제로 머문 방문 {cur[3]:.0f}{delta(cur[3], prev[3])}/{cur[1]:.0f}세션 · 1인 평균 {per:.0f}초',
             f'7일 사용자 {week:.0f}', f'30일 사용자 {m30[0][1][0]:.0f}']
    hosts = run(cl, pid, y, y, ['activeUsers'], ['hostName'], 5, 'activeUsers', path=path, skip=skip)
    if len(hosts) > 1:
        lines.append('사이트: ' + ', '.join(f'{d[0]} {v[0]:.0f}' for d, v in hosts))
    src = run(cl, pid, y, y, ['sessions'], ['sessionSource'], 10, 'sessions', path=path, skip=skip)
    if src:
        lines.append('유입: ' + ', '.join(f'{d[0]} {v[0]:.0f}' for d, v in src[:3]))
    pages = run(cl, pid, y, y, ['screenPageViews'], ['pagePath'], 3, 'screenPageViews', path=path, skip=skip)
    if pages:
        lines.append('페이지: ' + ', '.join(f'{d[0][:40]} {v[0]:.0f}' for d, v in pages))
    days = run(cl, pid, str(day - dt.timedelta(days=7)), y, ['activeUsers', 'engagedSessions', 'userEngagementDuration'], ['date'], path=path, skip=skip)
    before = [v[0] for d, v in days if d[0] != day.strftime('%Y%m%d')]
    # 11/6 "기준을 왔다갔다 안 하게": '평소' = 어제 앞 7일의 중앙값(빠진 날은 0). 평균은 자동 접속 하루(꿈해몽 11/4 1,806명)에 337명으로 부풀었다
    ebefore = [v[1] for d, v in days if d[0] != day.strftime('%Y%m%d')]
    avg7 = baseline(before) if days else None
    eavg7 = baseline(ebefore) if days else None
    src7 = run(cl, pid, w, y, ['sessions', 'engagedSessions'], ['sessionSource'], 6, 'sessions', path=path, skip=skip)
    data = {'8일 날짜별 [사용자, 참여세션, 총참여초]': {d[0]: v for d, v in sorted(days)},
            '7일 유입별 [세션, 참여세션]': {d[0]: v for d, v in src7}}
    return {'name': name, 'users': cur[0], 'prev': prev[0], 'm30': m30[0][1][0], 'avg7': avg7, 'eavg7': eavg7, 'engaged': cur[3], 'per': per, 'new': False, 'src': src, 'hosts': [(d[0], v[0]) for d, v in hosts], 'pid': pid, 'path': path, 'skip': skip,
            'detail': '\n'.join(lines), 'data': data}


SNS = HOME / '.cache/sns-stats'
SNS_NAME = {'yt': '유튜브', 'ig': '인스타', 'th': '스레드'}
WHO = {'dev_ram_kang': '개인 계정', 'eodi_sseot': '어디썼', 'eodimeok': '어디먹', 'oguriworks': '오구리웍스', 'geulmagam': '글마감', 'mukmap.kr': '먹맵', 'mukmap_kr': '먹맵', 'ssum.pandok': '썸 판독기', 'eodimeok.kr': '어디먹', 'koubonoshiori': '公募の栞', 'nunsseolmi.kr': '오늘의 눈썰미', 'sharpeyesdaily': '오늘의 눈썰미'}  # 썸 판독기는 웹 칸 이름과 맞춘다(11/1 전엔 '썸판독기'로 따로 놀았다)
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
        old = [x for x in xs if (site, x['id']) in prev]
        new = [x for x in xs if (site, x['id']) not in prev]
        gain = {x['id']: max(0, x['views'] - prev[(site, x['id'])]) for x in old}
        tot, nv = sum(gain.values()), sum(x['views'] for x in new)
        if tot <= 0 and not nv:
            continue
        line = f'- {SNS_NAME[site]} ' + ', '.join(([f'조회 +{tot:,}회'] if tot else []) + ([f'새 글 {len(new)}개 조회 {nv:,}회'] if new else []))
        gain.update({x['id']: x['views'] for x in new})
        tot += nv
        best = max(xs, key=lambda x: gain[x['id']])
        if gain[best['id']] >= SNS_MIN:
            title = best['title'].replace('#shorts', '').split('\n')[0].strip()
            t18 = title[:18] + "…" if len(title) > 18 else title
            line += f' 「{t18}」' if gain[best['id']] == tot else f' (제일 많이 본 글 「{t18}」 +{gain[best["id"]]:,}회)'  # 글 하나가 전부면 숫자를 두 번 안 쓴다
        out.setdefault(WHO.get(handle, handle), []).append((tot, line))
    return {k: [t for _, t in sorted(v, key=lambda u: -u[0])] for k, v in out.items()}, errs


def sns_span():
    """SNS 수집 두 번의 시각('10/31 12시~11/01 09시'). 수집 간격이 일정하지 않아 '어제'가 아니다."""
    files = sorted(SNS.glob('*.json'))
    if len(files) < 2:
        return ''
    at = lambda f: dt.datetime.fromtimestamp(f.stat().st_mtime)
    prev = SNS / f'{dt.date.fromisoformat(files[-1].stem) - dt.timedelta(days=1)}.json'
    return f'{at(prev):%m/%d %H}시~{at(files[-1]):%m/%d %H}시' if prev.exists() else ''


TOSS = Path.home() / '.cache/toss-stats'  # my-sns eodi-sns/scripts/toss_stats.py 가 6시간마다 쓴다


TOSS_M30 = {}  # 앱 이름 → 토스앱 최근 30일 방문(하루 방문자 합). 어제 0명인 앱 목록에도 붙인다


def toss_by_service(day):
    """앱인토스 콘솔 숫자(사용자 10/28 "토스에서 나온 지표들도 ga 분석기에 합쳐"). ({앱: (사용자, [줄])}, 0명 앱, 오류)."""
    files = sorted(TOSS.glob('*.json'))
    if not files:
        return {}, [], None
    cur = json.loads(files[-1].read_text())
    if cur.get('error'):
        return {}, [], cur['error']
    d, p = str(day), str(day - dt.timedelta(days=1))
    # 11/5: 수집이 10/31에 멈췄는데 16개 앱이 전부 '0명'으로 나왔다. 그날을 안 담은 파일은 0명이 아니라 '못 읽음'이다
    if cur.get('to') and cur['to'] < d:
        return {}, [], f'{cur["to"][5:].replace("-", "/")} 뒤로 수집이 멈춤'
    rows, zero = {}, []
    for x in cur['apps']:
        if x.get('error'):
            rows[x['name']] = (0, ['- 못 읽음'])
            continue
        u, pu, n = x['au'].get(d, 0), x['au'].get(p, 0), x['new'].get(d, 0)
        d30 = [str(day - dt.timedelta(days=k)) for k in range(30)]
        if (cur.get('from') or d) <= d30[-1]:  # 30일을 다 담은 파일일 때만(11/6 이전 파일은 9일치뿐)
            x['m30'] = sum(x['au'].get(k, 0) for k in d30)
            TOSS_M30[short(x['name'])] = x['m30']
        if not u:
            zero.append(x['name'])
            continue
        lines = [f'- {u}명 (신규 {n}, 전날 {pu}명)']
        ref = sorted((x.get('referrer_by_day') or {}).get(d, {}).items(), key=lambda kv: -kv[1])[:3]
        if ref:
            lines.append('- ' + ' · '.join(f'{k} {v}' for k, v in ref))
        rows[x['name']] = (u, lines, x.get('m30'))
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


AI_PROMPT = """아래는 서비스별 어제 숫자다(웹 GA4 방문·유입·페이지, 구글 서치콘솔 날짜별·검색어·페이지, 토스앱, SNS 조회). 서비스마다 두 가지를 써라.

- "할일": 오늘 해 볼 일 한 문장, 30자 안팎, '~하기'로 끝낸다. 자료에 나온 실제 페이지 주소·검색어·글 제목 하나를 꼭 넣는다.
  무엇을 어떻게 바꾸는지까지 쓴다(예: 제목에 '13년생 띠' 넣기). '글 하나 더 올리기', '제목 손보기', '링크 달기'처럼 어느 서비스에나 맞는 말은 안 된다.
  페이지는 주소 대신 쉬운 말로(예: '소설 공모전 모음 페이지'). 하루 숫자가 10 밑인 것으로는 할 일을 만들지 않는다. '어제' 대신 날짜를 쓴다. SNS 조회 증가는 하루치가 아니라 두 번 잰 사이의 증가라 '○월 ○일 조회'라고 쓰지 않는다. 근거를 댈 수 없으면 빈 문자열.
- "근거": 그 할 일을 고른 이유 한 문장, 자료에 있는 숫자 하나 이상, 주소 대신 쉬운 말로(예: '소설 공모전 모음 페이지가 구글에 120회 보였는데 눌린 건 0회').

규칙
- 쉬운 한국어. 영어·전문용어(CTR, 임프레션 등) 금지. 지어낸 숫자 금지.
- 웹 유입이 (direct)·(not set)뿐이고 머문 방문이 거의 없으면 "할일"은 빈 문자열.
- 출력은 JSON 하나만: {"<서비스 이름 그대로>": {"할일": "…", "근거": "…"}}. 다른 말 금지.

자료:
"""


# 구글 서치콘솔(사용자 10/31 "ga 리포트줄때도 구글서치콘솔도 참고해서분석해서줘"). 같은 서비스 계정이 사이트 소유자다.
# 사이트 → 서비스 이름(short() 결과와 같게). 블로그는 하위 경로 사이트를 빼고 센다.
GSC = {'https://kangraemin.github.io/oneul-kkum/': '꿈해몽', 'https://kangraemin.github.io/jeju-stay/': '제주 숙소',
       'https://kangraemin.github.io/': '개발 블로그', 'https://geulmagam.vercel.app/': '글마감', 'https://xn--ob0butqet42c6pmgpe.kr/': '글마감',
       'https://eodimeok.kr/': '어디먹', 'https://mukmap.kr/': '먹맵', 'https://xn--zf0b677a.kr/': '상권.kr',
       'https://ssum-pandok.remin1994.workers.dev/': '썸 판독기', 'https://oguriworks.com/': '오구리웍스',
       'https://eodisseot.pages.dev/': '어디썼', 'https://eodisseot.vercel.app/': '어디썼', 'sc-domain:paper-digest.app': 'AI 논문 요약',
       'https://koubonoshiori.com/': '公募の栞', 'https://threads-unfollow.pages.dev/': '스레드언팔확인',
       'https://kangraemin.github.io/bid-window-404/': '입찰 창구 404호', 'https://kangraemin.github.io/forge-survivor-play/': '강화 서바이버',
       'https://gooreum.github.io/ttuk-chiro-clinic/': '뚝 카이로 클리닉', 'https://tax-watcher.remin1994.workers.dev/': '법카로 본 서울'}  # 11/1 일본판·언팔확인 빠져 있던 것
GSC_SKIP = {'https://kangraemin.github.io/': ['/oneul-kkum/', '/jeju-stay/', '/bid-window-404/', '/forge-survivor-play/']}


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
        a = acc.setdefault(svc, {'sites': [], 'last': last, 'cur': [0, 0, 0], 'prev': [0, 0], 'q': {}, 'p': {}, 'day': {}, 'cty': {}})
        a['last'] = max(a['last'], last)
        a['sites'].append(site)
        a.setdefault('fresh', {})
        for r in s.post(url, json={'startDate': str(day - dt.timedelta(days=16)), 'endDate': str(day), 'dimensions': ['date'], 'dataState': 'all', 'dimensionFilterGroups': flt}).json().get('rows', []):
            a['fresh'][r['keys'][0]] = a['fresh'].get(r['keys'][0], 0) + r['impressions']
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
        out[svc] = {'lines': lines, 'detail': '\n'.join(det), 'fresh': a.get('fresh', {}), 'sites': a['sites'], 'day': (a['last'], dc, dp, {k: a['cty'].get(L, {}).get(k, [0, 0]) for k in ('국내', '외국')}),
                    'data': {'날짜별 [노출, 클릭]': {k: v[:2] for k, v in sorted(a['day'].items())}, '구글 검색 7일 [노출, 클릭, 평균순위]': [imp, clk, round(pos / imp, 1) if imp else None], '그 앞 7일 [노출, 클릭]': a['prev'],
                             '검색어 [노출, 클릭, 평균순위]': {k: [v[0], v[1], round(v[2] / v[0], 1)] for k, v in top(a['q'], 10) if v[0]},
                             '페이지 [노출, 클릭]': {k: v[:2] for k, v in top(a['p'], 8)}}}
    return out


COVER = [('Crawled', '구글이 읽어 갔지만 색인 안 함'), ('Discovered', '구글이 알지만 아직 안 읽어 감'), ('noindex', 'noindex 표시 있음'), ('Duplicate', '다른 주소와 중복으로 봄'),
         ('canonical', '다른 주소와 중복으로 봄'), ('404', '없는 페이지(404)'), ('Server error', '서버 오류'), ('robots', 'robots.txt가 막음'), ('redirect', '다른 주소로 넘어감')]


def why_drop(sites, start, end):
    """노출이 많던 페이지 5개가 지금 구글 색인에 있는지(URL 검사 API). '5개 중 4개 색인에서 빠짐' 같은 한 줄."""
    from google.auth.transport.requests import AuthorizedSession
    s = AuthorizedSession(service_account.Credentials.from_service_account_file(str(SA), scopes=['https://www.googleapis.com/auth/webmasters']))
    pages = []
    for site in sites:
        url = f'https://www.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(site, safe="")}/searchAnalytics/query'
        pages += [(r['impressions'], r['keys'][0], site) for r in s.post(url, json={'startDate': str(start), 'endDate': str(end), 'dimensions': ['page'], 'rowLimit': 5}).json().get('rows', [])]
    out, raw = [], []
    top = sorted(pages, reverse=True)[:5]
    for _, u, site in top:
        r = s.post('https://searchconsole.googleapis.com/v1/urlInspection/index:inspect', json={'inspectionUrl': u, 'siteUrl': site}).json()
        ix = r.get('inspectionResult', {}).get('indexStatusResult', {})
        if ix.get('verdict') != 'PASS':
            pu = urllib.parse.urlparse(u)
            st = ix.get('coverageState', '')
            why = next((k for c, k in COVER if c in st), '색인 안 됨')
            out.append(f'{pu.netloc.encode().decode("idna")}{urllib.parse.unquote(pu.path)} ({why})')
            raw.append((site, u))
    return (len(top), out, raw)


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


HOST = {'kangraemin.github.io': '깃허브 웹판', 'kangraemin.itch.io': 'itch.io'}


def host_name(h):
    """주소 대신 사람 말로(11/1 "eodimeok.apps.tossmini.com 이런건뭐여"). 토스 미니앱 주소는 토스 앱 안에서 연 것."""
    if h.endswith('.private-apps.tossmini.com'):
        return '토스 테스트판'
    if h.endswith('.apps.tossmini.com'):
        return '토스 앱 안'
    return HOST.get(h, '웹사이트')


# 토스 콘솔에 있지만 아직 출시 안 된 앱(11/7 기준). 출시되면 toss_stats.py APPS로 옮긴다.
TOSS_PREPARE = {'나사톡톡', '골골냥', '소라고동님', '뚝 카이로 클리닉', '썸 판독기', '오늘의 눈썰미', '강화 서바이버'}


def short(name):
    """'제주 숙소 (jeju-stay)'·'Ram's tech blog - GA4' 같은 꼬리를 뗀다."""
    n = re.sub(r'\s*(\([^)]*\)|- GA4)$', '', name) or name
    n = re.sub(r'(?<=[가-힣])\s+[A-Za-z][\w-]*$', '', n)
    return {'MukMap': '먹맵', "Ram's tech blog": '개발 블로그', '오늘꿈해몽': '꿈해몽', 'forge-survivor-app': '강화 서바이버 스토어 앱', 'claude inspector': '클로드 인스펙터', 'screwtoktok-app': '나사톡톡 스토어 앱', 'ai-paper': 'AI 논문 요약'}.get(n, n)


def channel(src):
    """GA sessionSource → 사람이 바로 알아듣는 길 이름. 모르는 사이트는 '다른 사이트'."""
    x = src.lower()
    for keys, name in [(('(direct)',), '직접 접속'), (('(not set)',), '출처 모름'),
                       (('chatgpt', 'openai'), 'ChatGPT'), (('perplexity',), '퍼플렉시티'), (('claude.ai',), '클로드'), (('gemini',), '제미나이'), (('copilot',), '코파일럿'),  # 11/5 "AI 답변 어딘진 모름?": 묶지 않는다
                       
                       (('kin.naver',), '지식iN'), (('cafe.naver', 'blog.naver'), '네이버 카페·블로그'),
                       (('naver',), '네이버 검색'), (('google',), '구글 검색'), (('bing', 'daum', 'duckduckgo'), '다른 검색'),
                       (('threads',), '스레드'), (('instagram',), '인스타'), (('youtube',), '유튜브'), (('t.co', 'x.com', 'twitter'), 'X'),
                       (('kangraemin.github.io',), '개발 블로그'), (('toss',), '토스')]:
        if any(k in x for k in keys):
            return name
    return '다른 사이트'


def src_parts(x):
    """사용자 10/26 "어느 채널에서 들어왔는지도 서비스별로" + "정성스럽게" → 길별로 묶어 비중(방문 10번 이상) 또는 횟수로."""
    tot = sum(v[0] for _, v in x['src'])
    by = {}
    for d, v in x['src']:
        by[channel(d[0])] = by.get(channel(d[0]), 0) + v[0]
    top = sorted(by.items(), key=lambda kv: -kv[1])[:3]
    if tot >= 10:
        return [f'{k} {v / tot:.0%}' for k, v in top]
    return [f'{k} {v:.0f}번' for k, v in top]


def src_line(x):
    return '- ' + ' · '.join(src_parts(x))


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


def check(text):
    """보내기 전 점검(사용자 11/1 "납품받는다 생각하면"). 걸린 것 목록을 돌려준다."""
    bad, L = [], text.split('\n')
    titles = [l for i, l in enumerate(L) if l and not l.startswith('- ') and i and not L[i - 1].strip()]
    SUBS = {'웹', '토스', '유입', '노출'}
    dup = {t for t in titles if titles.count(t) > 1 and t not in SUBS}
    if dup:
        bad.append('같은 칸이 두 번: ' + ', '.join(dup))
    for i, l in enumerate(L):  # 사용자 11/1 형식: '제목' + '- 짧은 줄'만
        if not l.strip():
            continue
        if l.startswith('- '):
            if len(re.sub(r'\S+\.(kr|com|app|io|dev)/\S*', 'URL', l)) > 60:
                bad.append('너무 긴 줄: ' + l[:30])
            if ', ' in l and l.count(', ') >= 2:
                bad.append('나열 줄: ' + l[:30])
        elif l.startswith('[') and l.endswith(']'):
            continue  # 서비스 머리줄(사용자 11/7 웹·토스·유입·노출 네 칸)
        elif i and L[i - 1].strip():
            bad.append('- 없는 줄: ' + l[:30])
        elif len(l) > 20:
            bad.append('제목이 김: ' + l[:30])
    for l in L:
        if l.startswith(('- 구글 노출', '- 구글 클릭')) and not re.search(r'\d\d/\d\d', l):
            bad.append('날짜 없는 구글 줄: ' + l)
        if re.search(r'사용자 \d|\+\d[\d,]*회$', l) and '조회' not in l and '조회' not in l:
            bad.append('뜻이 애매한 줄: ' + l)
    if '나빠진 것' not in text:
        bad.append('맨 위 나빠진 것 없음')
    if len(text) > 12000:  # send()가 칸 단위로 나눠 보내므로 2통까지 허용(11/4 유입 줄 추가)
        bad.append(f'너무 김 {len(text)}자')
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--day')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--force', action='store_true', help='오늘 이미 보냈어도 다시 보낸다')
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
    bots_first = [x for x in live if bot(x)]
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
    # 11/6 "기준을 왔다갔다 안 하게": 자동 접속이 몰린 날도 다른 날과 같은 줄(웹 방문·실제로 머문 방문)로 보이고, 안내 한 줄만 더한다
    for x in live:
        x['botday'] = bot(x)
        svc.setdefault(short(x['name']), {})['web'] = x
    # 사용자 11/7 "왤케 포맷이 다 달라": 0명인 곳도 따로 이름 목록에 빼지 않고 같은 칸·같은 줄로 보인다
    for x in secs:
        if x['users'] < 1:
            x['botday'] = False
            svc.setdefault(short(x['name']), {}).setdefault('web', x)
    for k in toss:
        svc.setdefault(k, {})['toss'] = toss[k]
    for k in toss_zero:
        svc.setdefault(k, {})['toss'] = (0, [], TOSS_M30.get(short(k)))
    for k in sns:
        svc.setdefault(k, {})['sns'] = sns[k]
    for k in game:
        svc.setdefault(k, {})['game'] = game[k]
    for k in gsc:
        svc.setdefault(k, {})['gsc'] = gsc[k]['lines']
        svc[k]['gsc_data'] = gsc[k]['data']
    notes = {} if a.no_ai else ai_notes(svc)
    # 11/1 AI가 사람 29명(머문 방문 13)을 봇이라 했다 → 봇 판정은 규칙(bot())만. AI 말은 할 일에만 쓴다
    bots = [x for x in live if bot(x)]
    total = lambda v: (v['web']['users'] if 'web' in v else 0) + (v['botweb']['engaged'] if 'botweb' in v else 0) + (v['toss'][0] if 'toss' in v else 0)
    wd = lambda d: f'{d:%m/%d}({"월화수목금토일"[d.weekday()]})'
    # 사용자 11/1 "납품받는다 생각하면": 맨 위에 '오늘 볼 것'(규칙으로 계산, AI 아님) — 나쁜 일·좋은 일을 나누고 할 일을 붙인다
    bad_n, good_n, dropped, week_up, reidx, lost, reraw, g_span = [], [], [], {}, [], [], [], ''
    for name, gg in gsc.items():
        f = gg.get('fresh') or {}
        last = gg['day'][0]  # 구글이 확정한 마지막 날. 그 뒤(아직 확정 전) 숫자는 판정에 안 쓴다
        ds = [str(last - dt.timedelta(days=k)) for k in range(9)]
        last2, base = [f.get(d, 0) for d in ds[:2]], [f.get(d, 0) for d in ds[2:9]]
        b, l = sum(base) / 7, sum(last2) / 2
        if b >= 20 and l < b * 0.3:
            try:
                why = why_drop(gg['sites'], last - dt.timedelta(days=8), last - dt.timedelta(days=2))
            except Exception:
                why = None
            t = f'- {name} 구글 노출 하루 {b:,.0f}회 → {last2[0]:,.0f}회'
            g_span = f'{last - dt.timedelta(days=8):%m/%d}~{last - dt.timedelta(days=2):%m/%d} 평균 → {last:%m/%d}'
            if why and why[1]:
                lost.append(f'{name} {why[0]}개 중 {len(why[1])}개')
                reidx.extend(why[1])
                reraw.extend(why[2])
            bad_n.append((1e9 + sum(base), t))
            dropped.append(name)
        else:  # 확정된 마지막 7일 합이 그 앞 7일의 3배 넘으면 좋은 소식
            ds14 = [str(last - dt.timedelta(days=k)) for k in range(14)]
            w1, w2 = sum(f.get(d, 0) for d in ds14[:7]), sum(f.get(d, 0) for d in ds14[7:])
            if w1 >= 300 and w1 >= w2 * 3:
                ck = gg['day'][1][1] if gg.get('day') else 0
                # 11/1 검사: 눌린 게 적으면 '좋아진 것'이 아니다 → 그 서비스 칸에만 적는다
                c7 = sum(v[1] for d, v in gg.get('data', {}).get('날짜별 [노출, 클릭]', {}).items() if d in ds14[:7])
                week_up[name] = [f'구글 노출 {last - dt.timedelta(days=6):%m/%d}~{last:%m/%d} {w1:,.0f}회 (그 앞 7일 {w2:,.0f}회)', f'구글 클릭 {last - dt.timedelta(days=6):%m/%d}~{last:%m/%d} {c7:,.0f}회']
    for x in live:  # 실제로 머문 방문이 평소(앞 7일 중앙값)의 1.5배 이상이거나 절반 이하인 곳(10회 이상만)
        # 11/6 "기준은 그대로라는거?": 자동 접속이 섞인 사용자 수 대신 실제로 머문 방문으로 좋아짐·나빠짐을 판단한다
        av, ev, ea = x.get('avg7'), x.get('engaged'), x.get('eavg7')
        if av is None or ev is None or ea is None or max(ev, ea) < 10:
            continue
        by = {}
        for d, v in x.get('src') or []:
            by[channel(d[0])] = by.get(channel(d[0]), 0) + v[0]
        top = max(by.items(), key=lambda kv: kv[1])[0] if by else ''
        t = f'- {short(x["name"])} 실제로 머문 방문 {ev:.0f}회 (평소 {ea:.0f}회)'
        if ev >= ea * 1.5:
            good_n.append((ev - ea, t))
        elif ev <= ea * 0.5:
            bad_n.append((ea - ev, t))
    span_s = sns_span() + ' 사이' if sns_span() else ''
    for name, v in svc.items():  # SNS 조회가 한 계정에서 1,000회 넘게 늘면 좋은 소식
        for l in v.get('sns') or []:
            m = re.match(r'- (\S+) (?:조회 \+([\d,]+)회)?', l)
            if m and m.group(2) and int(m.group(2).replace(',', '')) >= 1000:
                good_n.append((int(m.group(2).replace(',', '')), f'- {short(name)} ' + l[2:].split(' (')[0].split(' 「')[0]))
    # 사용자 11/1 "내가 두번다시 이야기안한다": 모든 칸은 '제목' + '- 짧은 줄'. 괄호 설명·들여쓴 목록·'이름: a, b' 줄 금지
    other, shown, quiet, todo = [], set(), [], []
    out = [f'{wd(day)} 방문 리포트']
    out += ['', '나빠진 것'] + ([t for _, t in sorted(bad_n, key=lambda u: -u[0])][:4] or ['- 없음'])
    if dropped:
        out.append(f'- 기준: {g_span}')
    if lost:
        out.append('- 원인: 많이 보이던 페이지가 구글 색인에서 빠짐')
        out += [f'- {x}' for x in lost]
    if len(dropped) >= 2:
        todo.append(f'- {len(dropped)}곳 같은 때 줄어듦 → 그 무렵 배포·설정 바꾼 것 확인')
    if reraw:  # 사용자 11/1 "색인요청 다 적을려고?": 사람에게 시키지 않는다 → 08:20 홍보 작업(daily_growth_run.sh)이 gsc_request_index.py로 요청
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f'{day}-reindex.json').write_text(json.dumps(reraw, ensure_ascii=False))
        todo.append(f'- 빠진 페이지 {len(reraw)}개는 08:20에 자동으로 색인 요청')
        if {re.search(r' \((.+)\)$', u).group(1) for u in reidx if re.search(r' \((.+)\)$', u)} == {'구글이 읽어 갔지만 색인 안 함'}:
            todo.append('- 읽고도 뺀 페이지라 얇거나 겹치는지 각 앱에서 보기')
    bot_names = {short(x['name']) for x in bots}
    dead_names = {short(n) for n in dead}
    good_n_txt = [t for _, t in sorted(good_n, key=lambda u: -u[0])][:3]
    body, allzero = [], []
    for name, v in sorted(svc.items(), key=lambda kv: -total(kv[1])):
        n = notes.get(name, {})
        # 사용자 11/7 "웹 / 토스 / 유입 / 노출 이렇게 보내도록해": 모든 서비스가 같은 네 칸. 없는 칸은 '- 없음'
        web_l, toss_l, src_l, exp_l = [], [], [], []
        wx = v.get('web') or v.get('botweb')
        if wx:
            av = wx.get('avg7')
            web_l.append(f'어제 {wx["users"]:,.0f}명' + (f' (평소 {av:.0f}명)' if av is not None else ''))
            web_l.append(f'최근 30일 {wx["m30"]:,.0f}명' if wx.get('m30') is not None else '최근 30일 집계 전')
            if wx.get('engaged') is not None:
                ea = wx.get('eavg7')
                web_l.append(f'실제로 머문 방문 {wx["engaged"]:.0f}회' + (f' (평소 {ea:.0f}회)' if ea is not None else ''))
            if wx.get('botday') or 'botweb' in v:
                web_l.append('자동 접속이 섞여 머문 방문으로 봄')
        if 'web' in v:
            x = v['web']
            hs = [(h, u) for h, u in x.get('hosts') or [] if h and h != '(not set)']
            if len(hs) > 1 or (hs and GAME_SVC in name):  # 사용자 11/1 "itch인지 뭐 다른데인지 이야기를 해줘야"
                web_l += [f'{host_name(h)} {u:.0f}명' for h, u in hs]
            if name in SPLIT_KR and x.get('pid'):
                try:
                    c = kr_split(cl, x, day, raw=True)
                    web_l.append(f'국내 {c["국내"]:.0f}명, 외국 {c["외국"]:.0f}명')
                except Exception:
                    pass
            src_l += src_parts(x) if x.get('src') else []
        if 'botweb' in v:
            x = v['botweb']
            by = {}
            for d_, v_ in x.get('src') or []:
                if channel(d_[0]) not in ('직접 접속', '출처 모름'):
                    by[channel(d_[0])] = by.get(channel(d_[0]), 0) + v_[0]
            src_l += [f'{k} {u:.0f}번' for k, u in sorted(by.items(), key=lambda kv: -kv[1])[:3]]
        if 'toss' in v:
            toss_l.append(f'어제 {v["toss"][0]:,.0f}명')
            t30 = v['toss'][2] if len(v['toss']) > 2 else None
            toss_l.append(f'최근 30일 {t30:,.0f}명' if t30 is not None else '최근 30일 확인 안 됨')
        elif short(name) in TOSS_PREPARE:
            toss_l.append('출시 전')
        g = gsc.get(name, {}).get('day')
        if name in week_up:
            exp_l += week_up[name]
        elif g and max(g[1][0], g[2][0]) >= 10 and name not in dropped:  # 줄어든 곳은 맨 위에 있다
            exp_l.append(f'구글 노출 {g[1][0]:,.0f}회, 클릭 {g[1][1]:,.0f}회 ({g[0]:%m/%d})')
        for l in v.get('sns') or []:
            if max([int(m.replace(',', '')) for m in re.findall(r'([\d,]+)회', l.split(' (')[0])] or [0]) < 10:  # 한 자릿수 증감은 뺀다
                continue
            main_, best = l[2:].split(' (제일 많이 본 글 ')[0], ''
            if ' (제일 많이 본 글 ' in l:
                t_, n_ = l.split(' (제일 많이 본 글 ')[1].rstrip(')').rsplit(' ', 1)
                best = f'많이 본 글 {t_} 조회 {n_}'
            exp_l += [main_] + ([best] if best else [])
        for gl in v.get('game') or []:  # 게임은 어느 포털 숫자인지 다 적는다
            g0 = gl.lstrip('- ').split(' (')[0]
            if '못 읽음' not in g0:
                exp_l.append(g0)
        shown.add(short(name))
        # 사용자 11/7 "전부 0인건 묶어": 웹·토스 어제·30일이 다 0이고 유입·노출도 없으면 한 칸에 이름만
        w0 = not wx or (wx['users'] < 1 and not wx.get('m30'))
        t0 = 'toss' not in v or (v['toss'][0] < 1 and not (v['toss'][2] if len(v['toss']) > 2 else 0))
        if w0 and t0 and not src_l and not exp_l:
            allzero.append(short(name) + (' (토스 출시 전)' if short(name) in TOSS_PREPARE else ''))
            continue
        body += ['', f'[{short(name)}]']
        for sub, ls in (('웹', web_l), ('토스', toss_l), ('유입', src_l), ('노출', exp_l)):
            body += ['', sub] + [f'- {p}' for p in (ls or ['없음'])]
        eng = re.sub(r'(https?://|/)\S+|[\w.-]+\.(kr|com|app|io|dev)\S*', '', n.get('할일', ''))
        if name in dropped and re.search(r'검색|구글|순위', n.get('근거', '') + n.get('할일', '')):
            n = {}  # 구글 색인에서 빠진 곳은 다시 올리기가 먼저
        if n.get('할일') and re.search(r'\d', n.get('근거', '')) and not re.search(r'[A-Za-z]{3,}', eng):
            todo.append(f'- {short(name)}: {n["할일"]}')
    out += ['', '오늘 할 일'] + (todo or ['- 없음'])
    out += ['', '좋아진 것'] + (good_n_txt or ['- 없음'])
    out += body
    if allzero:
        out += ['', '전부 0인 곳'] + [f'- {z}' for z in allzero]
    zero = sorted(dead_names - shown - bot_names)
    note = []
    if bots:
        note += [f'- 봇이라 뺌: {short(x["name"])} {x["users"]:.0f}명' for x in bots if short(x['name']) not in shown]
    span = sns_span()
    if span:
        note.append(f'- SNS 조회는 {span} 사이 증가')
    note.append('- 웹 30일은 GA 순 방문자, 토스 30일은 하루 방문자를 더한 값')
    if gsc:
        note.append('- 검색 숫자는 이틀 늦게 확정돼 그 날짜로 적음')
    if toss_err:
        note.append(f'- 토스 숫자 못 읽음: {toss_err}')
    if sns_err:
        note.append(f'- SNS 못 읽은 곳 {len(sns_err)}개')
    if not a.no_ai and not notes:
        note.append('- 할 일 분석 빠짐(AI 실패)')
    if errs:
        note.append(f'- GA 못 읽은 곳 {len(errs)}개')
    out += ['', '참고'] + note if note else []
    lowlist = {'웹 1~4명': quiet, '웹 0명': zero, 'SNS·토스앱만': other, '토스앱 0명': [short(t) for t in toss_zero]}
    full = [f'방문 리포트 {wd(day)} (긴 판)']
    for name, v in sorted(svc.items(), key=lambda kv: -total(kv[1])):
        n = notes.get(name, {})
        full += ['', name]
        if 'web' in v:
            x = v['web']
            full.append(f'- 웹 방문자 {x["users"]:.0f}명' + (f' (전날 {x["prev"]:.0f}명)' if x.get('prev') is not None else ''))
            if x.get('src'):
                full.append(src_line(x))
        full += v.get('gsc') or []
        if 'toss' in v:
            full += v['toss'][1]
        full += v.get('game') or []
        full += v.get('sns') or []
        if n.get('할일'):
            full.append(f'- 할 일: {n["할일"]} (근거: {n.get("근거", "")})')
    full += ['', '거의 안 들어온 곳'] + [f'- {k}: {", ".join(v)}' for k, v in lowlist.items() if v] + [f'- GA 오류 {e}' for e in errs]
    text = '\n'.join(out)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{day}.txt').write_text(text + '\n')
    (OUT / f'{day}-full.txt').write_text('\n'.join(full) + '\n')
    (OUT / f'{day}-detail.txt').write_text('\n\n'.join([x['detail'] for x in secs] + [g['detail'] for g in gsc.values()]) + '\n')  # 유입·페이지 상세는 파일로만
    print(text)
    bad = check(text)
    if bad:
        print('점검 걸림: ' + ' / '.join(bad))
    if not a.dry_run:
        sent = OUT / f'{day}.sent'
        if sent.exists() and not a.force:  # 11/1 같은 날 다섯 번 넘게 보냈다 → 하루 한 번, 다시 보내려면 --force
            print(f'RESULT: SKIP 이미 보냄 {sent.read_text().strip()}')
            return
        if bad:  # 점검에 걸린 판은 보내지 않고 걸린 이유만 알린다
            send(f'방문 리포트 {day:%m/%d}: 보내기 전 점검에 걸려 안 보냈어요\n' + '\n'.join(f'- {x}' for x in bad))
            print('RESULT: FAIL 점검')
            sys.exit(1)
        send(text)
        sent.write_text(dt.datetime.now().strftime('%m/%d %H:%M'))
    print(f'RESULT: OK {len(secs)}')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'RESULT: FAIL {e}')
        sys.exit(1)
