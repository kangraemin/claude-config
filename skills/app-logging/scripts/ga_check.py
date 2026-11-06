#!/usr/bin/env python3
"""GA4 속성의 로깅 상태를 한 번에 본다(읽기 전용, 서비스 계정 ai-paper-analytics-sa.json).

사용법:
  python3 ga_check.py                 # 서비스 계정이 볼 수 있는 속성 목록(id, 이름)
  python3 ga_check.py <속성ID|이름일부> [--days 30]

보는 것:
- 스트림(웹·안드로이드 패키지·iOS 번들)
- 맞춤 측정기준(app_platform 등록 여부)
- 이벤트 이름별 건수·사용자 수(실패·오류 이벤트 표시)
- 플랫폼(platform)·호스트(hostName)·app_platform별 사용자 수
- 최근 30분 실시간 이벤트(테스트 배포 직후 확인용)
마지막 줄: RESULT: OK | WARN <빠진 것> | FAIL <이유>
"""
import json, sys, urllib.request
from pathlib import Path
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (RunReportRequest, RunRealtimeReportRequest, DateRange,
                                                 Metric, Dimension, OrderBy)

SA = Path.home() / '.claude/ai-paper-analytics-sa.json'
BAD = ('fail', 'error', 'crash', 'exception', 'timeout', 'reject')


def admin(cred, path):
    cred.refresh(Request())
    req = urllib.request.Request('https://analyticsadmin.googleapis.com/v1beta/' + path,
                                 headers={'Authorization': 'Bearer ' + cred.token})
    return json.load(urllib.request.urlopen(req, timeout=30))


def props(cred):
    r = admin(cred, 'accountSummaries?pageSize=200')
    return [(p['property'].split('/')[1], p['displayName']) for a in r.get('accountSummaries', [])
            for p in a.get('propertySummaries', [])]


def report(cl, pid, days, dims, metrics=('eventCount', 'totalUsers'), limit=200):
    r = cl.run_report(RunReportRequest(property=f'properties/{pid}',
        date_ranges=[DateRange(start_date=f'{days}daysAgo', end_date='today')],
        dimensions=[Dimension(name=d) for d in dims], metrics=[Metric(name=m) for m in metrics],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name=metrics[0]), desc=True)], limit=limit))
    return [([d.value for d in x.dimension_values], [int(float(m.value)) for m in x.metric_values]) for x in r.rows]


def main():
    a = sys.argv[1:]
    days = 30
    if '--days' in a:
        i = a.index('--days'); days = int(a[i + 1]); del a[i:i + 2]
    cred = service_account.Credentials.from_service_account_file(str(SA), scopes=['https://www.googleapis.com/auth/analytics.readonly'])
    ps = props(cred)
    if not a:
        for pid, name in ps:
            print(pid, name)
        print('RESULT: OK', len(ps), '속성')
        return
    q = a[0]
    hit = [p for p in ps if p[0] == q or q.lower() in p[1].lower()]
    if len(hit) != 1:
        print('후보:', hit or '없음')
        print('RESULT: FAIL 속성을 하나로 못 정함(서비스 계정에 뷰어 권한이 없으면 목록에 안 나온다)')
        return
    pid, name = hit[0]
    print(f'# {name} (properties/{pid}), 최근 {days}일')
    warn = []
    st = admin(cred, f'properties/{pid}/dataStreams').get('dataStreams', [])
    print('\n## 스트림')
    for s in st:
        extra = (s.get('webStreamData', {}).get('defaultUri') or s.get('androidAppStreamData', {}).get('packageName')
                 or s.get('iosAppStreamData', {}).get('bundleId') or '')
        print('-', s['type'].replace('_DATA_STREAM', ''), s.get('displayName', ''), extra)
    dims = admin(cred, f'properties/{pid}/customDimensions').get('customDimensions', [])
    print('\n## 맞춤 측정기준', len(dims), '개')
    for d in dims:
        print('-', d['parameterName'], d.get('scope', ''), d.get('displayName', ''))
    if not any(d['parameterName'] == 'app_platform' for d in dims):
        warn.append('app_platform 맞춤 측정기준 없음')
    cl = BetaAnalyticsDataClient(credentials=cred)
    ev = report(cl, pid, days, ['eventName'])
    print('\n## 이벤트', len(ev), '종류 (건수, 사용자)')
    for (n,), (c, u) in ev:
        print('-', n, c, u, '← 실패·오류' if any(b in n.lower() for b in BAD) else '')
    if len(ev) < 10:
        warn.append(f'이벤트 {len(ev)}종류뿐(화면·버튼·실패 이벤트 부족)')
    for dim in ('platform', 'hostName'):
        print(f'\n## {dim}별 사용자')
        for (v,), (c, u) in report(cl, pid, days, [dim], limit=20):
            print('-', v or '(빈 값)', u)
    if any(d['parameterName'] == 'app_platform' for d in dims):
        print('\n## app_platform별 사용자')
        try:
            for (v,), (c, u) in report(cl, pid, days, ['customEvent:app_platform'], limit=10):
                print('-', v, u)
        except Exception as e:
            print('- 조회 실패', str(e)[:100])
    rt = cl.run_realtime_report(RunRealtimeReportRequest(property=f'properties/{pid}',
        dimensions=[Dimension(name='eventName')], metrics=[Metric(name='eventCount')], limit=30))
    print('\n## 최근 30분 실시간')
    for x in rt.rows:
        print('-', x.dimension_values[0].value, x.metric_values[0].value)
    if not rt.rows:
        print('- 없음')
    print('RESULT:', 'WARN ' + ', '.join(warn) if warn else 'OK')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('RESULT: FAIL', str(e)[:200])
