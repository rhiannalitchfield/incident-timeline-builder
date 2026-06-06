"""
incident-timeline-builder
A Trust & Safety tool for building structured incident timelines
with escalation detection, response lag analysis, and summary reporting.
"""

from .loader import load_events
from .timeline import Timeline
from .report import generate_report

__version__ = "0.1.0"
__all__ = ["load_events", "Timeline", "generate_report"]
