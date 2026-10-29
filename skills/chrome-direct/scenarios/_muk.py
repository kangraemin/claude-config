"""먹맵 외국어 커뮤니티 스크립트 공용 (sns.env 읽기/쓰기, 입력칸 채우기). 값을 출력하지 않는다."""
import json, os, secrets, string
from pathlib import Path

ENV = Path.home() / ".claude/sns.env"


def env_get(k):
    if ENV.exists():
        for l in ENV.read_text().splitlines():
            if l.startswith(k + "="):
                return l.split("=", 1)[1].strip().strip('"')
    return None


def env_set(k, v):
    lines = ENV.read_text().splitlines() if ENV.exists() else []
    lines = [l for l in lines if not l.startswith(k + "=")] + [f'{k}="{v}"']
    ENV.write_text("\n".join(lines) + "\n")
    os.chmod(ENV, 0o600)


def newpw(n=16):
    al = string.ascii_letters + string.digits
    return "".join(secrets.choice(al) for _ in range(n - 2)) + "A9"


def fill_js(selector, val):
    """selector 의 보이는 마지막 입력칸에 네이티브 setter 로 값 넣기 (JS 문자열 반환)."""
    return f"""const f=[...document.querySelectorAll({json.dumps(selector)})].filter(e=>e.offsetParent).pop();
      if(!f) return 'NOFIELD';
      const P=f.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(P,'value').set.call(f,{json.dumps(val)});
      f.dispatchEvent(new Event('input',{{bubbles:true}})); f.dispatchEvent(new Event('change',{{bubbles:true}})); return 'ok'"""
