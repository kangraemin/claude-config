#!/bin/bash
# 배포 대상 앱 전부에 asc validate(제출 전 점검)를 돌려 오류·경고만 모아 보여 준다. 읽기 전용.
#   validate_all.sh            배포 대상 전부
#   validate_all.sh <앱 ID>...  지정한 앱만
# 배포 보류 4개(과학기록·AI-Tycoon·러너스하이·한개국어)는 뺀다(결정 store-release-scope).
D="$(cd "$(dirname "$0")" && pwd)"
SKIP='com.kangraemin.sciencenote|com.aitycoon.game|com.runnersHi|com.kangraemin.hankuk'
if [ $# -gt 0 ]; then IDS="$*"; else
  IDS=$("$D/asc.sh" apps list --output json | python3 -c "
import json,sys,re
d=json.load(sys.stdin); d=d.get('data',d)
print(' '.join(a['id'] for a in d if not re.fullmatch(r'$SKIP', a['attributes']['bundleId'])))")
fi
bad=0
for id in $IDS; do
  out=$("$D/asc.sh" validate --app "$id" --output json 2>/dev/null)
  echo "$out" | python3 -c "
import json,sys
raw=sys.stdin.read(); app='$id'
try: d=json.JSONDecoder().raw_decode(raw[raw.index(chr(123)):])[0]
except Exception: print(f'== {app} 읽기 실패: '+raw.strip()[:200]); sys.exit(2)
st=d.get('remediation',{}).get('steps',[])
st=[i for i in st if i.get('checkId')!='version.state.editable']  # 심사 대기·중이면 당연히 뜨는 것
# socialMedia=false면 socialMediaAgeRestricted는 비어 있는 게 맞다(asc age-rating audit은 Ready). validate만 오탐.
st=[i for i in st if not (i.get('checkId')=='age_rating.missing_field' and i.get('field')=='socialMediaAgeRestricted')]
errs=[i for i in st if i.get('severity')=='error']
warns=[i for i in st if i.get('severity')=='warning']
print(f\"== {app} {d.get('versionString','')} 오류 {len(errs)} 경고 {len(warns)}\")
for i in errs+warns: print('  -', i.get('severity'), i.get('checkId'), '|', i.get('message','')[:120], '→', i.get('remediation','')[:100])
sys.exit(1 if errs else 0)" || bad=$((bad+1))
done
echo "RESULT: $([ $bad -eq 0 ] && echo OK || echo "FAIL $bad")"
