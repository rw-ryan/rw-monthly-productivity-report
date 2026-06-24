#!/usr/bin/env python3
"""Monthly productivity analysis — Status Time universe + CSV In Progress column."""
import csv
import json
import re
import statistics
import sys
from datetime import date, datetime
from pathlib import Path

from config import load_config, month_short_name, next_month_short_name

TEAMS = ["ARISE", "CTOOL", "DOL", "MOB", "DRG", "FE", "KRK", "PGS"]
EARLY_STAGE_STATUSES = frozenset({"To Do", "Backlog"})

DURATION_RE = re.compile(
    r"(?:(\d+)M\s*)?(?:(\d+)w\s*)?(?:(\d+)d\s*)?(?:(\d+)h\s*)?(?:(\d+)m)?"
)


def parse_status_time_duration(raw):
    if raw is None or str(raw).strip() in ("", "-"):
        return 0.0
    s = str(raw).strip()
    if s == "0m":
        return 0.0
    m = DURATION_RE.fullmatch(s)
    if not m:
        return 0.0
    months, weeks, days, hours, minutes = (int(x) if x else 0 for x in m.groups())
    total_minutes = (
        months * 30 * 24 * 60 + weeks * 7 * 24 * 60 + days * 24 * 60 + hours * 60 + minutes
    )
    return round(total_minutes / (24 * 60), 2)


def load_status_time_ip(csv_file: Path):
    ip_by_key = {}
    with csv_file.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ip_by_key[row["Key"]] = {
                "in_progress_days": parse_status_time_duration(row.get("In Progress")),
                "in_progress_raw": row.get("In Progress", "-"),
                "status_time_status": row.get("Status"),
            }
    return ip_by_key


def parse_date(v):
    if v is None:
        return None
    if isinstance(v, str):
        return datetime.strptime(v[:10], "%Y-%m-%d").date()
    return None


def resolve_in_progress_days(actual_start, actual_release, status_time_days, status_time_raw):
    if actual_start is not None and actual_release is not None:
        days = max(0, (actual_release - actual_start).days)
        raw = (
            f"Actual Release − Actual Start "
            f"({actual_start.isoformat()} → {actual_release.isoformat()})"
        )
        return float(days), raw, "date_delta"
    return status_time_days, status_time_raw, "status_time"


def in_report_month(d: date | None, month_start: date, month_end: date) -> bool:
    return d is not None and month_start <= d <= month_end


def on_or_after(d: date | None, boundary: date) -> bool:
    return d is not None and d >= boundary


def is_released_in_month(actual_release, resolutiondate, month_start, month_end):
    if in_report_month(actual_release, month_start, month_end):
        return True
    if actual_release is None and in_report_month(parse_date(resolutiondate), month_start, month_end):
        return True
    return False


def is_not_released_yet(actual_release, resolutiondate, status, released_in_month, month_end):
    if released_in_month:
        return False
    if (status or "") in ("Closed", "Done"):
        res = parse_date(resolutiondate)
        return res is not None and res > month_end
    if actual_release is None:
        return True
    return actual_release > month_end


def classify_started_in_month(
    released_in_month,
    not_released,
    planned_start,
    actual_start,
    ip_days,
    month_start,
    month_end,
    next_month_start,
):
    if released_in_month:
        started = in_report_month(actual_start, month_start, month_end) or in_report_month(
            planned_start, month_start, month_end
        )
        return started, False, False

    if on_or_after(planned_start, next_month_start):
        return False, False, True

    if not_released:
        if ip_days > 0 or in_report_month(planned_start, month_start, month_end):
            return True, False, False
        return False, True, False

    started = in_report_month(actual_start, month_start, month_end) or in_report_month(
        planned_start, month_start, month_end
    )
    return (True, False, False) if started else (False, True, False)


def attention_reasons(epic, month_start, month_end, next_month_start):
    reasons = []
    if epic["needs_backfill"]:
        reasons.append("needs_backfill")
    if epic["released_in_month"] and epic["in_progress_days"] == 0:
        reasons.append("released_in_month_zero_in_progress")
    if (
        epic["started_in_month"]
        and epic["in_progress_days"] == 0
        and not in_report_month(parse_date(epic.get("planned_start")), month_start, month_end)
    ):
        reasons.append("started_in_month_zero_in_progress_no_planned_in_month")
    ps = parse_date(epic.get("planned_start"))
    ar = parse_date(epic.get("actual_release"))
    ast = parse_date(epic.get("actual_start"))
    if ar and ast and ar < ast:
        reasons.append("release_before_start")
    if on_or_after(ps, next_month_start) and epic.get("status") == "In Progress":
        reasons.append("planned_future_but_in_progress")
    return reasons


def is_bulk_closed(epic: dict) -> bool:
    return (
        epic.get("team") == "ARISE"
        and epic.get("released_in_month")
        and epic.get("in_progress_days", 0) == 0
    )


def stats(vals):
    if not vals:
        return {"count": 0, "average": None, "median": None}
    return {
        "count": len(vals),
        "average": round(statistics.mean(vals), 2),
        "median": round(statistics.median(vals), 2),
    }


