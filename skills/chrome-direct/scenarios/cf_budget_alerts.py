"""[제출] Cloudflare 요금 예산 알림을 금액별로 건다(로그인된 대시보드 세션의 /api/v4 alerting/v3/policies).

  cf_budget_alerts.py            # 2,5,10,15,20,30,50달러(이미 있는 금액은 건너뜀)
  cf_budget_alerts.py 3 7       # 원하는 금액만
이번 청구기간 사용량 요금 누적이 금액을 넘으면 remin1994@gmail.com으로 메일 1번(기간마다 초기화). 2026-11-17 먹맵 KV 요금 때 만듦.
"""
import json,time,sys
sys.path.insert(0,'/Users/ram/.claude/skills/chrome-direct/scenarios')
from _common import parser, run, tab, emit
import chromectl as c
ap=parser(__doc__,submit=False); ap.add_argument("amounts",nargs="*",default=["2","5","10","15","20","30","50"]); a=ap.parse_args()
ACC="c023da92383ce204b357f6f18b86eb86"
def api(tid,method,path,body=None):
    b="undefined" if body is None else json.dumps(json.dumps(body))
    c.run_js(tid,f"""window.__r=null;fetch('/api/v4{path}',{{method:'{method}',credentials:'include',headers:{{'content-type':'application/json','x-cross-site-security':'dash'}},body:{b}}}).then(r=>r.text().then(x=>window.__r=r.status+' '+x)).catch(e=>window.__r='ERR '+e);1""")
    for _ in range(60):
        time.sleep(1); r=c.run_js(tid,"window.__r")
        if r and r not in("null","missing value"): return r
def main():
    with tab(f"https://dash.cloudflare.com/{ACC}/billing/billable-usage",a) as tid:
        time.sleep(8)
        pol=json.loads(api(tid,"GET",f"/accounts/{ACC}/alerting/v3/policies").partition(' ')[2])['result']
        bud=[p for p in pol if p['alert_type']=='billing_budget_alert']
        have={str(v) for p in bud for v in (p.get('filters') or {}).get('total_spend_dollars',[])}
        print('existing', [(p['name'],p.get('filters')) for p in bud])
        for amt in a.amounts:
            if amt in have: continue
            body={"name":f"먹맵 요금 ${amt} 넘음","description":"Cloudflare 이번 청구기간 사용량 요금이 이 금액을 넘으면 메일","enabled":True,"alert_type":"billing_budget_alert","mechanisms":{"email":[{"id":"remin1994@gmail.com"}]},"filters":{"total_spend_dollars":[amt]}}
            print(amt, api(tid,"POST",f"/accounts/{ACC}/alerting/v3/policies",body)[:200])
        pol=json.loads(api(tid,"GET",f"/accounts/{ACC}/alerting/v3/policies").partition(' ')[2])['result']
        print('now', sorted(float(v) for p in pol if p['alert_type']=='billing_budget_alert' for v in (p.get('filters') or {}).get('total_spend_dollars',[])))
run(main,a,"Cloudflare 청구 예산 알림(billing_budget_alert)을 금액별로 만든다")
