from __future__ import annotations

import argparse
import json
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
        description="Run an export-and-evaluate smoke test using assembler-style fixtures."
    )

    parser.add_argument(
        "--output-dir",
        default="data/outputs/smoke_export_and_evaluate",
        help="Directory where smoke test artifacts should be written.",
    )

    parser.add_argument(
        "--run-id",
        default="smoke_export_and_evaluate_001",
        help="Run ID to store in evaluation metadata.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    claims_path = output_dir / "claims.json"
    speaker_path = output_dir / "speaker_perspective.json"
    adjudications_path = output_dir / "adjudications.json"
    evidence_path = output_dir / "evidence_records.json"

    paper_artifact_path = output_dir / "paper_artifact.json"
    audit_report_path = output_dir / "audit_report.json"
    audit_summary_path = output_dir / "audit_summary.md"
    manifest_path = output_dir / "evaluation_manifest.json"
    artifact_index_path = output_dir / "evaluation_artifact_index.json"

    run_command(
        [
            sys.executable,
            "main.py",
            "--stage",
            "assembler_fixture",
            "--output-dir",
            str(output_dir),
        ]
    )

    run_command(
        [
            sys.executable,
            "main.py",
            "--stage",
            "export_and_evaluate",
            "--claims",
            str(claims_path),
            "--speaker-perspective",
            str(speaker_path),
            "--adjudications",
            str(adjudications_path),
            "--evidence-records",
            str(evidence_path),
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

    expected_outputs = [
        claims_path,
        speaker_path,
        adjudications_path,
        evidence_path,
        paper_artifact_path,
        audit_report_path,
        audit_summary_path,
        manifest_path,
        artifact_index_path,
    ]

    for path in expected_outputs:
        assert_exists(path)

    audit_payload = json.loads(audit_report_path.read_text(encoding="utf-8"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    index_payload = json.loads(artifact_index_path.read_text(encoding="utf-8"))

    if audit_payload.get("publishable") is not True:
        raise AssertionError("Expected exported assembler fixture to be publishable.")

    if manifest_payload.get("metadata", {}).get("run_id") != args.run_id:
        raise AssertionError("Expected manifest to include the requested run_id.")

    if index_payload.get("valid") is not True:
        raise AssertionError("Expected artifact index to mark artifact as valid.")

    if index_payload.get("publishable") is not True:
        raise AssertionError("Expected artifact index to mark artifact as publishable.")

    print("Export-and-evaluate smoke test passed.")
    print(f"Output directory: {output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
