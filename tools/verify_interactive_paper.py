"""
One-command verification flow for the interactive sample paper.

Steps:
1) Generate the sample interactive paper.
2) Run HTML integrity checks.
3) Run accessibility audit.
4) Optionally run browser behavior tests.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.html.accessibility_audit import audit_accessibility_file, format_accessibility_report  # noqa: E402
from src.html.html_integrity import check_html_integrity_file, format_integrity_report  # noqa: E402
from src.html.paper_assembler import write_html_paper  # noqa: E402
from tools.generate_sample_paper import build_sample_document  # noqa: E402


DEFAULT_OUTPUT_PATH = Path("data/outputs/sample_interactive_paper.html")
DEFAULT_BROWSER_TEST_PATH = Path("tests/test_browser_behavior.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run interactive paper verification in one command."
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path where the generated sample paper will be written.",
    )
    parser.add_argument(
        "--allow-missing-components",
        action="store_true",
        help="Allow integrity checks to pass without component markers.",
    )
    parser.add_argument(
        "--run-browser-tests",
        action="store_true",
        help="Run browser behavior tests after static checks pass.",
    )
    parser.add_argument(
        "--browser-test-path",
        type=Path,
        default=DEFAULT_BROWSER_TEST_PATH,
        help="Pytest path for browser checks when --run-browser-tests is enabled.",
    )
    return parser.parse_args()


def _run_browser_tests(test_path: Path) -> bool:
    print(f"[4/4] Running browser tests: {test_path}")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_path)],
        cwd=str(PROJECT_ROOT),
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    args = parse_args()

    print(f"[1/4] Generating sample interactive paper -> {args.output_path}")
    generated_path = write_html_paper(build_sample_document(), args.output_path)

    print("[2/4] Running HTML integrity check")
    integrity_report = check_html_integrity_file(
        generated_path,
        require_components=not args.allow_missing_components,
    )
    print(format_integrity_report(integrity_report))

    print("[3/4] Running accessibility audit")
    accessibility_report = audit_accessibility_file(generated_path)
    print(format_accessibility_report(accessibility_report))

    if not integrity_report.passed or not accessibility_report.passed:
        return 1

    if args.run_browser_tests and not _run_browser_tests(args.browser_test_path):
        return 1

    print("Interactive paper verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
