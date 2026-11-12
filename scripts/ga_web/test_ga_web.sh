#!/bin/bash
# GA 리포트 웹 검사: 파서·빌드·배포 주소·갱신 API
set -e
O=$(mktemp -d)
python3 ~/.claude/scripts/ga_web/build.py --out "$O" | grep -q 'RESULT: OK days='
grep -q '지금 숫자로 갱신' "$O/index.html"
python3 - <<'P'
import sys; sys.path.insert(0, '/Users/ram/.claude/scripts/ga_web'); import build
d = build.parse("11/09(월) 방문 리포트\n\n나빠진 것\n- 없음\n\n[글마감]\n\n웹\n- 어제 120명 (평소 100명)\n- 최근 30일 3,000명\n- 실제로 머문 방문 80회 (평소 70회)\n\n토스\n- 어제 5명\n\n전부 0인 곳\n- 상권.kr\n")
assert d['svcs'][0]['name'] == '글마감', d
s = build.summary(d['svcs'][0])
assert s == {'web': 120, 'web_usual': 100, 'web30': 3000, 'eng': 80, 'eng_usual': 70, 'toss': 5}, s
assert d['tail'][0]['t'] == '전부 0인 곳'
P
# 0시~아침판 전 갱신(live.json에 day)이면 어제 칸을 두 번 만들지 않는다(사용자 11/13 "어제 ga통계 저거 맞아?")
python3 - <<'P'
import sys, json, tempfile, pathlib; sys.path.insert(0, '/Users/ram/.claude/scripts/ga_web'); import build
t = pathlib.Path(tempfile.mkdtemp()); body = "11/12(목) 방문 리포트\n\n[글마감]\n\n웹\n- 어제 59명 (평소 91명)\n"
(t / '2026-11-11.txt').write_text(body.replace('11/12(목)', '11/11(수)')); (t / '2026-11-12.txt').write_text(body); (t / 'live.txt').write_text(body)
(t / 'live.json').write_text(json.dumps({'at': 1794515829601, 'day': '2026-11-12'})); build.SRC = t
days, live = build.load()
assert [x['key'] for x in days] == ['2026-11-12', '2026-11-11'], days
assert live == {'at': 1794515829601, 'merged': True}, live
assert '확정 전' not in days[0]['range'], days[0]['range']  # 끝난 하루는 확정된 날로 보인다
P
K=$(grep '^PRIVATE_WEB_KEY=' ~/.claude/.env | cut -d= -f2); U=https://ga-report.remin1994.workers.dev
test "$(curl -s -m 20 -o /dev/null -w '%{http_code}' $U/)" = 404          # 키 없으면 못 봄
test "$(curl -s -m 20 -o /dev/null -w '%{http_code}' $U/api/state)" = 404
test "$(curl -s -m 20 -o /dev/null -w '%{http_code}' -H "cookie: pk=$K" $U/)" = 200
curl -s -m 20 -H "cookie: pk=$K" $U/api/state | grep -q '"req"'
curl -s -m 20 -H "cookie: pk=$K" $U/live.json | grep -q '"at"'
curl -s -m 20 -H "cookie: pk=$K" $U/ | grep -q 'data-m="30"'
test "$(curl -s -m 20 -o /dev/null -w '%{http_code}' https://sns-calendar.remin1994.workers.dev/)" = 404
test "$(curl -s -m 20 -o /dev/null -w '%{http_code}' -H "cookie: pk=$K" https://sns-calendar.remin1994.workers.dev/)" = 200
python3 -c "import ast;ast.parse(open('/Users/ram/.claude/scripts/ga_daily_report.py').read())"
echo PASS
