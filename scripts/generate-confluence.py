#!/usr/bin/env python3
"""Generate Confluence ADF body for monthly productivity report."""
import json
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from config import load_config, month_short_name, next_month_short_name

STATUS_TIME_URL = (
    "https://visable.atlassian.net/plugins/servlet/ac/io.bloompeak.status-time-free/"
    "st-report?project.key=PGS&project.id=10612"
)

TEAM = {
    "ARISE": "Arise",
    "CTOOL": "Bamboo",
    "MOB": "Hummingbird",
    "DOL": "Dolphin",
    "DRG": "Dragon",
    "KRK": "Kraken",
    "PGS": "Pegasus",
    "FE": "Frontend",
}

JQL = (
    'project in (MOB, ARISE, CTOOL, DOL, DRG, FE, KRK, PGS) '
    'AND issuetype = Epic AND created >= "2026-03-05"'
)


def macro_id() -> str:
    return str(uuid.uuid4())


def text_node(text: str, bold: bool = False) -> dict:
    node = {"type": "text", "text": text}
    if bold:
        node["marks"] = [{"type": "strong"}]
    return node


def link_node(label: str, href: str) -> dict:
    return {
        "type": "text",
        "text": label,
        "marks": [{"type": "link", "attrs": {"href": href}}],
    }


def paragraph(*parts, bold_all: Optional[str] = None) -> dict:
    if bold_all is not None:
        content = [text_node(bold_all, bold=True)]
    else:
        content = list(parts)
    return {"type": "paragraph", "content": content}


def heading(level: int, text: str) -> dict:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [text_node(text)],
    }


def rule() -> dict:
    return {"type": "rule"}


def code_block(text: str) -> dict:
    return {
        "type": "codeBlock",
        "attrs": {"language": "text"},
        "content": [text_node(text)],
    }


def bullet_list(items: list[list[dict]]) -> dict:
    return {
        "type": "bulletList",
        "content": [
            {"type": "listItem", "content": [paragraph(*item)]} for item in items
        ],
    }


def multiline_parts(lines: list[str], bold: bool = False) -> list[dict]:
    parts: list[dict] = []
    for i, line in enumerate(lines):
        if i > 0:
            parts.append({"type": "hardBreak"})
        parts.append(text_node(line, bold=bold))
    return parts


def table_row_cells(
    cells: list[tuple[list[dict], Optional[int]]],
    header: bool = False,
) -> dict:
    cell_type = "tableHeader" if header else "tableCell"
    row_cells = []
    for content_parts, colwidth in cells:
        attrs = {}
        if colwidth is not None:
            attrs["colwidth"] = [colwidth]
        row_cells.append(
            {
                "type": cell_type,
                "attrs": attrs,
                "content": [paragraph(*content_parts)],
            }
        )
    return {"type": "tableRow", "content": row_cells}


def team_breakdown_table(header_specs: list[tuple[list[str], int]], rows: list[list[str]]) -> dict:
    header_row = table_row_cells(
        [(multiline_parts(lines, bold=True), width) for lines, width in header_specs],
        header=True,
    )
    widths = [w for _, w in header_specs]
    body_rows = []
    for row in rows:
        cells = []
        for value, width in zip(row, widths):
            cells.append(([text_node(value if value != "—" else "—")], width))
        body_rows.append(table_row_cells(cells))
    return {
        "type": "table",
        "attrs": {
            "isNumberColumnEnabled": False,
            "layout": "full-width",
            "width": sum(widths),
        },
        "content": [header_row, *body_rows],
    }


def table(header: list[str], rows: list[list[str]]) -> dict:
    header_cells = [[text_node(h, bold=True)] for h in header]
    body_rows = [
        {
            "type": "tableRow",
            "content": [
                {
                    "type": "tableCell",
                    "attrs": {},
                    "content": [paragraph(text_node(c))],
                }
                for c in row
            ],
        }
        for row in rows
    ]
    return {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
        "content": [
            {
                "type": "tableRow",
                "content": [
                    {
                        "type": "tableHeader",
                        "attrs": {},
                        "content": [paragraph(*cell)],
                    }
                    for cell in header_cells
                ],
            },
            *body_rows,
        ],
    }


def info_panel(*blocks: dict) -> dict:
    return {
        "type": "panel",
        "attrs": {"panelType": "info"},
        "content": list(blocks),
    }


