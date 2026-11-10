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
K=$(grep '^PRIVATE_WEB_KEY=' ~/.claude/.env | cut -d= -f2); U=https://ga-report.remin1994.workers.dev
test "$(curl -s -m 20 -o /dev/null -w '%{http_code}' $U/)" = 404          # 키 없으면 못 봄
test "$(curl -s -m 20 -o /dev/null -w '%{http_code}' $U/api/state)" = 404
test "$(curl -s -m 20 -o /dev/null -w '%{http_code}' -H "cookie: pk=$K" $U/)" = 200
curl -s -m 20 -H "cookie: pk=$K" $U/api/state | grep -q '"req"'
curl -s -m 20 -H "cookie: pk=$K" $U/live.json | grep -q '"at"'
curl -s -m 20 -H "cookie: pk=$K" $U/ | grep -q '흐름·증감'
test "$(curl -s -m 20 -o /dev/null -w '%{http_code}' https://sns-calendar.remin1994.workers.dev/)" = 404
test "$(curl -s -m 20 -o /dev/null -w '%{http_code}' -H "cookie: pk=$K" https://sns-calendar.remin1994.workers.dev/)" = 200
python3 -c "import ast;ast.parse(open('/Users/ram/.claude/scripts/ga_daily_report.py').read())"
echo PASS
