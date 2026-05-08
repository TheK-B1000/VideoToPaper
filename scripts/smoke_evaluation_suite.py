from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional

from scripts.smoke_evaluation_suite_summary import write_suite_summary


def run_command(command: list[str]) -> None:
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"Smoke command failed with exit code {result.returncode}: {' '.join(command)}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the complete evaluation smoke test suite."
    )

    parser.add_argument(
        "--output-dir",
        default="data/outputs/smoke_evaluation_suite",
        help="Directory where smoke suite artifacts should be written.",
    )

    parser.add_argument(
        "--run-prefix",
        default="evaluation_suite",
        help="Prefix used for run IDs written into smoke artifacts.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    passing_output_dir = output_dir / "passing"
    unpublishable_output_dir = output_dir / "unpublishable"
    malformed_output_dir = output_dir / "malformed"

    run_command(
        [
            sys.executable,
            "scripts/smoke_evaluation.py",
            "--output-dir",
            str(passing_output_dir),
            "--run-id",
            f"{args.run_prefix}_passing",
        ]
    )

    run_command(
        [
            sys.executable,
            "scripts/smoke_evaluation_failure.py",
            "--output-dir",
            str(unpublishable_output_dir),
            "--run-id",
            f"{args.run_prefix}_unpublishable",
        ]
    )

    run_command(
        [
            sys.executable,
            "scripts/smoke_evaluation_validation_failure.py",
            "--output-dir",
            str(malformed_output_dir),
            "--run-id",
            f"{args.run_prefix}_malformed",
        ]
    )

    summary_path = output_dir / "summary.md"
    write_suite_summary(
        output_dir=output_dir,
        summary_path=summary_path,
    )

    print(f"Smoke suite summary written to: {summary_path}")
    print("Evaluation smoke suite passed.")
    print(f"Output directory: {output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())