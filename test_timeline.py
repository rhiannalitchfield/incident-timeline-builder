"""
Tests for incident-timeline-builder.
Run with: python -m pytest tests/ -v
"""

import pytest
from datetime import datetime, timedelta
from incident_timeline.models import IncidentEvent, EventType, Severity
from incident_timeline.timeline import Timeline
from incident_timeline.loader import load_csv
from incident_timeline.report import generate_report
from pathlib import Path


SAMPLE_CSV = Path(__file__).parent.parent / "examples" / "sample_events.csv"

BASE_TIME = datetime(2024, 1, 1, 12, 0, 0)

def make_event(event_type: EventType, minutes_offset: int = 0, severity=None, case_id=None, actor="agent:test"):
    return IncidentEvent(
        timestamp=BASE_TIME + timedelta(minutes=minutes_offset),
        event_type=event_type,
        actor=actor,
        description=f"Test event: {event_type.value}",
        severity=severity,
        case_id=case_id,
    )


class TestModels:
    def test_is_escalation(self):
        e = make_event(EventType.ESCALATION)
        assert e.is_escalation

    def test_is_resolution(self):
        e = make_event(EventType.RESOLVED)
        assert e.is_resolution

    def test_is_action(self):
        e = make_event(EventType.BAN)
        assert e.is_action

    def test_ban_is_escalation_and_action(self):
        e = make_event(EventType.BAN)
        assert e.is_escalation
        assert e.is_action

    def test_note_is_not_special(self):
        e = make_event(EventType.NOTE)
        assert not e.is_escalation
        assert not e.is_resolution
        assert not e.is_action


class TestTimeline:
    def setup_method(self):
        self.events = [
            make_event(EventType.REPORT, 0, Severity.HIGH, "INC-001"),
            make_event(EventType.REVIEW_START, 10, Severity.HIGH, "INC-001"),
            make_event(EventType.ESCALATION, 20, Severity.CRITICAL, "INC-001"),
            make_event(EventType.BAN, 30, Severity.CRITICAL, "INC-001"),
            make_event(EventType.RESOLVED, 60, Severity.MEDIUM, "INC-001"),
            make_event(EventType.REPORT, 0, Severity.LOW, "INC-002"),
            make_event(EventType.BAN, 5, Severity.LOW, "INC-002"),
            make_event(EventType.RESOLVED, 6, Severity.LOW, "INC-002"),
        ]
        self.tl = Timeline(self.events)

    def test_sorted_by_timestamp(self):
        ts = [e.timestamp for e in self.tl]
        assert ts == sorted(ts)

    def test_len(self):
        assert len(self.tl) == 8

    def test_escalation_points(self):
        # ESCALATION + BAN + BAN = 3 escalation events
        assert len(self.tl.escalation_points) == 3

    def test_resolution_points(self):
        assert len(self.tl.resolution_points) == 2

    def test_by_case(self):
        sub = self.tl.by_case("INC-001")
        assert len(sub) == 5
        assert all(e.case_id == "INC-001" for e in sub)

    def test_by_severity(self):
        sub = self.tl.by_severity(Severity.LOW)
        assert len(sub) == 3

    def test_time_to_resolution(self):
        lag = self.tl.by_case("INC-001").time_to_resolution()
        assert lag is not None
        assert lag.seconds == 60 * 60  # 60 minutes

    def test_time_to_first_action(self):
        sub = self.tl.by_case("INC-001")
        lag = sub.time_to_first_action()
        assert lag is not None
        assert lag.seconds == 30 * 60  # BAN is at +30 min

    def test_summary_keys(self):
        s = self.tl.summary()
        for key in ["total_events", "unique_cases", "unique_actors", "escalation_count", "lags"]:
            assert key in s

    def test_group_by_case(self):
        groups = self.tl.group_by_case()
        assert "INC-001" in groups
        assert "INC-002" in groups

    def test_event_type_counts(self):
        counts = self.tl.event_type_counts()
        assert counts["report"] == 2
        assert counts["ban"] == 2
        assert counts["resolved"] == 2


class TestLoader:
    def test_load_csv(self):
        if not SAMPLE_CSV.exists():
            pytest.skip("Sample CSV not found")
        events = load_csv(SAMPLE_CSV)
        assert len(events) > 0
        for e in events:
            assert isinstance(e.timestamp, datetime)
            assert isinstance(e.event_type, EventType)

    def test_load_csv_case_count(self):
        if not SAMPLE_CSV.exists():
            pytest.skip("Sample CSV not found")
        events = load_csv(SAMPLE_CSV)
        tl = Timeline(events)
        groups = tl.group_by_case()
        assert len(groups) == 3


class TestReport:
    def test_text_report_contains_overview(self):
        events = [
            make_event(EventType.REPORT, 0, Severity.HIGH, "INC-001"),
            make_event(EventType.BAN, 10, Severity.CRITICAL, "INC-001"),
            make_event(EventType.RESOLVED, 20, Severity.MEDIUM, "INC-001"),
        ]
        tl = Timeline(events)
        report = generate_report(tl, title="Test Report")
        assert "OVERVIEW" in report
        assert "ESCALATION POINTS" in report
        assert "FULL TIMELINE" in report

    def test_json_report_is_valid_json(self):
        import json
        events = [make_event(EventType.REPORT, 0, Severity.HIGH, "INC-001")]
        tl = Timeline(events)
        report = generate_report(tl, fmt="json")
        data = json.loads(report)
        assert "summary" in data
        assert "events" in data