def jira_work_items(keys: list[str]) -> dict:
    if not keys:
        return paragraph(text_node("None", bold=False))
    jql = "key in (" + ", ".join(keys) + ")"
    return {
        "type": "extension",
        "attrs": {
            "layout": "default",
            "extensionType": "com.atlassian.confluence.macro.core",
            "extensionKey": "jira",
            "text": jql,
            "parameters": {
                "macroParams": {
                    "columns": {
                        "value": "key,summary,status,assignee,updated",
                    },
                    "maximumIssues": {"value": str(max(len(keys), 100))},
                    "jqlQuery": {"value": jql},
                },
                "macroMetadata": {
                    "macroId": {"value": macro_id()},
                    "schemaVersion": {"value": "1"},
                    "title": "Jira",
                },
            },
        },
    }


def stat_row(label, s):
    avg = s["average"] if s["average"] is not None else "—"
    med = s["median"] if s["median"] is not None else "—"
    return [label, str(s["count"]), str(avg), str(med)]


def fmt_stat(s):
    return "—" if s["average"] is None else str(s["average"])


def fmt_stat_median(s):
    return "—" if s["median"] is None else str(s["median"])


def main():
    cfg = load_config()
    report_path = cfg["report_file"]
    attention_path = cfg["attention_file"]

    r = json.loads(report_path.read_text())
    attn = json.loads(attention_path.read_text())

    month_label = r.get("report_month_label", cfg["report_month_label"])
    month_name = month_short_name(month_label)
    next_month_name = next_month_short_name(cfg["next_month_start"])
    report_title = f"{month_label} Productivity Update"
    export_date = cfg.get("status_time_export_date", "—")

    cmp = r["comparison"]
    excl_bulk = cmp["released_in_month_excl_bulk"]
    by_team = r["by_team"]
    content: list[dict] = []
    add = content.append

    both_keys = [e["key"] for e in r["started_and_released_in_month"]["epics"]]
    released_ip = sorted(
        [e for e in r["released_in_month"]["epics"] if e["in_progress_days"] > 0],
        key=lambda x: -x["in_progress_days"],
    )
    released_ip_keys = [e["key"] for e in released_ip]
    long_ip_keys = [e["key"] for e in attn["long_ip"]]

    add(heading(1, report_title))
    add(
        paragraph(
            text_node("Report period: "),
            text_node(month_label, bold=True),
            text_node(f" (Europe/Berlin). Status Time export: {export_date}."),
        )
    )
    add(rule())

    add(heading(2, "1. Executive summary"))
    add(
        table(
            ["Metric", "Count"],
            [
                ["Epics analysed", str(r["totals"]["epics_analyzed"])],
                [f"Started in {month_name}", str(r["started_in_month"]["count"])],
                [f"Released in {month_name}", str(r["released_in_month"]["count"])],
                [
                    f"Both started & released in {month_name}",
                    str(r["started_and_released_in_month"]["count"]),
                ],
                ["More data needed", str(len(attn["backfill"]))],
                [
                    f"Not started (Planned Start {next_month_name}+)",
                    str(len(attn["future_not_started"])),
                ],
                ["Bulk-closed (migration)", str(len(attn["bulk_closed"]))],
            ],
        )
    )
    add(paragraph(text_node("In Progress — key comparisons:", bold=True)))
    add(
        table(
            ["Group", "Epics", "Avg (days)", "Median (days)"],
            [
                stat_row(f"Started in {month_name}, not released", cmp["started_not_released"]),
                stat_row(f"Released in {month_name} (all)", cmp["released_in_month"]),
                stat_row(
                    f"Released in {month_name} (excl. bulk-closed)",
                    cmp["released_in_month_excl_bulk"],
                ),
                stat_row(f"Both started & released in {month_name}", cmp["both"]),
                stat_row(f"Started in {month_name} (all)", r["started_in_month"]["in_progress_stats"]),
            ],
        )
    )
    add(
        paragraph(
            text_node(
                f"Of {r['released_in_month']['count']} epics released in {month_name}, "
                f"{len(attn['bulk_closed'])} are Arise migration bulk-closes (0 days In Progress). "
                f"Excluding those, {excl_bulk['count']} epics remain — avg {excl_bulk['average']} days, "
                f"median {excl_bulk['median']} days In Progress."
            )
        )
    )
    add(rule())

    add(heading(2, "2. Methodology & measurement rules"))
    add(
        bullet_list(
            [
                [
                    text_node("Universe: "),
                    text_node(f"{r['totals']['epics_analyzed']} Epics", bold=True),
                    text_node(" from the "),
                    link_node("Status Time report", STATUS_TIME_URL),
                    text_node(" (8 teams, Epic, created ≥ 2026-03-05). Same scope as JQL below."),
                ],
                [
                    text_node("In Progress: when "),
                    text_node("Actual Start Date", bold=True),
                    text_node(" and "),
                    text_node("Actual Release Date", bold=True),
                    text_node(
                        " are both set on the Epic, use their calendar-day difference "
                        "(Actual Release − Actual Start). Otherwise use the Status Time "
                    ),
                    text_node("In Progress", bold=True),
                    text_node(" column (not Jira changelog), converted to days."),
                ],
                [
                    text_node(
                        f"Released in {month_name}: Actual Release Date in {month_name}, "
                        "or resolution date if release date empty."
                    ),
                ],
                [
                    text_node(
                        f"Started in {month_name} (released in {month_name}): "
                        f"Actual Start or Planned Start falls in {month_label}."
                    ),
                ],
                [
                    text_node(
                        f"Started in {month_name} (not yet released): Planned Start before "
                        f"{next_month_name} {cfg['next_month_start'].year}, and either "
                        f"In Progress > 0 in Status Time or Planned Start in {month_label}."
                    ),
                ],
                [
                    text_node(
                        f"Not started: Planned Start is {next_month_name} "
                        f"{cfg['next_month_start'].year} or later (excluded from Started in {month_name})."
                    ),
                ],
                [
                    text_node("More data needed", bold=True),
                    text_node(" (not yet released, not not-started, and "),
                    text_node("not To Do or Backlog", bold=True),
                    text_node(
                        f"): status is beyond early creation — we expect dates or In Progress signal, but "
                        f"In Progress = 0 in Status Time and Planned/Actual Start are missing or before {month_name}. "
                        "To Do and Backlog epics are excluded (newly created; planned dates not required yet)."
                    ),
                ],
                [
                    text_node(
                        f"Bulk-closed: Arise epics released in {month_name} with 0 days In Progress "
                        "(Jira migration batch)."
                    ),
                ],
                [
                    text_node("Teams: Arise, Bamboo, Dolphin, Dragon, Frontend, Hummingbird, Kraken, Pegasus."),
                ],
            ]
        )
    )
    add(code_block(JQL))
    add(rule())

    add(heading(2, "3. Team breakdown"))
    backfill_leaders = sorted(
        [(TEAM[c], by_team[c]["backfill_needed"]) for c in TEAM if by_team[c]["backfill_needed"] > 0],
        key=lambda x: -x[1],
    )
    backfill_summary = (
        ", ".join(f"{name} ({n})" for name, n in backfill_leaders[:3])
        if backfill_leaders
        else "none"
    )
    add(
        info_panel(
            paragraph(
                text_node(
                    f"Highest more-data-needed counts: {backfill_summary} "
                    "(excludes To Do / Backlog). "
                    "— = no epics in that column."
                )
            )
        )
    )
    team_rows = []
    for code in ["ARISE", "CTOOL", "DOL", "MOB", "DRG", "FE", "KRK", "PGS"]:
        d = by_team[code]
        rel = d["in_progress_stats"]["released_in_month"]
        sta = d["in_progress_stats"]["started_in_month"]
        team_rows.append(
            [
                TEAM[code],
                str(d["total_epics"]),
                str(d["started_in_month"]),
                str(d["released_in_month"]),
                str(d["both"]),
                str(d["backfill_needed"]),
                str(d["not_started_future_planned"]),
                fmt_stat(rel),
                fmt_stat_median(rel),
                fmt_stat(sta),
                fmt_stat_median(sta),
            ]
        )
    add(
        team_breakdown_table(
            [
                (["Team"], 96),
                (["Epics"], 58),
                (["Started", month_name], 72),
                (["Released", month_name], 76),
                (["Both"], 52),
                (["More data", "needed"], 92),
                (["Not started", f"({next_month_name}+)"], 92),
                (["Released", "avg In Progress", "(days)"], 118),
                (["Released", "median In Progress", "(days)"], 128),
                (["Started", "avg In Progress", "(days)"], 118),
                (["Started", "median In Progress", "(days)"], 128),
            ],
            team_rows,
        )
    )
    add(rule())

    add(heading(2, f"4. Started & released in {month_name} (both)"))
    both_count = r["started_and_released_in_month"]["count"]
    add(
        info_panel(
            paragraph(
                text_node(
                    f"{both_count} epic(s) both started and released within {month_name}."
                    if both_count
                    else f"No epics both started and released within {month_name}."
                )
            )
        )
    )
    add(jira_work_items(both_keys))
    add(rule())

    add(heading(2, f"5. Released in {month_name} with In Progress > 0"))
    top_line = ""
    if released_ip:
        top = ", ".join(f"{e['key']} ({e['in_progress_days']}d)" for e in released_ip[:3])
        med = excl_bulk["median"] if excl_bulk["median"] is not None else "—"
        top_line = (
            f"{excl_bulk['count']} of {r['released_in_month']['count']} {month_name}-released epics remain after "
            f"excluding {len(attn['bulk_closed'])} bulk-closes (all have In Progress > 0). Longest: {top}"
            + (" …" if len(released_ip) > 3 else "")
            + f". Median In Progress: {med} days (avg {excl_bulk['average']} days)."
        )
    add(info_panel(paragraph(text_node(top_line or "No epics in this category."))))
    add(jira_work_items(released_ip_keys))
    add(rule())

    attention_total = (
        len(attn["bulk_closed"])
        + len(attn["backfill"])
        + len(attn["future_not_started"])
        + len(attn["released_zero_non_bulk"])
        + len(attn["long_ip"])
    )
    add(heading(2, "6. Epics needing attention"))
    add(
        info_panel(
            paragraph(
                text_node(
                    f"{attention_total} epic entries across 5 categories. "
                    f"Priority: {len(attn['backfill'])} need more Jira date data, "
                    f"{len(attn['bulk_closed'])} are likely migration bulk-closes, "
                    f"{len(attn['long_ip'])} have unusually long In Progress while still open."
                )
            )
        )
    )

    add(heading(3, "6.1 Bulk-closed epics (migration)"))
    add(
        info_panel(
            paragraph(
                text_node(
                    f"{len(attn['bulk_closed'])} Arise epics — released in {month_name} with 0 days In Progress; "
                    "exclude from normal cycle-time interpretation."
                )
            )
        )
    )
    add(jira_work_items([e["key"] for e in attn["bulk_closed"]]))

    add(heading(3, "6.2 More data needed"))
    add(
        info_panel(
            paragraph(
                text_node(
                    f"{len(attn['backfill'])} epics in active statuses (not To Do / Backlog) — "
                    f"cannot classify Started in {month_name} without Planned Start, Actual Start, or In Progress signal."
                )
            )
        )
    )
    add(jira_work_items([e["key"] for e in attn["backfill"]]))

    add(heading(3, f"6.3 Not started (Planned Start in {next_month_name} or later)"))
    add(
        info_panel(
            paragraph(
                text_node(
                    f"{len(attn['future_not_started'])} epics planned to start from {next_month_name}."
                )
            )
        )
    )
    add(jira_work_items([e["key"] for e in attn["future_not_started"]]))

    add(heading(3, f"6.4 Released in {month_name} with zero In Progress (non-bulk)"))
    add(
        info_panel(
            paragraph(
                text_node(
                    f"{len(attn['released_zero_non_bulk'])} epic(s) outside the Arise migration batch — "
                    "released with no recorded In Progress time."
                )
            )
        )
    )
    add(jira_work_items([e["key"] for e in attn["released_zero_non_bulk"]]))

    add(heading(3, f"6.5 Long In Progress time (> 30 days, started in {month_name}, not released)"))
    long_summary = f"{len(attn['long_ip'])} epics still open with > 30 days In Progress."
    if attn["long_ip"]:
        long_summary += " " + ", ".join(
            f"{e['key']} ({e['in_progress_days']}d)" for e in attn["long_ip"]
        )
    add(info_panel(paragraph(text_node(long_summary))))
    add(jira_work_items(long_ip_keys))

    add(rule())
    add(
        paragraph(
            text_node("Generated by "),
            text_node("rw-monthly-productivity-report", bold=True),
            text_node(" (Visable Cursor skill)."),
        )
    )

    doc = {"version": 1, "type": "doc", "content": content}
    out_json = cfg["adf_output"]
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(doc, indent=2))
    print(f"Wrote ADF doc with {len(content)} top-level nodes -> {out_json}")

    jql_urls = cfg["jql_urls_output"]
    lines = []
    sections = [
        ("4-both", both_keys),
        ("5-released-ip", released_ip_keys),
        ("6.1-bulk-closed", [e["key"] for e in attn["bulk_closed"]]),
        ("6.2-more-data-needed", [e["key"] for e in attn["backfill"]]),
        ("6.3-future-not-started", [e["key"] for e in attn["future_not_started"]]),
        ("6.4-released-zero-non-bulk", [e["key"] for e in attn["released_zero_non_bulk"]]),
        ("6.5-long-ip", long_ip_keys),
    ]
    for name, keys in sections:
        if keys:
            jql = quote(f"key in ({', '.join(keys)})")
            lines.append(f"# {name}")
            lines.append(f"https://visable.atlassian.net/issues/?jql={jql}")
            lines.append("")
    jql_urls.write_text("\n".join(lines))
    print(f"Wrote {jql_urls}")


if __name__ == "__main__":
    main()
