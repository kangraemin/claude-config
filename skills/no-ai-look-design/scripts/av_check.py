"""영상·소리를 숫자로 잰다 — "음악 너무 커", "음성 중간에 끊겨", "냅다 시간만 늘림", "같은 음악 반복" 방지.

사용: python3 av_check.py <영상 또는 음성 파일> [--bgm 배경음악파일] [--voice 음성파일]
기준(넘으면 FAIL):
  - 전체 음량(통합 LUFS) -20 ~ -12 (유튜브·쇼츠 기준 약 -14). 너무 작거나 찢어지지 않게.
  - 피크 -1 dBTP 이하.
  - 소리 중간 무음 0.6초 이상 구간 0개(앞뒤 0.5초 제외) — "음성 중간에 존나 끊김".
  - 영상 정지 화면 2초 이상 구간 전체의 15% 이하 — "롱폼 냅다 시간만 늘려놓음".
  - --bgm: 배경음악 길이 60초 미만이면서 결과물이 그보다 길면 FAIL(같은 루프 반복, "뚜두두 존나 반복").
  - --bgm + --voice: 배경음악이 음성보다 12dB 이상 작아야 함("배경음악 너무 커").
마지막 줄: RESULT PASS|FAIL <요약>
"""
import argparse
import json
import re
import subprocess
import sys


def ff(args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args, "-f", "null", "-"],
                          capture_output=True, text=True).stderr


def dur(f):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def has(f, kind):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", kind, "-show_entries", "stream=index",
                          "-of", "csv=p=0", f], capture_output=True, text=True).stdout.strip()
    return bool(out)


def loud(f):
    e = ff(["-i", f, "-af", "ebur128=peak=true", "-vn"])
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", e)
    pk = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", e)
    return (float(i[-1]) if i else None), (float(pk[-1]) if pk else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--bgm")
    ap.add_argument("--voice")
    a = ap.parse_args()
    D = dur(a.file)
    rep, fails = {"duration_s": round(D, 1)}, []
    if has(a.file, "a"):
        lufs, peak = loud(a.file)
        rep.update(lufs=lufs, peak_dbtp=peak)
        if lufs is not None and not -20 <= lufs <= -12:
            fails.append(f"음량 {lufs}LUFS(기준 -20~-12)")
        if peak is not None and peak > -1:
            fails.append(f"피크 {peak}dBTP>-1")
        e = ff(["-i", a.file, "-af", "silencedetect=noise=-45dB:d=0.6", "-vn"])
        st = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", e)]
        en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", e)]
        gaps = [(s, t) for s, t in zip(st, en) if s > 0.5 and t < D - 0.5]
        rep["mid_silences"] = [[round(s, 1), round(t, 1)] for s, t in gaps]
        if gaps:
            fails.append(f"중간 무음 {len(gaps)}곳")
    else:
        fails.append("소리 없음")
    if has(a.file, "v"):
        e = ff(["-i", a.file, "-vf", "freezedetect=n=0.003:d=2", "-an"])
        fd = sum(float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", e))
        rep["frozen_pct"] = round(fd / D * 100, 1) if D else 0
        if D and fd / D > 0.15:
            fails.append(f"정지 화면 {fd/D*100:.0f}%>15%")
    if a.bgm:
        bd = dur(a.bgm)
        rep["bgm_s"] = round(bd, 1)
        if bd < 60 and D > bd + 5:
            fails.append(f"배경음악 {bd:.0f}초 루프 반복")
        if a.voice:
            bl, _ = loud(a.bgm)
            vl, _ = loud(a.voice)
            rep["voice_minus_bgm_db"] = round(vl - bl, 1) if None not in (bl, vl) else None
            if None not in (bl, vl) and vl - bl < 12:
                fails.append(f"배경음악이 음성보다 {vl-bl:.0f}dB만 작음(12 이상)")
    print(json.dumps(rep, ensure_ascii=False))
    print(("RESULT FAIL " + "; ".join(fails)) if fails else "RESULT PASS")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
