#!/usr/bin/env python3
"""[제출] 앱인토스 콘솔 — 인앱 광고 그룹 만들기. 같은 이름이 이미 있으면 만들지 않고 그 ID만 출력(멱등).
기본 dry-run: 생성 화면에서 이름·유형·보상을 채워 보기만(확인 체크·등록하기 안 누름, 탭 닫으면 저장 안 됨).
--submit: '위 내용을 확인했어요' 체크 → 등록하기 → ait_adgroups 로 adGroupId 읽기.
광고 약관 동의 화면이 나오면 멈춤(NEEDS_OWNER — 사용자 승인 후 Codex/사람).

  ait_adgroup_create.py seoultaxdev --name "카드 한 장 더 dev" --type 리워드 --unit 카드 --amount 1
  ait_adgroup_create.py ttuk-chiro --name 한판더 --type 전면형 --submit
"""
import subprocess
import sys
import time
from pathlib import Path

from _ait import table, url, wait_page
from _common import Blocked, emit, js, parser, poll, run, tab

ap = parser(__doc__, submit=True)
ap.add_argument("app")
ap.add_argument("--name", required=True)
ap.add_argument("--type", required=True, choices=["리워드", "전면형", "배너"])
ap.add_argument("--unit", help="리워드 보상 단위 (예: 카드)")
ap.add_argument("--amount", help="리워드 수량 (예: 1)")
ap.add_argument("--workspace", default="35273")
a = ap.parse_args()
HERE = Path(__file__).resolve().parent


def existing(tid):
    rows = table(tid)
    return [r for r in rows if len(r["cells"]) > 1 and r["cells"][1] == a.name]


def setv(tid, placeholder, v):
    r = js(tid, f"""const e = [...document.querySelectorAll('input')].filter(__vis).find(e => (e.placeholder || '').includes({placeholder!r}));
      if (!e) return 'NOTFOUND'; return __setv(e, {v!r}) ? 'OK' : 'MISMATCH';""")
    if r != "OK":
        raise RuntimeError(f"칸 '{placeholder}': {r}")


def main():
    if a.type == "리워드" and not (a.unit and a.amount):
        raise Blocked("리워드는 --unit --amount 필요")
    with tab(url(a.workspace, a.app, "placement-group/list?tab=adUnitGroup"), a) as tid:
        poll(tid, "const t = document.body.innerText; return /광고 그룹 이름|광고를 등록하고 수익을|약관에 먼저 동의/.test(t) ? 1 : null", 30)
        if js(tid, "return document.body.innerText.includes('약관에 먼저 동의')"):
            raise Blocked("NEEDS_OWNER 'TOSS 광고대행 서비스 이용약관' 동의가 먼저 필요 — 사용자 승인 후 진행")
        if not js(tid, "return document.body.innerText.includes('광고를 등록하고 수익을')") and existing(tid):
            out = subprocess.run([sys.executable, str(HERE / "ait_adgroups.py"), a.app, "--name", a.name, "--profile", a.profile, "--no-fallback"],
                                 capture_output=True, text=True)
            print(out.stdout)
            print(f"RESULT: EXISTS {a.name}")
            return
        from chromectl import goto
        goto(tid, url(a.workspace, a.app, "placement-group/create"))
        wait_page(tid, "광고 그룹 이름")
        setv(tid, "보상형 광고 1차", a.name)
        r = js(tid, f"""const c = [...document.querySelectorAll('label, [role=radio], button, div')].filter(e => __vis(e) && e.innerText.trim().split('\\n')[0] === {a.type!r})
            .sort((x, y) => x.innerText.length - y.innerText.length)[0]; if (!c) return 'NOTFOUND'; __press(c); return 'OK';""")
        if r != "OK":
            raise RuntimeError(f"유형 '{a.type}': {r}")
        time.sleep(0.8)
        if a.type == "리워드":
            setv(tid, "보석", a.unit)
            setv(tid, "100", a.amount)
        filled = js(tid, "return [...document.querySelectorAll('input[type=text]')].filter(__vis).map(e => e.placeholder + '=' + e.value)")
        if not a.submit:
            emit({"app": a.app, "filled": filled}, "DRY_RUN", "채우기만 — 확인 체크·등록하기 안 누름 (--submit)")
            return
        r = js(tid, """const cb = [...document.querySelectorAll('input[type=checkbox]')].find(e => __vis(e) || (e.parentElement && __vis(e.parentElement)));
          if (!cb) return 'NOTFOUND'; if (!cb.checked) __press(cb.closest('label') || cb); return cb.checked ? 'OK' : 'UNCHECKED';""")
        if r != "OK":
            raise RuntimeError(f"확인 체크박스: {r}")
        r = js(tid, """const b = [...document.querySelectorAll('button')].filter(e => __vis(e) && e.innerText.trim() === '등록하기').pop();
          if (!b || b.disabled) return b ? 'DISABLED' : 'NOTFOUND'; __press(b); return 'OK';""")
        if r != "OK":
            raise RuntimeError(f"등록하기: {r}")
        poll(tid, "return /placement-group\\/list/.test(location.pathname) || /groupId=/.test(location.search) ? 1 : null", 30)
    out = subprocess.run([sys.executable, str(HERE / "ait_adgroups.py"), a.app, "--name", a.name, "--profile", a.profile, "--no-fallback"],
                         capture_output=True, text=True)
    print(out.stdout)
    print(f"RESULT: {'CREATED' if 'AD_GROUP' in out.stdout else 'CREATED_ID_UNREAD'} {a.name}")


run(main, a, f"앱인토스 콘솔 워크스페이스 {a.workspace} 앱 {a.app}의 인앱 광고 > 광고 그룹. 이름 '{a.name}' 그룹이 이미 있으면 만들지 말고 ID만. "
    + (f"없으면 생성: 이름 {a.name}, 유형 {a.type}" + (f", 보상 단위 {a.unit}, 수량 {a.amount}" if a.unit else "") + ", 확인 체크 후 등록하기. " if a.submit
       else "없으면 생성 화면에서 값만 채워 보고 등록하기는 누르지 마라(dry-run). ")
    + "다른 앱·검토요청·출시·약관 동의 금지(약관 화면이면 NEEDS_OWNER). 마지막 줄 AD_GROUP <app> <name> <type> <adGroupId>.", cwd="/tmp")
