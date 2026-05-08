from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional


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
            f"Command failed with exit code {result.returncode}: {' '.join(command)}"
        )


def assert_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Expected output was not created: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an end-to-end evaluation smoke test."
    )

    parser.add_argument(
        "--output-dir",
        default="data/outputs/smoke_evaluation",
        help="Directory where smoke test artifacts should be written.",
    )

    parser.add_argument(
        "--run-id",
        default="smoke_evaluation_001",
        help="Run ID to store in evaluation metadata.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paper_artifact_path = output_dir / "sample_paper_artifact.json"
    audit_report_path = output_dir / "audit_report.json"
    audit_summary_path = output_dir / "audit_summary.md"
    manifest_path = output_dir / "evaluation_manifest.json"
    artifact_index_path = output_dir / "evaluation_artifact_index.json"

    run_command(
        [
            sys.executable,
            "-m",
            "src.evaluation.sample_artifact_cli",
            "--output",
            str(paper_artifact_path),
            "--publishable",
        ]
    )

    run_command(
        [
            sys.executable,
            "main.py",
            "--stage",
            "evaluation",
            "--paper-artifact",
            str(paper_artifact_path),
            "--audit-report",
            str(audit_report_path),
            "--audit-summary",
            str(audit_summary_path),
            "--manifest",
            str(manifest_path),
            "--artifact-index",
            str(artifact_index_path),
            "--run-id",
            args.run_id,
            "--print-summary",
        ]
    )

    assert_exists(paper_artifact_path)
    assert_exists(audit_report_path)
    assert_exists(audit_summary_path)
    assert_exists(manifest_path)
    assert_exists(artifact_index_path)

    print("Smoke evaluation passed.")
    print(f"Output directory: {output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())