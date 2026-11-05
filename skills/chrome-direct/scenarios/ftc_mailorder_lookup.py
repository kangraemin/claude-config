#!/usr/bin/env python3
"""Usage: ftc_mailorder_lookup.py captcha | answer <6자리> [--out FILE]

공정위 통신판매사업자 공개 조회(ftc.go.kr/bizCommPop.do)로 통신판매업 신고번호가 나왔는지 본다.
- captcha: 사업자번호(개인정보.md에서 패턴)로 세션을 열고 보안문자 그림을 저장한다. 그림 경로를 출력한다.
- answer: 그림을 읽은 6자리를 한 번만 보낸다(재시도 루프 금지). 성공하면 신고번호를 --out 파일에 쓰고 모양·신고일자만 출력.
Pre: 없음(로그인·간편인증 불필요). 정부24 카톡 인증 없이 발급 여부를 볼 수 있어 gov24_status.py보다 먼저 쓴다.
화면 대신 HTTP인 이유: 조회 화면이 단순 폼+보안문자라 curl 세션으로 충분하다.
Gotcha: 보안문자 통과(bizChkAnswer.do=200) 뒤 같은 쿠키로 wrkr_no+answer를 bizCommPop.do에 POST해야 결과가 나온다.
RESULT: CAPTCHA <png> | ISSUED <모양> <신고일자> | NOT_FOUND | WRONG_CAPTCHA | FAIL
"""
import html, os, re, subprocess, sys, tempfile
D = os.path.join(tempfile.gettempdir(), "ftc_lookup"); os.makedirs(D, exist_ok=True)
CK, PNG = os.path.join(D, "ck"), os.path.join(D, "cap.png")
B = "https://www.ftc.go.kr"
def curl(*a): return subprocess.run(["curl", "-s", "-m", "25", "-c", CK, "-b", CK, "-A", "Mozilla/5.0", *a], capture_output=True, text=True).stdout
def brn():
    m = re.search(r"\d{3}-\d{2}-\d{5}", open(os.path.expanduser("~/Documents/oguri-works/개인정보.md")).read())
    if not m: print("RESULT: FAIL 사업자번호 없음"); sys.exit(1)
    return m.group(0).replace("-", "")
def out(s, rc=0): print("RESULT:", s); sys.exit(rc)
a = sys.argv[1:]
if not a: out("FAIL 사용법", 1)
if a[0] == "captcha":
    if os.path.exists(CK): os.remove(CK)
    curl(f"{B}/bizCommPop.do?wrkr_no={brn()}")
    subprocess.run(["curl", "-s", "-m", "25", "-c", CK, "-b", CK, "-A", "Mozilla/5.0", f"{B}/bizCaptchaImg.do?rand=1", "-o", PNG])
    out("CAPTCHA " + PNG)
if a[0] == "answer" and len(a) > 1:
    ans = a[1]; dst = a[a.index("--out") + 1] if "--out" in a else os.path.join(D, "no.txt")
    if curl("-X", "POST", "-d", f"answer={ans}", f"{B}/bizChkAnswer.do").strip().strip('"') != "200": out("WRONG_CAPTCHA (다시 captcha부터, 같은 답 재전송 금지)", 2)
    t = curl("-X", "POST", "-d", f"wrkr_no={brn()}&answer={ans}", f"{B}/bizCommPop.do")
    t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)))
    m = re.search(r"통신판매번호\s+(\S+)\s+사업자등록번호", t)
    if not m or not re.search(r"\d", m.group(1)): out("NOT_FOUND", 2)
    open(dst, "w").write(m.group(1)); d = re.search(r"신고일자\s+(\d{8})", t)
    out(f"ISSUED {re.sub(r'[가-힣]', '가', re.sub(r'[0-9]', '9', m.group(1)))} {d.group(1) if d else '?'} → {dst}")
out("FAIL 사용법", 1)
