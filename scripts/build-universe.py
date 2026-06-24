#!/usr/bin/env python3
"""Build status-time-universe.json from a Status Time CSV export."""
import argparse
import csv
import json
from pathlib import Path

JQL = (
    'project in (MOB, ARISE, CTOOL, DOL, DRG, FE, KRK, PGS) '
    'AND issuetype = Epic AND created >= "2026-03-05"'
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path, help="Status Time export CSV")
    p.add_argument("-o", "--output", type=Path, required=True, help="Output JSON path")
    args = p.parse_args()

    keys = []
    with args.csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            keys.append(row["Key"])

    payload = {
        "jql": JQL,
        "keys": sorted(keys),
        "count": len(keys),
        "source_csv": str(args.csv),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2))
    print(json.dumps({"count": len(keys), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
