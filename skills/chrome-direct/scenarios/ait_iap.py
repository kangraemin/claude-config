#!/usr/bin/env python3
"""[읽기] 앱인토스 콘솔 — 앱의 인앱 결제 상품 목록 페이지 상태와 상품 표(이름·가격·상품 ID·상태).
사업자 정보가 없으면 그 안내 문구를 그대로 돌려준다(BUSINESS_REQUIRED). 생성·수정 안 함.

  ait_iap.py screw-toktok
Output lines `IAP <app> <cell1> | <cell2> | ...`.
"""
from _ait import url, wait_page
from _common import emit, js, parser, poll, run, tab

ap = parser(__doc__)
ap.add_argument("app")
ap.add_argument("--workspace", default="35273")
a = ap.parse_args()
# 기본 탭은 성과(차트)라 상품 표가 없다. ?tab=products 로 열어야 상품 행이 나온다(2026-10-23: 탭 없이 열어 0 rows로 잘못 보고)
LIST = url(a.workspace, a.app, "in-app-purchase/list") + "?tab=products"
STATE = r"""const t = document.body.innerText; if (t.length < 200) return null;
  if (t.includes('사업자 정보를 등록')) return {state: 'BUSINESS_REQUIRED', text: t.slice(0, 1500)};
  const rows = [...document.querySelectorAll('table tbody tr')].filter(__vis).map(r => [...r.children].map(c => c.innerText.trim()));
  if (rows.length || t.includes('인앱 상품을 등록하고')) return {state: 'OK', rows, text: t.slice(0, 1500)};
  return null;"""


def main():
    with tab(LIST, a) as tid:
        wait_page(tid, "인앱", 40)  # raises LOGIN_REQUIRED on the login screen
        try:
            st = poll(tid, STATE, 30)
        except RuntimeError:
            st = {"state": "UNKNOWN", "text": js(tid, "return location.href + '\\n' + document.body.innerText.slice(0, 2500)")}
            print(st["text"])
        emit({"app": a.app, **st}, st["state"], f"{len(st.get('rows') or [])} rows")
        for r in st.get("rows") or []:
            print(f"IAP {a.app} " + " | ".join(r))


run(main, a, f"READ ONLY. 앱인토스 콘솔 워크스페이스 {a.workspace} 앱 {a.app} → 수익화 > 인앱 결제 목록. 페이지 문구와 상품 표만 읽는다. 생성·수정·약관 동의 금지.", cwd="/tmp")
