# incident-timeline-builder

A lightweight Python library and CLI for building structured **Trust & Safety incident timelines** — with escalation detection, response lag analysis, and summary reporting.

Built for T&S analysts, ops teams, and safety researchers who need to reconstruct, audit, and report on moderation incidents from structured event logs.

---

## Features

- **Load events** from CSV or JSON logs
- **Chronological timeline** with automatic sorting
- **Escalation detection** — flags events like bans, suspensions, law enforcement referrals
- **Response lag analysis** — time-to-first-action, time-to-escalation, time-to-resolution, review lag
- **Filtering** by case ID, severity, actor, event type, or tag
- **Grouping** by case or actor
- **Report generation** in plain text or JSON
- **CLI** for quick command-line use
- **Zero external dependencies** — pure Python 3.10+

---

## Installation

```bash
git clone https://github.com/rhiannalitchfield/incident-timeline-builder
cd incident-timeline-builder
pip install -e .
```

---

## Quick Start

### As a library

```python
from incident_timeline import load_events, Timeline, generate_report

# Load events from CSV or JSON
events = load_events("examples/sample_events.csv")

# Build timeline
tl = Timeline(events)

# Print summary
print(tl.summary())

# Filter to a single case
case = tl.by_case("INC-2024-001")

# Check response lags
print(case.time_to_resolution())   # ResponseLag(label='time_to_resolution', duration='1d 0h')
print(case.time_to_first_action()) # ResponseLag(label='time_to_first_action', duration='1h 10m')

# Generate a report
report = generate_report(case, title="INC-2024-001 Postmortem")
print(report)
```

### As a CLI

```bash
# Full text report to stdout
incident-timeline examples/sample_events.csv

# Filter to one case
incident-timeline examples/sample_events.csv --case INC-2024-001

# JSON output to file
incident-timeline examples/sample_events.csv --format json --output report.json

# Summary stats only
incident-timeline examples/sample_events.csv --summary-only

# Filter by severity
incident-timeline examples/sample_events.csv --severity critical
```

---

## Input Format

### CSV

Required columns: `timestamp`, `event_type`, `actor`, `description`  
Optional columns: `severity`, `case_id`, `tags` (pipe-separated)  
Any extra columns are stored as event metadata.

```csv
timestamp,event_type,actor,description,severity,case_id,tags
2024-03-15 08:02:11,report,user:alice,"User reported coordinated harassment",high,INC-001,harassment|coordinated
2024-03-15 09:14:01,escalation,agent:jsmith,"Escalating to senior review",high,INC-001,escalation
2024-03-15 14:02:55,ban,senior:cmendez,"Permanent ban applied",critical,INC-001,action
2024-03-15 16:22:00,resolved,agent:jsmith,"Case closed",medium,INC-001,
```

### JSON

A top-level array of event objects with the same fields:

```json
[
  {
    "timestamp": "2024-03-15T08:02:11",
    "event_type": "report",
    "actor": "user:alice",
    "description": "User reported coordinated harassment",
    "severity": "high",
    "case_id": "INC-001",
    "tags": "harassment|coordinated"
  }
]
```

---

## Supported Event Types

| Category    | Event Types |
|-------------|-------------|
| Detection   | `report`, `auto_flag`, `proactive_detect` |
| Review      | `review_start`, `review_complete`, `escalation`, `de_escalation` |
| Action      | `warn`, `restrict`, `suspend`, `ban`, `content_remove`, `content_restore` |
| Resolution  | `appeal_received`, `appeal_upheld`, `appeal_denied`, `resolved`, `closed` |
| Comms       | `user_notified`, `external_report`, `law_enforcement` |
| Other       | `note`, `other` |

---

## Severity Levels

`critical` · `high` · `medium` · `low`

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Example Output

```
============================================================
  Incident Timeline Report
  Generated: 2024-03-20 14:00 UTC
============================================================

[ OVERVIEW ]
  Total events    : 30
  Unique cases    : 3
  Unique actors   : 6
  Escalations     : 5
  Resolutions     : 3
  Total duration  : 8 days, 1:20:00

[ RESPONSE LAGS ]
  Time To First Action           1h 10m
  Time To First Escalation       1h 11m
  Time To Resolution             1d 0h

[ SEVERITY BREAKDOWN ]
  🔴 CRITICAL         ████████░░░░░░░░░░░░  8
  🟠 HIGH             ████░░░░░░░░░░░░░░░░  4
  🟡 MEDIUM           ████░░░░░░░░░░░░░░░░  4
  🟢 LOW              ████░░░░░░░░░░░░░░░░  4
```

---

## Project Structure

```
incident-timeline-builder/
├── incident_timeline/
│   ├── __init__.py       # Public API
│   ├── models.py         # IncidentEvent, EventType, Severity
│   ├── loader.py         # CSV + JSON loaders
│   ├── timeline.py       # Timeline analysis engine
│   ├── report.py         # Text + JSON report generation
│   └── cli.py            # Command-line interface
├── examples/
│   └── sample_events.csv
├── tests/
│   └── test_timeline.py
├── pyproject.toml
└── README.md
```

---

## Background

Built as part of a T&S tooling portfolio. Motivated by real-world moderation ops work where incident reconstruction, escalation auditing, and response lag reporting are common but underserved by general-purpose tooling.

Pairs well with the [refusal-eval-toolkit](https://github.com/nikkimusic34) for combined T&S + AI safety portfolio coverage.

---

## License

MIT
