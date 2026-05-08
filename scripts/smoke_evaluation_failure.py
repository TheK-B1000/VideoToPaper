from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_command_expect_success(command: list[str]) -> None:
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
            f"Expected command to pass, but it failed with exit code "
            f"{result.returncode}: {' '.join(command)}"
        )


def run_command_expect_failure(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode == 0:
        raise RuntimeError(
            f"Expected command to fail, but it passed: {' '.join(command)}"
        )

    return result


def assert_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Expected output was not created: {path}")


def assert_not_exists(path: Path) -> None:
    if path.exists():
        raise AssertionError(f"Output should not have been created: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a negative evaluation smoke test."
    )

    parser.add_argument(
        "--output-dir",
        default="data/outputs/smoke_evaluation_failure",
        help="Directory where negative smoke test artifacts should be written.",
    )

    parser.add_argument(
        "--run-id",
        default="smoke_evaluation_failure_001",
        help="Run ID to store in evaluation metadata.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paper_artifact_path = output_dir / "bad_sample_paper_artifact.json"
    audit_report_path = output_dir / "bad_audit_report.json"
    audit_summary_path = output_dir / "bad_audit_summary.md"
    manifest_path = output_dir / "bad_evaluation_manifest.json"
    artifact_index_path = output_dir / "bad_evaluation_artifact_index.json"

    run_command_expect_success(
        [
            sys.executable,
            "-m",
            "src.evaluation.sample_artifact_cli",
            "--output",
            str(paper_artifact_path),
            "--unpublishable",
        ]
    )

    run_command_expect_failure(
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

    audit_payload = json.loads(audit_report_path.read_text(encoding="utf-8"))
    index_payload = json.loads(artifact_index_path.read_text(encoding="utf-8"))

    if audit_payload.get("publishable") is not False:
        raise AssertionError("Expected audit report to mark artifact as not publishable.")

    if index_payload.get("publishable") is not False:
        raise AssertionError("Expected artifact index to mark artifact as not publishable.")

    if index_payload.get("valid") is not True:
        raise AssertionError(
            "Expected artifact structure to be valid even though publishability failed."
        )

    print("Negative smoke evaluation passed.")
    print(f"Output directory: {output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())