---
name: rw-monthly-productivity-report
description: >-
  Build and publish Visable monthly Epic productivity reports for 8 cross-functional
  teams (Arise, Bamboo, Dolphin, Dragon, Frontend, Hummingbird, Kraken, Pegasus) using the
  Status Time Free report CSV as the epic universe; In Progress from Actual Start/Release
  date difference when both are set, otherwise Status Time CSV column,
  Jira date fields, and Confluence PRODTECH updates. Use when the user asks for monthly
  epic productivity, May 2026 Productivity Update, June Productivity Update, Status Time
  report, More data needed, bulk-closed migration epics, or rw-monthly-productivity-report.
---

# Monthly Epic Productivity Report (Visable)

Produce a structured **English** Confluence report for one calendar month, covering 8 teams. The **Status Time Free report** defines the epic universe. **In Progress** uses Actual Release − Actual Start (calendar days) when both dates are set on the Epic; otherwise the Status Time **In Progress** column — not broad Jira queries or changelog parsing.

Full field IDs, measurement rules, and URLs: [reference.md](reference.md)

## Report title (required)

**Confluence page title** and **H1 heading** must both be:

```text
{Month} {YYYY} Productivity Update
```

| Month | Title |
|-------|-------|
| May 2026 | **May 2026 Productivity Update** |
| June 2026 | **June 2026 Productivity Update** |

Do **not** use “Epic Productivity Update”, “May updates”, or other variants.

In [scripts/generate-confluence.py](scripts/generate-confluence.py), set in `data/config.json`:

```json
"report_month_label": "June 2026"
```

Title is derived as `{report_month_label} Productivity Update`. Use the same string as `title` in `updateConfluencePage`.

## Team display names

| Jira | Display |
|------|---------|
| CTOOL | Bamboo |
| MOB | Hummingbird |
| DOL | Dolphin |
| DRG | Dragon |
| KRK | Kraken |
| PGS | Pegasus |
| ARISE | Arise |
| FE | Frontend |

## Workflow checklist

```
- [ ] 1. Export Status Time CSV; verify row count vs JQL (e.g. 122 for May 2026)
- [ ] 2. Fetch/cache Jira epic JSON → epic-cache/
- [ ] 3. python3 scripts/epic-analysis.py → may-epic-report.json
- [ ] 4. python3 scripts/build-attention.py may-epic-report.json → confluence-attention.json
- [ ] 5. python3 scripts/generate-confluence.py → *-confluence.adf.json
- [ ] 6. updateConfluencePage (contentFormat: adf, full JSON body, correct title)
- [ ] 7. Verify Info Panels, Jira Work Items macros, team names, counts
```

## Step 1 — Status Time export

