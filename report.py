"""
Report generation: produces structured text and JSON summaries from a Timeline.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Union, Optional

from .timeline import Timeline
from .models import Severity


SEVERITY_ORDER = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]
SEVERITY_LABELS = {
    Severity.CRITICAL: "🔴 CRITICAL",
    Severity.HIGH:     "🟠 HIGH",
    Severity.MEDIUM:   "🟡 MEDIUM",
    Severity.LOW:      "🟢 LOW",
    None:              "⚪ UNSET",
}


def _bar(value: int, total: int, width: int = 20) -> str:
    filled = round((value / total) * width) if total else 0
    return "█" * filled + "░" * (width - filled)


def generate_report(
    timeline: Timeline,
    title: str = "Incident Timeline Report",
    output_path: Optional[Union[str, Path]] = None,
    fmt: str = "text",
) -> str:
    """
    Generate a report from a Timeline.

    Args:
        timeline: A Timeline instance.
        title: Report title string.
        output_path: Optional file path to write the report to.
        fmt: "text" for a plain-text report, "json" for structured JSON.

    Returns:
        The report as a string.
    """
    if fmt == "json":
        report = _json_report(timeline, title)
    else:
        report = _text_report(timeline, title)

    if output_path:
        path = Path(output_path)
        path.write_text(report, encoding="utf-8")

    return report


def _json_report(timeline: Timeline, title: str) -> str:
    summary = timeline.summary()
    events = [
        {
            "timestamp": e.timestamp.isoformat(),
            "event_type": e.event_type.value,
            "actor": e.actor,
            "description": e.description,
            "severity": e.severity.value if e.severity else None,
            "case_id": e.case_id,
            "tags": e.tags,
            "is_escalation": e.is_escalation,
            "is_resolution": e.is_resolution,
            "is_action": e.is_action,
        }
        for e in timeline
    ]
    payload = {
        "title": title,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "summary": summary,
        "events": events,
    }
    return json.dumps(payload, indent=2)


def _text_report(timeline: Timeline, title: str) -> str:
    lines = []
    sep = "=" * 60
    thin = "-" * 60

    lines.append(sep)
    lines.append(f"  {title}")
    lines.append(f"  Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(sep)

    summary = timeline.summary()

    # -- Overview --
    lines.append("\n[ OVERVIEW ]")
    lines.append(f"  Total events    : {summary['total_events']}")
    lines.append(f"  Unique cases    : {summary['unique_cases']}")
    lines.append(f"  Unique actors   : {summary['unique_actors']}")
    lines.append(f"  Escalations     : {summary['escalation_count']}")
    lines.append(f"  Resolutions     : {summary['resolution_count']}")
    if summary["total_duration"]:
        lines.append(f"  Total duration  : {summary['total_duration']}")

    # -- Response Lags --
    if summary["lags"]:
        lines.append("\n[ RESPONSE LAGS ]")
        for label, human in summary["lags"].items():
            label_fmt = label.replace("_", " ").title()
            lines.append(f"  {label_fmt:<30} {human}")

    # -- Severity Breakdown --
    lines.append("\n[ SEVERITY BREAKDOWN ]")
    sev_counts = summary["severity_counts"]
    total = summary["total_events"]
    for sev in [*SEVERITY_ORDER, None]:
        key = sev.value if sev else "unset"
        count = sev_counts.get(key, 0)
        label = SEVERITY_LABELS[sev]
        bar = _bar(count, total)
        lines.append(f"  {label:<20} {bar}  {count}")

    # -- Event Type Breakdown --
    lines.append("\n[ EVENT TYPES ]")
    type_counts = summary["event_type_counts"]
    for etype, count in list(type_counts.items())[:15]:  # cap at 15 rows
        bar = _bar(count, total)
        lines.append(f"  {etype:<25} {bar}  {count}")

    # -- Escalation Points --
    escalations = timeline.escalation_points
    if escalations:
        lines.append("\n[ ESCALATION POINTS ]")
        for e in escalations:
            ts = e.timestamp.strftime("%Y-%m-%d %H:%M")
            sev = f"[{e.severity.value.upper()}]" if e.severity else ""
            case = f"(case: {e.case_id})" if e.case_id else ""
            lines.append(f"  {ts}  {e.event_type.value:<20}  {e.actor:<15}  {sev} {case}")
            lines.append(f"           {e.description}")

    # -- Full Chronological Timeline --
    lines.append("\n[ FULL TIMELINE ]")
    lines.append(thin)
    for e in timeline:
        ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        flags = []
        if e.is_escalation:
            flags.append("↑ ESCALATION")
        if e.is_resolution:
            flags.append("✓ RESOLUTION")
        if e.is_action:
            flags.append("⚡ ACTION")
        flag_str = "  " + "  ".join(flags) if flags else ""
        sev_str = f"[{e.severity.value.upper()}]" if e.severity else ""
        case_str = f"#{e.case_id}" if e.case_id else ""
        header = f"  {ts}  {e.event_type.value:<22} {sev_str:<12} {case_str}"
        lines.append(header + flag_str)
        lines.append(f"    Actor: {e.actor}")
        lines.append(f"    {e.description}")
        if e.tags:
            lines.append(f"    Tags: {', '.join(e.tags)}")
        lines.append("")

    lines.append(sep)
    lines.append("  END OF REPORT")
    lines.append(sep)

    return "\n".join(lines)