def epic_list(entries):
    return [
        {
            "key": e["key"],
            "team": e["team"],
            "summary": e["summary"],
            "in_progress_days": e["in_progress_days"],
            "in_progress_raw": e.get("in_progress_raw"),
            "planned_start": e["planned_start"],
            "actual_start": e["actual_start"],
            "actual_release": e["actual_release"],
        }
        for e in entries
    ]


def process_epic(issue, ip_info, month_start, month_end, next_month_start):
    fields = issue.get("fields") or {}
    key = issue["key"]
    team = fields.get("project", {}).get("key", key.split("-")[0])
    status = (fields.get("status") or {}).get("name", "Unknown")
    planned_start = parse_date(fields.get("customfield_10970"))
    planned_release = parse_date(fields.get("customfield_10971"))
    actual_start = parse_date(fields.get("customfield_10972"))
    actual_release = parse_date(fields.get("customfield_10973"))
    resolutiondate = fields.get("resolutiondate")

    ip_days, ip_raw, ip_source = resolve_in_progress_days(
        actual_start,
        actual_release,
        ip_info["in_progress_days"],
        ip_info["in_progress_raw"],
    )

    released_in_month = is_released_in_month(
        actual_release, resolutiondate, month_start, month_end
    )
    not_released = is_not_released_yet(
        actual_release, resolutiondate, status, released_in_month, month_end
    )

    started, backfill, future_planned = classify_started_in_month(
        released_in_month,
        not_released,
        planned_start,
        actual_start,
        ip_days,
        month_start,
        month_end,
        next_month_start,
    )

    if backfill and status in EARLY_STAGE_STATUSES:
        backfill = False

    classifications = []
    if released_in_month:
        classifications.append("released_in_month")
    if started:
        classifications.append("started_in_month")
    if backfill:
        classifications.append("needs_backfill")
    if future_planned:
        classifications.append("not_started_future_planned")

    epic = {
        "key": key,
        "team": team,
        "summary": fields.get("summary", ""),
        "status": status,
        "classification": classifications,
        "in_progress_days": ip_days,
        "in_progress_raw": ip_raw,
        "in_progress_source": ip_source,
        "planned_start": planned_start.isoformat() if planned_start else None,
        "planned_release": planned_release.isoformat() if planned_release else None,
        "actual_start": actual_start.isoformat() if actual_start else None,
        "actual_release": actual_release.isoformat() if actual_release else None,
        "resolutiondate": parse_date(resolutiondate).isoformat() if parse_date(resolutiondate) else None,
        "released_in_month": released_in_month,
        "started_in_month": started,
        "needs_backfill": backfill,
        "not_started_future_planned": future_planned,
        "needs_attention_reason": [],
    }
    epic["needs_attention_reason"] = attention_reasons(
        epic, month_start, month_end, next_month_start
    )
    return epic


