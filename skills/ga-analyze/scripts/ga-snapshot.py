#!/usr/bin/env python3
"""GA4 snapshot + compare tool.

Takes a structured snapshot of key metrics for the project's GA4 property and
saves it as JSON. Compares against the most recent previous snapshot and emits
a markdown report flagging meaningful deltas + ranked action items.

Usage:
  python scripts/ga-snapshot.py                    # snapshot last 30d, compare, report
  python scripts/ga-snapshot.py --days 7           # shorter window
  python scripts/ga-snapshot.py --no-report        # snapshot only
  python scripts/ga-snapshot.py --compare-only     # re-run comparison with latest two snapshots

Outputs (relative to cwd):
  analytics/snapshots/YYYY-MM-DDTHHMM.json
  analytics/reports/YYYY-MM-DD.md
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account

# Project config — detect by reading scripts/ga-query.py (created by ga-connect skill)
QUERY_SCRIPT = Path("scripts/ga-query.py")


def load_config():
    if not QUERY_SCRIPT.exists():
        sys.exit(
            "ERROR: scripts/ga-query.py not found. Run ga-connect skill first to set up GA4 Data API."
        )
    txt = QUERY_SCRIPT.read_text()
    pid, sa = None, None
    for line in txt.splitlines():
        if line.startswith("PROPERTY_ID"):
            pid = line.split("=", 1)[1].strip().strip('"').strip("'")
        if line.startswith("SA_PATH"):
            expr = line.split("=", 1)[1].strip()
            # os.path.expanduser("...") — grab the string literal
            start = expr.find('"') if '"' in expr else expr.find("'")
            end = expr.rfind('"') if '"' in expr else expr.rfind("'")
            sa = os.path.expanduser(expr[start + 1 : end])
    if not pid or not sa:
        sys.exit(f"ERROR: failed to parse PROPERTY_ID/SA_PATH from {QUERY_SCRIPT}")
    return pid, sa


def client(sa_path):
    creds = service_account.Credentials.from_service_account_file(sa_path)
    return BetaAnalyticsDataClient(credentials=creds)


def run(c, pid, metrics, dimensions, days, limit=200):
    req = RunReportRequest(
        property=f"properties/{pid}",
        metrics=[Metric(name=m) for m in metrics],
        dimensions=[Dimension(name=d) for d in dimensions],
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        limit=limit,
    )
    resp = c.run_report(req)
    dims = [h.name for h in resp.dimension_headers]
    mets = [h.name for h in resp.metric_headers]
    rows = []
    for r in resp.rows:
        row = {}
        for i, d in enumerate(dims):
            row[d] = r.dimension_values[i].value
        for i, m in enumerate(mets):
            row[m] = r.metric_values[i].value
        rows.append(row)
    return rows


def safe_run(c, pid, metrics, dimensions, days, limit=200):
    """Wrapper that returns ('ok', rows) or ('error', error_message).

    Sections can fail independently (invalid metric for this property, e.g. no
    e-commerce or AdMob linked) without poisoning the whole snapshot."""
    try:
        return {"status": "ok", "rows": run(c, pid, metrics, dimensions, days, limit)}
    except Exception as e:
        return {"status": "error", "rows": [], "error": str(e).split("\n")[0][:300]}


def take_snapshot(days):
    pid, sa = load_config()
    c = client(sa)
    snap = {
        "taken_at": datetime.now().isoformat(timespec="seconds"),
        "period_days": days,
        "property_id": pid,
        "sections": {},
    }

    queries = {
        "overview": (
            ["activeUsers", "newUsers", "sessions", "screenPageViews",
             "averageSessionDuration", "userEngagementDuration", "engagementRate"],
            [],
        ),
        "sources": (
            ["sessions", "activeUsers", "userEngagementDuration"],
            ["sessionSource", "sessionMedium"],
        ),
        "new_users_by_day": (["newUsers", "activeUsers"], ["date"]),
        "devices": (
            ["activeUsers", "sessions", "averageSessionDuration"],
            ["deviceCategory"],
        ),
        "countries": (
            ["activeUsers", "sessions", "userEngagementDuration"],
            ["country"],
        ),
        "events": (
            ["eventCount", "totalUsers", "eventCountPerUser"],
            ["eventName"],
        ),
        "pages": (["screenPageViews", "activeUsers"], ["pageTitle"]),
        "first_session_engagement": (
            ["userEngagementDuration", "eventCountPerUser", "totalUsers"],
            ["firstSessionDate"],
        ),
        "purchases": (
            ["totalRevenue", "purchaseRevenue", "transactions", "ecommercePurchases"],
            [],
        ),
        # AdMob / Publisher ads — only populated if AdMob linked to GA4
        "ads": (
            ["publisherAdImpressions", "publisherAdClicks", "totalAdRevenue"],
            [],
        ),
    }

    for section, (metrics, dims) in queries.items():
        limit = 500 if section == "events" else 200
        res = safe_run(c, pid, metrics, dims, days, limit)
        # For backwards-compat we keep `sections[name]` as the row list, and
        # stash the status alongside in `sections_status` so the report can
        # flag which queries failed.
        snap["sections"][section] = res["rows"]
        snap.setdefault("sections_status", {})[section] = res["status"]
        if res["status"] == "error":
            snap.setdefault("sections_errors", {})[section] = res["error"]

    return snap


def save_snapshot(snap, out_dir):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%dT%H%M")
    path = Path(out_dir) / f"{ts}.json"
    path.write_text(json.dumps(snap, indent=2, ensure_ascii=False))
    return path


def find_prev_snapshot(out_dir, current_path):
    files = sorted(Path(out_dir).glob("*.json"))
    files = [f for f in files if f != current_path]
    return files[-1] if files else None


def to_num(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def flat_overview(snap):
    rows = snap["sections"].get("overview", [])
    if not rows:
        return {}
    return {k: to_num(v) for k, v in rows[0].items()}


def events_dict(snap):
    return {r["eventName"]: to_num(r["eventCount"]) for r in snap["sections"].get("events", [])}


def pct_delta(a, b):
    if b == 0:
        return float("inf") if a > 0 else 0.0
    return (a - b) / b * 100


def fmt_delta(cur, prev):
    d = cur - prev
    if prev == 0:
        return f"+{cur:.0f} (new)" if cur > 0 else "0"
    p = pct_delta(cur, prev)
    arrow = "↑" if d > 0 else ("↓" if d < 0 else "=")
    return f"{arrow} {d:+.0f} ({p:+.1f}%)"


def generate_report(snap, prev_snap, out_dir):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    day = datetime.now().strftime("%Y-%m-%d")
    path = Path(out_dir) / f"{day}.md"

    ov = flat_overview(snap)
    prev_ov = flat_overview(prev_snap) if prev_snap else {}
    evs = events_dict(snap)
    prev_evs = events_dict(prev_snap) if prev_snap else {}

    lines = []
    lines.append(f"# GA4 Analysis Report — {day}")
    lines.append("")
    lines.append(f"- Snapshot: `{snap['taken_at']}` · period: last **{snap['period_days']} days**")
    if prev_snap:
        lines.append(f"- Compared to: `{prev_snap['taken_at']}` ({prev_snap['period_days']}d window)")
    else:
        lines.append(f"- No previous snapshot — this is the baseline.")
    lines.append("")

    # --- Headline metrics ---
    lines.append("## Headline")
    lines.append("| Metric | Current | vs prev |")
    lines.append("|---|---|---|")
    headline = [
        ("Active users", "activeUsers"),
        ("New users", "newUsers"),
        ("Sessions", "sessions"),
        ("Screen views", "screenPageViews"),
        ("Avg session (sec)", "averageSessionDuration"),
        ("Engagement rate", "engagementRate"),
    ]
    for label, key in headline:
        cur = ov.get(key, 0)
        prev = prev_ov.get(key, 0)
        delta = fmt_delta(cur, prev) if prev_snap else "—"
        if key == "engagementRate":
            lines.append(f"| {label} | {cur:.1%} | {delta} |")
        elif key == "averageSessionDuration":
            lines.append(f"| {label} | {cur:.1f} | {delta} |")
        else:
            lines.append(f"| {label} | {cur:.0f} | {delta} |")
    lines.append("")

    # --- Key events ---
    lines.append("## Key events")
    lines.append("| Event | Count | Per user | vs prev |")
    lines.append("|---|---|---|---|")
    tracked = [
        "first_visit", "tutorial_step", "session_start", "session_end",
        "challenge_start", "challenge_complete", "research_pull",
        "achievement_unlock", "gpu_expansion", "upgrade_purchase",
        "fusion_attempt", "event_resolved", "career_advance", "offline_collect",
    ]
    active = ov.get("activeUsers", 0) or 1
    for name in tracked:
        cur = evs.get(name, 0)
        prev = prev_evs.get(name, 0)
        per_user = cur / active if active else 0
        delta = fmt_delta(cur, prev) if prev_snap else "—"
        lines.append(f"| {name} | {cur:.0f} | {per_user:.2f} | {delta} |")
    lines.append("")

    # Also surface any events we don't know about yet
    unknown = sorted(set(evs.keys()) - set(tracked))
    if unknown:
        lines.append("**Other events observed**: " + ", ".join(
            f"{e} ({evs[e]:.0f})" for e in unknown if evs[e] > 0
        ))
        lines.append("")

    # --- Conversion ratios ---
    lines.append("## Funnel ratios")
    first_visit = evs.get("first_visit", 0)
    tut = evs.get("tutorial_step", 0)
    challenge_c = evs.get("challenge_complete", 0)
    challenge_s = evs.get("challenge_start", 0)
    upgrade = evs.get("upgrade_purchase", 0)
    tut_per_user = tut / active if active else 0
    ch_complete_rate = challenge_c / challenge_s if challenge_s else 0
    upgrade_rate = upgrade / active if active else 0
    lines.append(f"- Tutorial steps/user: **{tut_per_user:.2f}** — 낮을수록 튜토 드롭 심함")
    lines.append(f"- Challenge complete rate: **{ch_complete_rate:.0%}** (start {challenge_s:.0f} → complete {challenge_c:.0f})")
    lines.append(f"- Upgrade purchase rate: **{upgrade_rate:.0%}** (구매 유저 / 활성 유저)")
    lines.append("")

    # --- Acquisition ---
    lines.append("## Acquisition")
    lines.append("| Source / Medium | Sessions | Users | Engagement/user (sec) |")
    lines.append("|---|---|---|---|")
    for r in snap["sections"].get("sources", [])[:15]:
        src = r.get("sessionSource", "?")
        med = r.get("sessionMedium", "?")
        s = to_num(r.get("sessions", 0))
        u = to_num(r.get("activeUsers", 0))
        eng = to_num(r.get("userEngagementDuration", 0))
        per_user = eng / u if u else 0
        lines.append(f"| {src} / {med} | {s:.0f} | {u:.0f} | {per_user:.0f} |")
    lines.append("")

    # --- Countries ---
    lines.append("## Countries")
    lines.append("| Country | Users | Engagement/user (sec) |")
    lines.append("|---|---|---|")
    for r in snap["sections"].get("countries", [])[:10]:
        c = r.get("country", "?")
        u = to_num(r.get("activeUsers", 0))
        eng = to_num(r.get("userEngagementDuration", 0))
        per_user = eng / u if u else 0
        lines.append(f"| {c} | {u:.0f} | {per_user:.0f} |")
    lines.append("")

    # --- Devices ---
    lines.append("## Devices")
    lines.append("| Device | Users | Sessions | Avg sess (sec) |")
    lines.append("|---|---|---|---|")
    for r in snap["sections"].get("devices", []):
        d = r.get("deviceCategory", "?")
        u = to_num(r.get("activeUsers", 0))
        s = to_num(r.get("sessions", 0))
        asd = to_num(r.get("averageSessionDuration", 0))
        lines.append(f"| {d} | {u:.0f} | {s:.0f} | {asd:.0f} |")
    lines.append("")

    # --- Action items ---
    lines.append("## Action items (ranked)")
    actions = prioritize_actions(ov, evs, snap, prev_snap)
    for i, a in enumerate(actions, 1):
        lines.append(f"{i}. **[{a['severity']}]** {a['title']}")
        lines.append(f"   - *Why*: {a['why']}")
        lines.append(f"   - *How*: {a['how']}")
    lines.append("")

    path.write_text("\n".join(lines))
    return path


def prioritize_actions(ov, evs, snap, prev_snap):
    """Return a list of action dicts sorted by severity. Rules are heuristic and
    tuned for a game in early-access / beta with <1000 DAU. Expect to refine."""
    actions = []
    active = ov.get("activeUsers", 0) or 1
    tut = evs.get("tutorial_step", 0)
    tut_per_user = tut / active
    first_visit = evs.get("first_visit", 0)
    upgrade = evs.get("upgrade_purchase", 0)
    ad_imp = to_num(snap["sections"].get("ads", [{}])[0].get("adImpressions", 0)) if snap["sections"].get("ads") else 0
    purchases = to_num(snap["sections"].get("purchases", [{}])[0].get("transactions", 0)) if snap["sections"].get("purchases") else 0

    # Tutorial drop-off
    if tut_per_user < 3:
        actions.append({
            "severity": "P0",
            "title": "Tutorial 드롭 — step/user 너무 낮음",
            "why": f"tutorial_step/user = {tut_per_user:.2f} (10 이상이어야 완주 유저 다수 확보)",
            "how": "GA4 Custom dimension 등록(`step`, `action`) → 어느 스텝에서 이탈 확인 → 해당 UI 개선",
        })

    # No custom dimensions registered
    if "events" in snap["sections"] and not any(k.startswith("customEvent:") for r in snap["sections"]["events"] for k in r):
        # Check: attempting customEvent:step in the skill workflow returns a 400.
        # We don't currently fetch it from API — presence detection is imperfect.
        # Still flag as P1.
        actions.append({
            "severity": "P1",
            "title": "Custom dimension 미등록 — 이벤트 파라미터 조회 불가",
            "why": "GA4는 event parameter를 custom dimension으로 등록해야 Data API로 조회 가능. 현재 step, action, rarity, grade 등 모든 파라미터 접근 불가",
            "how": "GA4 Admin → Data display → Custom definitions → Create custom dimension. `step`, `action`, `challenge_type`, `grade`, `rarity`, `career_stage` 6개부터 등록",
        })

    # No Key events (conversions) configured
    # ^ Hard to detect via API reliably; leave as heuristic note if upgrade/challenge low

    # Retention — proxy via first_visit/activeUsers ratio
    if active > 5 and first_visit / active > 0.9:
        actions.append({
            "severity": "P0",
            "title": "리텐션 0% — 모든 유저가 신규",
            "why": f"first_visit {first_visit:.0f} / activeUsers {active:.0f} = {first_visit/active:.0%}. 복귀 유저 거의 없음",
            "how": "2일차 복귀 트리거 필요: (a) 웹 — localStorage 기반 복귀 리워드 팝업, (b) 모바일 — 로컬 푸시 알림 (offline_collect 루프와 연계)",
        })

    # Acquisition concentration
    sources = snap["sections"].get("sources", [])
    if sources:
        top_sessions = to_num(sources[0].get("sessions", 0))
        total_sessions = sum(to_num(s.get("sessions", 0)) for s in sources) or 1
        if top_sessions / total_sessions > 0.65:
            actions.append({
                "severity": "P1",
                "title": "유입 채널 단일 의존",
                "why": f"'{sources[0].get('sessionSource')}'가 전체 세션의 {top_sessions/total_sessions:.0%}. 이 채널 끊기면 유입 0",
                "how": "채널 다변화: (a) r/incremental_games / r/idlegames Show post, (b) HN Show HN, (c) product hunt, (d) 한국 디스코드 indie 게임 서버",
            })

    # Monetization signal
    if active > 10 and purchases == 0 and ad_imp == 0:
        actions.append({
            "severity": "P2",
            "title": "수익화 계측 0",
            "why": f"활성 유저 {active:.0f}명인데 transactions=0, adImpressions=0. 수익화 미연결 상태로 추정",
            "how": "AdMob 이벤트(`ad_impression`, `ad_reward`), IAP 이벤트(`purchase`) GA4 연동 확인. e-commerce 이벤트는 표준 param(`currency`, `value`, `transaction_id`) 지킬 것",
        })

    # Mobile penetration
    devices = snap["sections"].get("devices", [])
    if devices:
        mob = sum(to_num(d["activeUsers"]) for d in devices if d.get("deviceCategory") == "mobile")
        tot = sum(to_num(d["activeUsers"]) for d in devices) or 1
        if mob / tot < 0.1 and active > 20:
            actions.append({
                "severity": "P2",
                "title": "모바일 비중 낮음",
                "why": f"Mobile {mob/tot:.0%} vs Desktop {1-mob/tot:.0%}. Capacitor 앱 배포 후 모바일 마케팅 전환 시 재측정",
                "how": "Play Store + App Store 출시 이후 ASO(키워드: idle, tycoon, AI, programming) + 초기 리뷰 유도",
            })

    # Fallback — always give at least one
    if not actions:
        actions.append({
            "severity": "P3",
            "title": "No critical issues detected",
            "why": "Heuristic rules didn't trigger. Manual inspection recommended.",
            "how": "Review the report tables above. Compare with prev snapshot if present.",
        })

    return actions


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--snap-dir", default="analytics/snapshots")
    p.add_argument("--report-dir", default="analytics/reports")
    p.add_argument("--no-report", action="store_true")
    p.add_argument("--compare-only", action="store_true")
    args = p.parse_args()

    if args.compare_only:
        files = sorted(Path(args.snap_dir).glob("*.json"))
        if len(files) < 2:
            sys.exit("Need at least 2 snapshots to compare.")
        cur = json.loads(files[-1].read_text())
        prev = json.loads(files[-2].read_text())
        path = generate_report(cur, prev, args.report_dir)
        print(f"Report: {path}")
        return

    print(f"Taking snapshot (last {args.days} days)…", file=sys.stderr)
    snap = take_snapshot(args.days)
    snap_path = save_snapshot(snap, args.snap_dir)
    print(f"Snapshot: {snap_path}")

    if args.no_report:
        return

    prev_path = find_prev_snapshot(args.snap_dir, snap_path)
    prev_snap = json.loads(prev_path.read_text()) if prev_path else None
    report_path = generate_report(snap, prev_snap, args.report_dir)
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
