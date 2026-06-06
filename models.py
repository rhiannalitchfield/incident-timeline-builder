"""
Data models for incident timeline events.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(str, Enum):
    # Detection
    REPORT = "report"
    AUTO_FLAG = "auto_flag"
    PROACTIVE_DETECT = "proactive_detect"

    # Review
    REVIEW_START = "review_start"
    REVIEW_COMPLETE = "review_complete"
    ESCALATION = "escalation"
    DE_ESCALATION = "de_escalation"

    # Action
    WARN = "warn"
    RESTRICT = "restrict"
    SUSPEND = "suspend"
    BAN = "ban"
    CONTENT_REMOVE = "content_remove"
    CONTENT_RESTORE = "content_restore"

    # Resolution
    APPEAL_RECEIVED = "appeal_received"
    APPEAL_UPHELD = "appeal_upheld"
    APPEAL_DENIED = "appeal_denied"
    RESOLVED = "resolved"
    CLOSED = "closed"

    # Communication
    USER_NOTIFIED = "user_notified"
    EXTERNAL_REPORT = "external_report"
    LAW_ENFORCEMENT = "law_enforcement"

    # Other
    NOTE = "note"
    OTHER = "other"


ESCALATION_EVENTS = {EventType.ESCALATION, EventType.BAN, EventType.SUSPEND, EventType.LAW_ENFORCEMENT}
RESOLUTION_EVENTS = {EventType.RESOLVED, EventType.CLOSED, EventType.APPEAL_UPHELD, EventType.APPEAL_DENIED}
ACTION_EVENTS = {EventType.WARN, EventType.RESTRICT, EventType.SUSPEND, EventType.BAN, EventType.CONTENT_REMOVE}


@dataclass
class IncidentEvent:
    timestamp: datetime
    event_type: EventType
    actor: str                          # who triggered the event (user, agent, system)
    description: str
    severity: Optional[Severity] = None
    case_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def is_escalation(self) -> bool:
        return self.event_type in ESCALATION_EVENTS

    @property
    def is_resolution(self) -> bool:
        return self.event_type in RESOLUTION_EVENTS

    @property
    def is_action(self) -> bool:
        return self.event_type in ACTION_EVENTS
