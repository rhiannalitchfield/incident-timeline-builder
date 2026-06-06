"""
CLI for incident-timeline-builder.

Usage:
    python -m incident_timeline.cli events.csv
    python -m incident_timeline.cli events.json --format json --output report.json
    python -m incident_timeline.cli events.csv --case INC-001
    python -m incident_timeline.cli events.csv --severity high
"""

import argparse
import sys
from pathlib import Path

from .loader import load_events
from .timeline import Timeline
from .report import generate_report
from .models import Severity


def main():
    parser = argparse.ArgumentParser(
        prog="incident-timeline",
        description="Build and analyze Trust & Safety incident timelines.",
    )
    parser.add_argument("input", help="Path to CSV or JSON events file")
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Write report to this file path (default: stdout)",
    )
    parser.add_argument(
        "--case",
        help="Filter to a specific case ID",
    )
    parser.add_argument(
        "--severity",
        choices=[s.value for s in Severity],
        help="Filter to a specific severity level",
    )
    parser.add_argument(
        "--actor",
        help="Filter to a specific actor",
    )
    parser.add_argument(
        "--title",
        default="Incident Timeline Report",
        help="Report title",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print only the summary stats, no full timeline",
    )

    args = parser.parse_args()

    # Load
    try:
        events = load_events(args.input)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error loading events: {e}", file=sys.stderr)
        sys.exit(1)

    if not events:
        print("No events found in input file.", file=sys.stderr)
        sys.exit(1)

    # Build timeline
    tl = Timeline(events)

    # Apply filters
    if args.case:
        tl = tl.by_case(args.case)
        if not tl.events:
            print(f"No events found for case '{args.case}'.", file=sys.stderr)
            sys.exit(1)

    if args.severity:
        tl = tl.by_severity(Severity(args.severity))
        if not tl.events:
            print(f"No events found with severity '{args.severity}'.", file=sys.stderr)
            sys.exit(1)

    if args.actor:
        tl = tl.by_actor(args.actor)
        if not tl.events:
            print(f"No events found for actor '{args.actor}'.", file=sys.stderr)
            sys.exit(1)

    # Summary only mode
    if args.summary_only:
        import json
        print(json.dumps(tl.summary(), indent=2))
        sys.exit(0)

    # Generate and output report
    report = generate_report(
        tl,
        title=args.title,
        output_path=args.output,
        fmt=args.format,
    )

    if args.output:
        print(f"Report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
