# Monthly Epic Productivity Report — Reference

## Report title

```text
{Month} {YYYY} Productivity Update
```

Set `REPORT_MONTH_LABEL` in `generate-confluence.py`; use the same value for Confluence `title` and document H1.

## Canonical URLs

| Resource | URL |
|----------|-----|
| Status Time report | https://visable.atlassian.net/plugins/servlet/ac/io.bloompeak.status-time-free/st-report?project.key=PGS&project.id=10612 |
| May 2026 Confluence page | https://visable.atlassian.net/wiki/spaces/PRODTECH/pages/179798040/May+2026+Productivity+Update |
| Jira browse | `https://visable.atlassian.net/browse/{KEY}` |
| Confluence space | `PRODTECH` |

## Epic universe JQL

```
project in (MOB, ARISE, CTOOL, DOL, DRG, FE, KRK, PGS) AND issuetype = Epic AND created >= "2026-03-05"
```

Match Status Time export row count exactly. Do not use broader JQL (227-epic mistake).

## Jira custom fields

| Field | ID |
|-------|-----|
| Planned Start | `customfield_10970` |
| Planned Release | `customfield_10971` |
| Actual Start | `customfield_10972` |
| Actual Release | `customfield_10973` |

Cache: `epic-cache/{KEY}.json` via `getJiraIssue`.

## Team display names

| Jira | Display |
|------|---------|
| ARISE | Arise |
| CTOOL | Bamboo |
| MOB | Hummingbird |
| DOL | Dolphin |
| DRG | Dragon |
| KRK | Kraken |
| PGS | Pegasus |
| FE | Frontend |

## Document outline (Confluence ADF)

1. Executive summary (first)
2. Methodology & measurement rules (data sources merged; simplified bullets + JQL)
3. Team breakdown — Info Panel + table
4. Started & released in month — Info Panel + Jira Work Items
5. Released with In Progress > 0 — Info Panel + Jira Work Items
6. Epics needing attention — Info Panel + 6.1–6.5 each with Info Panel + Jira Work Items

No full epic inventory section.

## Measurement rules

### In Progress time
1. **Both dates set:** If **Actual Start Date** (`customfield_10972`) and **Actual Release Date** (`customfield_10973`) are both populated on the Epic, In Progress = **Actual Release − Actual Start** in **calendar days** (integer day count; negative deltas clamped to 0).
2. **Otherwise:** Status Time CSV column **In Progress** — not Jira changelog.
- Status Time human-readable durations → decimal days (24h = 1 day).
- `-`, empty, or `0m` → 0 days.

### Released in month M
- `Actual Release Date` in month M, **or**
- If Actual Release empty, `resolutiondate` in month M.

### Started in month M — released in M
- Actual Start in M **or** Planned Start in M.

### Started in month M — not yet released
1. Planned Start in month after M → **Not started**.
2. Else if In Progress > 0 **or** Planned Start in M → **Started in M**.
3. Else if status is **To Do** or **Backlog** → **Excluded** (no more data needed flag).
4. Else → **More data needed** (`needs_backfill` in `classification`).

### More data needed (code: `needs_backfill`)
- Status must **not** be `To Do` or `Backlog` (`EARLY_STAGE_STATUSES` in epic-analysis.py).
- Epic not released, not June+ planned, In Progress = 0, no May Planned/Actual Start.
- Omitted from §6.2 Jira Work Items list when status is early-stage.

### Bulk-closed (migration)
- **Arise** + Released in M + **0 days** In Progress.
- §6.1; exclude from normal cycle-time interpretation.

## Attention categories (§6)

| Subsection | Rule |
|------------|------|
| 6.1 Bulk-closed | Arise, released in M, 0 days In Progress |
| 6.2 More data needed | `needs_backfill` in classification; not To Do / Backlog |
| 6.3 Not started | Planned Start after report month |
| 6.4 Released zero In Progress (non-bulk) | Released in M, 0 In Progress, not bulk-closed |
| 6.5 Long In Progress | Started in M, not released, In Progress > 30 days |

`build-attention.py` filters using `classification` arrays on `all_epics`.

## Confluence ADF patterns

### Info Panel
```json
{"type": "panel", "attrs": {"panelType": "info"}, "content": [<paragraphs>]}
```

### Jira Work Items macro
```json
{
  "type": "extension",
  "attrs": {
    "extensionType": "com.atlassian.confluence.macro.core",
    "extensionKey": "jira",
    "parameters": {
      "macroParams": {
        "jqlQuery": {"value": "key in (PGS-701, ...)"},
        "columns": {"value": "key,summary,status,assignee,updated"},
        "maximumIssues": {"value": "100"}
      }
    }
  }
}
```

Publish: `contentFormat: adf`.

### Team breakdown table
- `layout: full-width` on table attrs.
- Multiline headers via ADF `hardBreak` in header cells.
- Column label **More data needed** (not Backfill).
- **In Progress (days)** spelled out (never IP).

## May 2026 baseline (128 epics)

| Metric | Count |
|--------|------:|
| Started in May | 48 |
| Released in May | 31 |
| Both | 2 |
| More data needed | 8 |
| Not started (June+ Planned Start) | 14 |
| Bulk-closed | 21 |

In Progress: **Actual Release − Actual Start** (calendar days) when both dates set on the Epic; otherwise Status Time CSV column. 20 epics used date-delta in v24.

Universe grew 122→128 on Status Time export 2026-06-10 (+8 epics, −2 dropped). CSV: `2026-06-10 17-35-list.csv`. Confluence **v24**.

## Skill scripts

All canonical scripts are in `~/.cursor/skills/rw-monthly-productivity-report/scripts/`:

- `epic-analysis.py` — analysis + `EARLY_STAGE_STATUSES`
- `build-attention.py` — attention JSON from report
- `generate-confluence.py` — ADF body generator
- `parse-status-time-duration.py` — duration parser

When running a new month, copy scripts to a working directory or update path constants at file tops.
