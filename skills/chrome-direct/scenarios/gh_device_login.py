"""gh CLI 토큰이 만료됐을 때 기기 로그인(device flow)을 실제 Chrome으로 끝낸다.
사용: python3 gh_device_login.py [--profile "Profile 1"]
마지막 줄 RESULT: OK <계정> | FAIL <이유> | BLOCKED <사람 몫>"""
import os, pty, re, subprocess, sys, time, select, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chromectl as c
ap = argparse.ArgumentParser(); ap.add_argument("--profile", default="Profile 1"); a = ap.parse_args()
pid, fd = pty.fork()
if pid == 0:
    os.environ["GH_BROWSER"] = "true"; os.environ["BROWSER"] = "true"
    os.execvp("gh", ["gh", "auth", "login", "-h", "github.com", "-p", "https", "-w", "--skip-ssh-key"])
buf = ""; code = None; t0 = time.time()
while time.time() - t0 < 40 and not code:
    r, _, _ = select.select([fd], [], [], 1)
    if r:
        try: buf += os.read(fd, 4096).decode("utf-8", "ignore")
        except OSError: break
        if "\x1b[6n" in buf: os.write(fd, b"\x1b[1;1R"); buf = buf.replace("\x1b[6n", "")
        if "(Y/n)" in buf and "_yn" not in globals(): _yn = 1; os.write(fd, b"Y\r")
        m = re.search(r"code:\s*([A-Z0-9]{4}-[A-Z0-9]{4})", buf)
        if m: code = m.group(1)
        if "Press Enter" in buf: os.write(fd, b"\n")
if not code: print(buf[-500:]); print("RESULT: FAIL no device code"); sys.exit(1)
time.sleep(1); os.write(fd, b"\n")
print("CODE", code, flush=True)
tab = c.new_tab("https://github.com/login/device", profile=a.profile)
time.sleep(4)
txt = c.page_text(tab)
if "Sign in" in txt and "Username or email" in txt:
    c.close_tab(tab); print("RESULT: BLOCKED github 로그아웃 상태(" + a.profile + ")"); sys.exit(2)
# 코드 칸 8개(또는 1개)에 넣기
c.js_json(tab, """const v=%r.replace('-','');const ins=[...document.querySelectorAll('input[name^="user-code-"], input#user-code-0, input[type=text]')].filter(i=>i.offsetParent);
if(ins.length>=8){ins.slice(0,8).forEach((i,k)=>{i.value=v[k];i.dispatchEvent(new Event('input',{bubbles:true}))});}else if(ins[0]){ins[0].value=%r;ins[0].dispatchEvent(new Event('input',{bubbles:true}))}
return ins.length;""" % (code, code))
c.js_json(tab, "const b=[...document.querySelectorAll('button,input[type=submit]')].find(b=>/Continue|계속/.test(b.innerText||b.value));if(b)b.click();return !!b;")
for _ in range(10):
    time.sleep(3); txt = c.page_text(tab)
    if re.search(r"Authorize github", txt, re.I):
        c.js_json(tab, "const b=[...document.querySelectorAll('button')].find(b=>/Authorize/.test(b.innerText)&&!b.disabled);if(b)b.click();return !!b;")
    if re.search(r"device is now connected|Congratulations|all set", txt, re.I): break
t1 = time.time()
while time.time() - t1 < 30:
    r, _, _ = select.select([fd], [], [], 1)
    if r:
        try: buf += os.read(fd, 4096).decode("utf-8", "ignore")
        except OSError: break
c.close_tab(tab)
st = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True).stdout + subprocess.run(["gh", "auth", "status"], capture_output=True, text=True).stderr
m = re.search(r"Logged in to github.com account (\S+)", st)
print("RESULT: OK " + m.group(1) if m else "RESULT: FAIL " + txt[:200].replace("\n", " "))
