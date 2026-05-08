from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


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


def write_malformed_artifact(output_path: Path) -> Path:
    """
    Write a structurally invalid paper artifact.

    This artifact is intentionally missing the claim anchor_clip, which should
    cause validation to fail before evaluation produces audit artifacts.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    artifact = {
        "claims": [
            {
                "claim_id": "claim_001",
                "verbatim_quote": "Balanced evidence matters.",
            }
        ],
        "speaker_perspective": {
            "expected_qualifications": ["the literature may be mixed"],
            "qualifications_preserved": ["the literature may be mixed"],
            "narrative_blocks": [
                {
                    "assertions": [
                        {
                            "text": "The speaker presents a claim that requires evidence.",
                            "hedge_drift_detected": False,
                        }
                    ],
                    "verbatim_anchors": ["claim_001"],
                }
            ],
        },
        "adjudications": [
            {
                "claim_id": "claim_001",
                "balance_score": "balanced",
                "verdict": "well_supported_with_qualifications",
            }
        ],
        "evidence_records": [
            {
                "evidence_record_id": "evidence_001",
                "identifier": "10.1234/example",
                "url": "https://example.com/paper",
            }
        ],
        "references": [
            {
                "evidence_record_id": "evidence_001",
                "identifier": "10.1234/example",
                "url": "https://example.com/paper",
            }
        ],
        "rendered_clips": [
            {
                "claim_id": "claim_001",
                "start": 10.0,
                "end": 20.0,
            }
        ],
    }

    output_path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a malformed-artifact evaluation smoke test."
    )

    parser.add_argument(
        "--output-dir",
        default="data/outputs/smoke_evaluation_validation_failure",
        help="Directory where validation-failure smoke test artifacts should be written.",
    )

    parser.add_argument(
        "--run-id",
        default="smoke_evaluation_validation_failure_001",
        help="Run ID to store in evaluation metadata.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paper_artifact_path = output_dir / "malformed_paper_artifact.json"
    audit_report_path = output_dir / "audit_report.json"
    audit_summary_path = output_dir / "audit_summary.md"
    manifest_path = output_dir / "evaluation_manifest.json"
    validation_report_path = output_dir / "validation_report.json"
    validation_summary_path = output_dir / "validation_summary.md"
    artifact_index_path = output_dir / "evaluation_artifact_index.json"

    write_malformed_artifact(paper_artifact_path)

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
            "--validation-report",
            str(validation_report_path),
            "--validation-summary",
            str(validation_summary_path),
            "--artifact-index",
            str(artifact_index_path),
            "--run-id",
            args.run_id,
            "--print-validation-summary",
        ]
    )

    assert_exists(paper_artifact_path)
    assert_exists(validation_report_path)
    assert_exists(validation_summary_path)
    assert_exists(artifact_index_path)

    assert_not_exists(audit_report_path)
    assert_not_exists(audit_summary_path)
    assert_not_exists(manifest_path)

    validation_payload = json.loads(validation_report_path.read_text(encoding="utf-8"))
    index_payload = json.loads(artifact_index_path.read_text(encoding="utf-8"))

    if validation_payload.get("valid") is not False:
        raise AssertionError("Expected validation report to mark artifact as invalid.")

    if "claims[0] is missing anchor_clip." not in validation_payload.get("errors", []):
        raise AssertionError("Expected validation report to include missing anchor_clip error.")

    if index_payload.get("valid") is not False:
        raise AssertionError("Expected artifact index to mark artifact as invalid.")

    if index_payload.get("publishable") is not None:
        raise AssertionError(
            "Expected artifact index publishable value to remain null when validation fails."
        )

    print("Malformed artifact smoke evaluation passed.")
    print(f"Output directory: {output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())