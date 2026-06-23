# Monthly Epic Productivity Report

Cursor skill and Python toolkit for Visable **monthly Epic productivity reports** — 7 cross-functional teams (Arise, Bamboo, Dolphin, Hummingbird, Dragon, Kraken, Pegasus).

Produces a structured English Confluence page in **PRODTECH** with executive summary, methodology, team breakdown, and epics needing attention. Epic universe comes from the **Status Time Free** CSV export; **In Progress** uses Actual Release − Actual Start when both dates are set, otherwise the Status Time column.

## Quick start

### 1. Install as a Cursor skill (recommended)

```bash
git clone https://github.com/rw-ryan/rw-monthly-productivity-report.git
ln -s "$(pwd)/rw-monthly-productivity-report" ~/.cursor/skills/rw-monthly-productivity-report
```

> **Org sharing:** This repo is under `rw-ryan` for now. To host under `visable-dev`, ask an org admin to create `visable-dev/rw-monthly-productivity-report` and transfer or mirror this repo, then add team members as collaborators.

Or copy the folder into `~/.cursor/skills/rw-monthly-productivity-report`.

Cursor will pick up `SKILL.md` automatically when you ask for a monthly productivity update.

### 2. Configure the report month

```bash
cp config.example.json data/config.json
# Edit data/config.json — set report month, CSV filename, export date
```

### 3. Export Status Time CSV

1. Open the [Status Time report](https://visable.atlassian.net/plugins/servlet/ac/io.bloompeak.status-time-free/st-report?project.key=PGS&project.id=10612) with Epic filters.
2. Export CSV → save as `data/status-time-export.csv` (or the path in `config.json`).
3. Verify row count matches universe JQL (see `reference.md`).

### 4. Build universe + Jira cache

```bash
python3 scripts/build-universe.py data/status-time-export.csv -o data/status-time-universe.json
```

For each key in the universe, fetch Jira issue JSON via MCP or API into `data/epic-cache/{KEY}.json`. Required fields: `summary`, `status`, `resolutiondate`, `customfield_10970`–`10973`.

### 5. Run analysis pipeline

```bash
cd scripts
python3 epic-analysis.py
python3 build-attention.py ../data/epic-report.json -o ../data/confluence-attention.json
python3 generate-confluence.py
```

Outputs:

| File | Purpose |
|------|---------|
| `data/epic-report.json` | Full analysis |
| `data/confluence-attention.json` | §6 attention categories |
| `data/productivity-update-confluence.adf.json` | Confluence ADF body |
| `data/jira-work-item-urls.txt` | JQL URLs (fallback) |

### 6. Publish to Confluence

Use Atlassian MCP `updateConfluencePage`:

```text
cloudId: visable.atlassian.net
pageId: <your page id>
title: June 2026 Productivity Update
contentFormat: adf
body: <full contents of productivity-update-confluence.adf.json>
versionMessage: Monthly productivity update
```

## Report title

Confluence page title and H1 must be:

```text
{Month} {YYYY} Productivity Update
```

Example: **June 2026 Productivity Update**

## Repository layout

```
├── SKILL.md              # Cursor agent instructions
├── reference.md          # Field IDs, URLs, measurement rules
├── config.example.json   # Copy to data/config.json
├── data/                 # Local working data (gitignored)
│   ├── config.json
│   ├── status-time-export.csv
│   ├── status-time-universe.json
│   ├── epic-cache/
│   └── *.json            # Generated outputs
└── scripts/
    ├── config.py
    ├── build-universe.py
    ├── epic-analysis.py
    ├── build-attention.py
    ├── generate-confluence.py
    └── parse-status-time-duration.py
```

## Environment

Optional override for data directory:

```bash
export PRODUCTIVITY_DATA_DIR=/path/to/data
```

## Prerequisites

- Python 3.9+
- Access to Visable Jira + Confluence (Atlassian MCP or API)
- Status Time Free plugin export access

## Documentation

- [SKILL.md](SKILL.md) — workflow checklist and Confluence structure
- [reference.md](reference.md) — JQL, custom fields, ADF patterns, measurement rules

## May 2026 reference page

https://visable.atlassian.net/wiki/spaces/PRODTECH/pages/179798040/May+2026+Productivity+Update

## License

Internal Visable tooling — share within the organisation.
