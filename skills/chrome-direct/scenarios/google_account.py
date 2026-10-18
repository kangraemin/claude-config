#!/usr/bin/env python3
"""[읽기] 이 Chrome 프로필의 Gmail이 어느 계정으로 로그인돼 있는지 (로그인 시도 안 함).
제출·메일 작업 전 'remin1994 로그인 살아 있나' 확인용.

  google_account.py                       # Profile 1, remin1994 기대
  google_account.py --profile "Profile 4" --expect eodisseot@gmail.com
Exit 0 = 기대 계정, 2 = 로그아웃/다른 계정.
"""
from _common import ACCOUNT, Blocked, emit, parser, poll, run, tab

ap = parser(__doc__)
ap.add_argument("--expect", default=ACCOUNT)
a = ap.parse_args()


def main():
    with tab("https://mail.google.com/mail/u/0/#inbox", a) as tid:
        st = poll(tid, r"""if (/accounts\.google\.com|workspace\.google\.com/.test(location.host)) return {state: 'LOGGED_OUT', url: location.href.slice(0, 120)};
          const m = document.title.match(/[\w.+-]+@[\w-]+\.[\w.]+/); return m ? {state: 'IN', account: m[0]} : null;""", 40)
        st["profile"] = a.profile
        if st["state"] != "IN":
            emit(st, "LOGGED_OUT", "Chrome에서 직접 로그인 필요 (자동 로그인 금지)")
            raise Blocked("LOGGED_OUT")
        ok = st["account"].lower() == a.expect.lower()
        emit(st, "OK" if ok else "WRONG_ACCOUNT", st["account"])
        if not ok:
            raise Blocked(f"WRONG_ACCOUNT {st['account']}")


run(main, a, f"READ ONLY. Chrome 프로필 '{a.profile}'에서 https://mail.google.com 을 열어 로그인된 계정 이메일만 출력. 로그아웃이면 LOGGED_OUT (로그인 시도 금지).")