1. Open [Status Time report](https://visable.atlassian.net/plugins/servlet/ac/io.bloompeak.status-time-free/st-report?project.key=PGS&project.id=10612) with Epic filters.
2. Export CSV (e.g. `~/Downloads/YYYY-MM-DD HH-MM-list.csv`).
3. Universe JQL must match export row count:

```text
project in (MOB, ARISE, CTOOL, DOL, DRG, FE, KRK, PGS) AND issuetype = Epic AND created >= "2026-03-05"
```

**Do not** use “all open epics + month-closed epics” (produced wrong 227-epic set).

## Step 2 — Jira epic cache

For each CSV key: `getJiraIssue` → `epic-cache/{KEY}.json`.

Required: `summary`, `status`, `resolutiondate`, `customfield_10970`–`10973`.

## Step 3 — Analysis scripts

Copy `config.example.json` → `data/config.json` and set report month bounds, CSV path, and export date.

| Config key | Purpose |
|------------|---------|
| `report_month_start` / `report_month_end` | Report month bounds |
| `next_month_start` | First day of month after report month (not-started cutoff) |
| `csv_file` | Status Time export filename (under `data/`) |
| `report_month_label` | e.g. `June 2026` — used in title and prose |

`EARLY_STAGE_STATUSES` in `scripts/epic-analysis.py`: `{"To Do", "Backlog"}` — never flag as more data needed.

```bash
python3 scripts/build-universe.py data/status-time-export.csv -o data/status-time-universe.json
python3 scripts/epic-analysis.py
python3 scripts/build-attention.py data/epic-report.json
python3 scripts/generate-confluence.py
```

Run from repo root; scripts resolve paths via `data/config.json` (or `PRODUCTIVITY_DATA_DIR` env var).

**build-attention.py** reads `classification` arrays from `all_epics` (e.g. `"needs_backfill"`), not boolean fields.

## Step 4 — Confluence document structure

Target: **PRODTECH** (May 2026: pageId `179798040`, title **May 2026 Productivity Update**).

| § | Section | Content |
|---|---------|---------|
| — | Title | `{Month} {YYYY} Productivity Update` |
| **1** | **Executive summary** | **First** — metric counts + In Progress comparison table |
| **2** | **Methodology & measurement rules** | Simplified bullets + JQL (data sources merged here; no separate data-sources section) |
| **3** | Team breakdown | Info Panel summary + full-width table |
| **4** | Started & released in month | Info Panel + Jira Work Items |
| **5** | Released with In Progress > 0 | Info Panel + Jira Work Items |
| **6** | Epics needing attention | Info Panel + subsections 6.1–6.5 |

**Do not** add a full epic inventory table.

### Info Panels (§3 onward)

Use ADF `panel` with `panelType: info` at the **top** of each section (§3–§6 and each §6.x). Helper in generate-confluence.py: `info_panel(paragraph(...))`.

### Jira Work Items (epic lists)

**Never** use bullet lists of epics. Use ADF extension:

```text
extensionKey: jira
jqlQuery: key in (PGS-701, ARISE-1073, ...)
```

Publish with **`contentFormat: adf`**. Read full body from `*-confluence.adf.json` — never send placeholder text.

### Team breakdown table columns

Use multiline ADF headers (not cramped single-line). Labels:

| Column | Meaning |
|--------|---------|
| More data needed | Epics needing dates/signal (excludes To Do / Backlog) |
| Released avg/median In Progress (days) | Date-delta or Status Time for May-released epics |
| Started avg/median In Progress (days) | Date-delta or Status Time for May-started epics |

Never abbreviate In Progress as **IP** in user-facing text.

### §6 Attention categories

| Subsection | Rule |
|------------|------|
| 6.1 Bulk-closed | Arise + released in month + 0 days In Progress (migration) |
| 6.2 More data needed | `needs_backfill` classification; **not** To Do / Backlog |
| 6.3 Not started | Planned Start in month after report month |
| 6.4 Released zero In Progress (non-bulk) | Released in month, 0 In Progress, not bulk-closed |
| 6.5 Long In Progress | Started in month, not released, In Progress > 30 days |

Each subsection: Info Panel summary + Jira Work Items macro.

## Step 5 — Publish

```text
updateConfluencePage:
  cloudId: visable.atlassian.net
  pageId: <page id>
  title: <e.g. May 2026 Productivity Update>
  contentFormat: adf
  body: <full ADF JSON>
  versionMessage: <short change note>
```

## Measurement rules (summary)

| Metric | Rule |
|--------|------|
| Universe | Exact Status Time CSV rows |
| In Progress | **Actual Release − Actual Start** (calendar days) when both dates set; else Status Time **In Progress** column → days (not changelog) |
| Released in month | Actual Release in month, else resolutiondate in month |
| Started (released) | Actual or Planned Start in month |
| Started (not released) | Before June planned; In Progress > 0 or Planned Start in month |
| Not started | Planned Start in month after report month |
| **More data needed** | Would be unclassified, but status **not** To Do / Backlog |
| Bulk-closed | Arise + released in month + 0 days In Progress |

## Learned conventions (do not regress)

1. **Executive summary first**, then simplified methodology (no standalone data-sources section).
2. Link every Epic mention to Jira where inline text is used.
3. Team **display names** in prose and tables.
4. Epic lists = **Jira Work Items macros** only (no bullets, no full inventory).
5. **Info Panel** summary at top of §3–§6 and each §6.x.
6. **More data needed** excludes **To Do** and **Backlog** (newly created epics).
7. Spell out **In Progress** — never **IP** in labels.
8. Report title: **`{Month} {YYYY} Productivity Update`**.

## May 2026 reference

| Item | Value |
|------|-------|
| Page | https://visable.atlassian.net/wiki/spaces/PRODTECH/pages/179798040/May+2026+Productivity+Update |
| Epics | 128 |
| More data needed | 8 |
| Bulk-closed | 21 |
| In Progress rule | Actual Release − Actual Start when both dates set; else Status Time CSV |
| CSV | `2026-06-10 17-35-list.csv` |
| Confluence version | v24 |

Scripts live in this repo's [scripts/](scripts/) directory. Clone from GitHub and install as a Cursor skill (see [README.md](README.md)).

## Scripts

| Script | Output |
|--------|--------|
| [scripts/build-universe.py](scripts/build-universe.py) | `status-time-universe.json` from CSV |
| [scripts/epic-analysis.py](scripts/epic-analysis.py) | `epic-report.json` |
| [scripts/build-attention.py](scripts/build-attention.py) | `confluence-attention.json` |
| [scripts/generate-confluence.py](scripts/generate-confluence.py) | `productivity-update-confluence.adf.json` |
| [scripts/parse-status-time-duration.py](scripts/parse-status-time-duration.py) | Duration → decimal days (imported by analysis) |
