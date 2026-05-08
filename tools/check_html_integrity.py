"""
Check a generated interactive Inquiry Engine HTML paper.

Usage:
    python tools/check_html_integrity.py data/outputs/sample_interactive_paper.html
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.html.html_integrity import (  # noqa: E402
    check_html_integrity_file,
    format_integrity_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check generated interactive HTML integrity."
    )

    parser.add_argument(
        "html_path",
        type=Path,
        help="Path to the generated HTML paper.",
    )

    parser.add_argument(
        "--allow-missing-components",
        action="store_true",
        help=(
            "Allow generated HTML without claim-card, evidence-panel, "
            "or reading-list component markers."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    report = check_html_integrity_file(
        args.html_path,
        require_components=not args.allow_missing_components,
    )

    print(format_integrity_report(report))

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
