"""
Core Timeline class: sorts events, detects escalations, and computes response lag stats.
"""

from __future__ import annotations
from datetime import timedelta
from typing import Optional
from collections import defaultdict

from .models import IncidentEvent, EventType, Severity, ESCALATION_EVENTS, RESOLUTION_EVENTS


class ResponseLag:
    """Captures the time gap between two events in the timeline."""

    def __init__(self, label: str, from_event: IncidentEvent, to_event: IncidentEvent):
        self.label = label
        self.from_event = from_event
        self.to_event = to_event
        self.duration: timedelta = to_event.timestamp - from_event.timestamp

    @property
    def seconds(self) -> float:
        return self.duration.total_seconds()

    @property
    def human(self) -> str:
        total = int(self.duration.total_seconds())
        if total < 0:
            return f"-{_fmt_seconds(-total)}"
        return _fmt_seconds(total)

    def __repr__(self):
        return f"ResponseLag(label={self.label!r}, duration={self.human!r})"


def _fmt_seconds(total: int) -> str:
    if total < 60:
        return f"{total}s"
    elif total < 3600:
        m, s = divmod(total, 60)
        return f"{m}m {s}s"
    elif total < 86400:
        h, remainder = divmod(total, 3600)
        m = remainder // 60
        return f"{h}h {m}m"
    else:
        d, remainder = divmod(total, 86400)
        h = remainder // 3600
        return f"{d}d {h}h"


class Timeline:
    """
    Wraps a list of IncidentEvents and provides:
    - Chronological ordering
    - Escalation point detection
    - Response lag computation (time-to-first-action, time-to-resolution, etc.)
    - Per-case grouping
    - Summary statistics
    """

    def __init__(self, events: list[IncidentEvent]):
        self.events: list[IncidentEvent] = sorted(events, key=lambda e: e.timestamp)

    # ------------------------------------------------------------------
    # Basic accessors
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self):
        return iter(self.events)

    @property
    def start(self) -> Optional[IncidentEvent]:
        return self.events[0] if self.events else None

    @property
    def end(self) -> Optional[IncidentEvent]:
        return self.events[-1] if self.events else None

    @property
    def total_duration(self) -> Optional[timedelta]:
        if len(self.events) < 2:
            return None
        return self.end.timestamp - self.start.timestamp

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def by_case(self, case_id: str) -> "Timeline":
        """Return a sub-timeline for a single case."""
        return Timeline([e for e in self.events if e.case_id == case_id])

    def by_severity(self, severity: Severity) -> "Timeline":
        return Timeline([e for e in self.events if e.severity == severity])

    def by_type(self, *event_types: EventType) -> "Timeline":
        return Timeline([e for e in self.events if e.event_type in event_types])

    def by_actor(self, actor: str) -> "Timeline":
        return Timeline([e for e in self.events if e.actor == actor])

    def with_tag(self, tag: str) -> "Timeline":
        return Timeline([e for e in self.events if tag in e.tags])

    # ------------------------------------------------------------------
    # Escalation detection
    # ------------------------------------------------------------------

    @property
    def escalation_points(self) -> list[IncidentEvent]:
        """Return all events that represent an escalation."""
        return [e for e in self.events if e.is_escalation]

    @property
    def resolution_points(self) -> list[IncidentEvent]:
        return [e for e in self.events if e.is_resolution]

    def escalation_rate(self) -> float:
        """Fraction of events that are escalations."""
        if not self.events:
            return 0.0
        return len(self.escalation_points) / len(self.events)

    # ------------------------------------------------------------------
    # Response lag analysis
    # ------------------------------------------------------------------

    def time_to_first_action(self) -> Optional[ResponseLag]:
        """Time from first event to first action (warn/restrict/remove/etc)."""
        first = self.start
        action = next((e for e in self.events if e.is_action), None)
        if first and action and first != action:
            return ResponseLag("time_to_first_action", first, action)
        return None

    def time_to_first_escalation(self) -> Optional[ResponseLag]:
        first = self.start
        esc = next((e for e in self.events if e.is_escalation), None)
        if first and esc and first != esc:
            return ResponseLag("time_to_first_escalation", first, esc)
        return None

    def time_to_resolution(self) -> Optional[ResponseLag]:
        first = self.start
        res = next((e for e in self.events if e.is_resolution), None)
        if first and res and first != res:
            return ResponseLag("time_to_resolution", first, res)
        return None

    def review_lag(self) -> Optional[ResponseLag]:
        """Time from first report/flag to review start."""
        detect = next(
            (e for e in self.events if e.event_type in {EventType.REPORT, EventType.AUTO_FLAG, EventType.PROACTIVE_DETECT}),
            None
        )
        review = next((e for e in self.events if e.event_type == EventType.REVIEW_START), None)
        if detect and review:
            return ResponseLag("review_lag", detect, review)
        return None

    def all_lags(self) -> list[ResponseLag]:
        lags = [
            self.time_to_first_action(),
            self.time_to_first_escalation(),
            self.time_to_resolution(),
            self.review_lag(),
        ]
        return [l for l in lags if l is not None]

    # ------------------------------------------------------------------
    # Grouping & aggregation
    # ------------------------------------------------------------------

    def group_by_case(self) -> dict[str, "Timeline"]:
        """Return a dict of case_id → Timeline for events that have a case_id."""
        groups: dict[str, list[IncidentEvent]] = defaultdict(list)
        for e in self.events:
            key = e.case_id or "__unassigned__"
            groups[key].append(e)
        return {k: Timeline(v) for k, v in groups.items()}

    def group_by_actor(self) -> dict[str, "Timeline"]:
        groups: dict[str, list[IncidentEvent]] = defaultdict(list)
        for e in self.events:
            groups[e.actor].append(e)
        return {k: Timeline(v) for k, v in groups.items()}

    def event_type_counts(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for e in self.events:
            counts[e.event_type.value] += 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def severity_counts(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for e in self.events:
            key = e.severity.value if e.severity else "unset"
            counts[key] += 1
        return dict(counts)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        lags = self.all_lags()
        return {
            "total_events": len(self.events),
            "unique_cases": len({e.case_id for e in self.events if e.case_id}),
            "unique_actors": len({e.actor for e in self.events}),
            "escalation_count": len(self.escalation_points),
            "resolution_count": len(self.resolution_points),
            "total_duration": str(self.total_duration) if self.total_duration else None,
            "event_type_counts": self.event_type_counts(),
            "severity_counts": self.severity_counts(),
            "lags": {l.label: l.human for l in lags},
        }
