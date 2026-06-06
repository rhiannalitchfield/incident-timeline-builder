"""
Loaders for incident event data from CSV and JSON sources.
"""

from __future__ import annotations
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Union

from .models import IncidentEvent, EventType, Severity


DATETIME_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
]


def _parse_datetime(value: str) -> datetime:
    value = value.strip()
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(
        f"Cannot parse datetime '{value}'. "
        f"Supported formats: {', '.join(DATETIME_FORMATS)}"
    )


def _parse_event_type(value: str) -> EventType:
    try:
        return EventType(value.lower().strip())
    except ValueError:
        return EventType.OTHER


def _parse_severity(value: str) -> Union[Severity, None]:
    if not value or value.strip() == "":
        return None
    try:
        return Severity(value.lower().strip())
    except ValueError:
        return None


def _parse_tags(value: str) -> list[str]:
    if not value or value.strip() == "":
        return []
    return [t.strip() for t in value.split("|") if t.strip()]


def _row_to_event(row: dict) -> IncidentEvent:
    """Convert a flat dict (from CSV or JSON) to an IncidentEvent."""
    required = {"timestamp", "event_type", "actor", "description"}
    missing = required - set(row.keys())
    if missing:
        raise ValueError(f"Row is missing required fields: {missing}")

    # Pull known fields, pass remainder as metadata
    known = {"timestamp", "event_type", "actor", "description", "severity", "case_id", "tags"}
    metadata = {k: v for k, v in row.items() if k not in known and v}

    return IncidentEvent(
        timestamp=_parse_datetime(row["timestamp"]),
        event_type=_parse_event_type(row["event_type"]),
        actor=row["actor"].strip(),
        description=row["description"].strip(),
        severity=_parse_severity(row.get("severity", "")),
        case_id=row.get("case_id", "").strip() or None,
        tags=_parse_tags(row.get("tags", "")),
        metadata=metadata,
    )


def load_csv(path: Union[str, Path]) -> list[IncidentEvent]:
    """Load events from a CSV file.

    Required columns: timestamp, event_type, actor, description
    Optional columns: severity, case_id, tags (pipe-separated)
    Any extra columns are stored in event.metadata.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    events = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # start=2 because row 1 is header
            try:
                events.append(_row_to_event(dict(row)))
            except (ValueError, KeyError) as e:
                raise ValueError(f"Error parsing CSV row {i}: {e}") from e

    return events


def load_json(path: Union[str, Path]) -> list[IncidentEvent]:
    """Load events from a JSON file (list of event objects)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("JSON file must contain a top-level array of event objects.")

    events = []
    for i, item in enumerate(data):
        try:
            events.append(_row_to_event(item))
        except (ValueError, KeyError) as e:
            raise ValueError(f"Error parsing JSON item {i}: {e}") from e

    return events


def load_events(path: Union[str, Path]) -> list[IncidentEvent]:
    """Auto-detect format (CSV or JSON) and load events from file."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return load_csv(path)
    elif suffix == ".json":
        return load_json(path)
    else:
        raise ValueError(f"Unsupported file format '{suffix}'. Use .csv or .json.")
