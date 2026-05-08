"""
Run the accessibility audit against a generated Inquiry Engine paper.

Usage:
    python tools/audit_accessibility.py data/outputs/sample_interactive_paper.html
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.html.accessibility_audit import (
    audit_accessibility_file,
    format_accessibility_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run accessibility audit."
    )

    parser.add_argument(
        "html_path",
        type=Path,
        help="Path to the generated HTML paper.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    report = audit_accessibility_file(args.html_path)
    print(format_accessibility_report(report))

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())