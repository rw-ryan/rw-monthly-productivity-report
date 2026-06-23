#!/usr/bin/env python3
"""Build confluence-attention.json from epic-report.json."""
import argparse
import json
from pathlib import Path


def has_class(epic: dict, name: str) -> bool:
    return name in epic.get("classification", [])


def is_bulk_closed(epic: dict) -> bool:
    return (
        epic.get("team") == "ARISE"
        and has_class(epic, "released_in_month")
        and epic.get("in_progress_days", 0) == 0
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("report", type=Path, help="Path to epic report JSON")
    p.add_argument("-o", "--output", type=Path, help="Output path (default: same dir as report)")
    args = p.parse_args()

    report = json.loads(args.report.read_text())
    epics = report["all_epics"]

    bulk_closed = [e for e in epics if is_bulk_closed(e)]
    bulk_keys = {e["key"] for e in bulk_closed}

    backfill = [e for e in epics if has_class(e, "needs_backfill")]
    future_not_started = [e for e in epics if has_class(e, "not_started_future_planned")]
    released_zero_non_bulk = [
        e
        for e in epics
        if has_class(e, "released_in_month")
        and e.get("in_progress_days", 0) == 0
        and e["key"] not in bulk_keys
    ]
    long_ip = [
        e
        for e in epics
        if has_class(e, "started_in_month")
        and not has_class(e, "released_in_month")
        and e.get("in_progress_days", 0) > 30
    ]

    out = {
        "bulk_closed": sorted(bulk_closed, key=lambda x: x["key"]),
        "backfill": sorted(backfill, key=lambda x: x["key"]),
        "future_not_started": sorted(future_not_started, key=lambda x: x["key"]),
        "released_zero_non_bulk": sorted(released_zero_non_bulk, key=lambda x: x["key"]),
        "long_ip": sorted(long_ip, key=lambda x: -x.get("in_progress_days", 0)),
    }

    output = args.output or args.report.parent / "confluence-attention.json"
    output.write_text(json.dumps(out, indent=2))
    print(json.dumps({k: len(v) for k, v in out.items()}, indent=2))


if __name__ == "__main__":
    main()