def main():
    cfg = load_config()
    month_start = cfg["report_month_start"]
    month_end = cfg["report_month_end"]
    next_month_start = cfg["next_month_start"]
    month_label = cfg["report_month_label"]
    month_name = month_short_name(month_label)
    next_month_name = next_month_short_name(next_month_start)

    csv_file = cfg["csv_file"]
    cache_dir = cfg["cache_dir"]
    universe_file = cfg["universe_file"]
    out_file = cfg["report_file"]

    if not csv_file.exists():
        print(f"Missing CSV: {csv_file}", file=sys.stderr)
        sys.exit(1)
    if not universe_file.exists():
        print(f"Missing universe file: {universe_file}", file=sys.stderr)
        sys.exit(1)

    universe = json.loads(universe_file.read_text())
    keys = universe["keys"]
    ip_map = load_status_time_ip(csv_file)

    csv_keys = set(ip_map)
    missing_csv = sorted(set(keys) - csv_keys)
    extra_csv = sorted(csv_keys - set(keys))
    if missing_csv or extra_csv:
        print("CSV/universe mismatch:", missing_csv, extra_csv, file=sys.stderr)
        sys.exit(1)

    all_epics = []
    missing_cache = []

    for key in keys:
        cache_path = cache_dir / f"{key}.json"
        if not cache_path.exists():
            missing_cache.append(key)
            continue
        issue = json.loads(cache_path.read_text())
        all_epics.append(
            process_epic(issue, ip_map[key], month_start, month_end, next_month_start)
        )

    if missing_cache:
        print(json.dumps({"error": "missing_cache", "keys": missing_cache}, indent=2))
        sys.exit(2)

    started = [e for e in all_epics if e["started_in_month"]]
    released = [e for e in all_epics if e["released_in_month"]]
    released_excl_bulk = [e for e in released if not is_bulk_closed(e)]
    both = [e for e in all_epics if e["started_in_month"] and e["released_in_month"]]
    backfill = [e for e in all_epics if e["needs_backfill"]]
    future_planned = [e for e in all_epics if e["not_started_future_planned"]]
    started_only = [e for e in all_epics if e["started_in_month"] and not e["released_in_month"]]

    by_team = {}
    for team in TEAMS:
        team_epics = [e for e in all_epics if e["team"] == team]
        attention = [e for e in team_epics if e["needs_attention_reason"]]
        team_released = [e for e in team_epics if e["released_in_month"]]
        team_released_excl_bulk = [e for e in team_released if not is_bulk_closed(e)]
        team_started = [e for e in team_epics if e["started_in_month"]]
        team_both = [e for e in team_epics if e["started_in_month"] and e["released_in_month"]]
        by_team[team] = {
            "total_epics": len(team_epics),
            "started_in_month": len(team_started),
            "released_in_month": len(team_released),
            "both": len(team_both),
            "backfill_needed": sum(1 for e in team_epics if e["needs_backfill"]),
            "not_started_future_planned": sum(
                1 for e in team_epics if e["not_started_future_planned"]
            ),
            "in_progress_stats": {
                "released_in_month": stats([e["in_progress_days"] for e in team_released]),
                "released_in_month_excl_bulk": stats(
                    [e["in_progress_days"] for e in team_released_excl_bulk]
                ),
                "started_in_month": stats([e["in_progress_days"] for e in team_started]),
                "both": stats([e["in_progress_days"] for e in team_both]),
            },
            "attention_epics": [
                {"key": e["key"], "summary": e["summary"][:60], "reasons": e["needs_attention_reason"]}
                for e in attention
            ],
        }

    report = {
        "report_month_label": month_label,
        "report_month_start": month_start.isoformat(),
        "report_month_end": month_end.isoformat(),
        "next_month_start": next_month_start.isoformat(),
        "assumptions": [
            f"Epic universe: {len(all_epics)} epics from Status Time report (8 teams, Epic, created >= 2026-03-05)",
            f"In Progress days: Actual Release − Actual Start (calendar days) when both dates set; "
            f"else Status Time CSV column 'In Progress' ({csv_file.name})",
            f"Released in {month_name}: Actual Release Date in {month_name} OR resolutiondate in {month_name} when Actual Release missing",
            f"Started in {month_name} (not released): planned_start before {next_month_name} AND (Status Time In Progress > 0 OR planned_start in {month_name}); else more data needed unless status is To Do or Backlog",
            f"Started in {month_name} (released in {month_name}): actual_start in {month_name} OR planned_start in {month_name}",
            f"Not started: planned_start in {next_month_name} or later",
        ],
        "source": {"csv": str(csv_file), "csv_rows": len(ip_map), "jql": universe.get("jql")},
        "totals": {"epics_analyzed": len(all_epics), "missing_cache": missing_cache},
        "started_in_month": {
            "count": len(started),
            "in_progress_stats": stats([e["in_progress_days"] for e in started]),
            "epics": epic_list(started),
            "needs_backfill": [
                {"key": e["key"], "team": e["team"], "summary": e["summary"]} for e in backfill
            ],
            "not_started_future_planned": [
                {
                    "key": e["key"],
                    "team": e["team"],
                    "summary": e["summary"],
                    "planned_start": e["planned_start"],
                }
                for e in future_planned
            ],
        },
        "released_in_month": {
            "count": len(released),
            "in_progress_stats": stats([e["in_progress_days"] for e in released]),
            "in_progress_stats_excl_bulk": stats(
                [e["in_progress_days"] for e in released_excl_bulk]
            ),
            "in_progress_stats_ip_gt_0": stats(
                [e["in_progress_days"] for e in released if e["in_progress_days"] > 0]
            ),
            "epics": epic_list(released),
        },
        "started_and_released_in_month": {
            "count": len(both),
            "in_progress_stats": stats([e["in_progress_days"] for e in both]),
            "epics": epic_list(both),
        },
        "comparison": {
            "started_only": stats([e["in_progress_days"] for e in started_only]),
            "released_in_month": stats([e["in_progress_days"] for e in released]),
            "released_in_month_excl_bulk": stats(
                [e["in_progress_days"] for e in released_excl_bulk]
            ),
            "released_in_month_ip_gt_0": stats(
                [e["in_progress_days"] for e in released if e["in_progress_days"] > 0]
            ),
            "both": stats([e["in_progress_days"] for e in both]),
            "started_not_released": stats([e["in_progress_days"] for e in started_only]),
        },
        "by_team": by_team,
        "all_epics": [
            {
                "key": e["key"],
                "team": e["team"],
                "summary": e["summary"],
                "status": e["status"],
                "classification": e["classification"],
                "in_progress_days": e["in_progress_days"],
                "in_progress_raw": e["in_progress_raw"],
                "planned_start": e["planned_start"],
                "actual_start": e["actual_start"],
                "actual_release": e["actual_release"],
                "needs_attention_reason": e["needs_attention_reason"],
            }
            for e in sorted(all_epics, key=lambda x: x["key"])
        ],
    }

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                "epics_analyzed": len(all_epics),
                "started_in_month": len(started),
                "released_in_month": len(released),
                "both": len(both),
                "backfill": len(backfill),
                "future_planned_not_started": len(future_planned),
                "attention": sum(1 for e in all_epics if e["needs_attention_reason"]),
                "comparison": report["comparison"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
