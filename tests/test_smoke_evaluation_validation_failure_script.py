import json
import subprocess
from pathlib import Path

import pytest

from scripts.smoke_evaluation_validation_failure import (
    assert_exists,
    assert_not_exists,
    main,
    run_command_expect_failure,
    write_malformed_artifact,
)


def test_write_malformed_artifact_creates_invalid_artifact(tmp_path):
    output_path = tmp_path / "malformed_paper_artifact.json"

    written_path = write_malformed_artifact(output_path)

    assert written_path == output_path
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["claims"][0]["claim_id"] == "claim_001"
    assert "anchor_clip" not in payload["claims"][0]


def test_assert_exists_accepts_existing_file(tmp_path):
    path = tmp_path / "artifact.json"
    path.write_text("{}", encoding="utf-8")

    assert_exists(path)


def test_assert_exists_raises_for_missing_file(tmp_path):
    missing_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        assert_exists(missing_path)


def test_assert_not_exists_accepts_missing_file(tmp_path):
    missing_path = tmp_path / "missing.json"

    assert_not_exists(missing_path)


def test_assert_not_exists_raises_for_existing_file(tmp_path):
    path = tmp_path / "artifact.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(AssertionError):
        assert_not_exists(path)


def test_run_command_expect_failure_accepts_failed_command():
    result = run_command_expect_failure(["python", "-c", "raise SystemExit(3)"])

    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 3


def test_run_command_expect_failure_raises_for_successful_command():
    with pytest.raises(RuntimeError):
        run_command_expect_failure(["python", "-c", "raise SystemExit(0)"])


def test_malformed_artifact_smoke_script_runs_end_to_end(tmp_path):
    output_dir = tmp_path / "validation_failure_smoke"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--run-id",
            "validation_failure_smoke_test_001",
        ]
    )

    assert exit_code == 0

    audit_report_path = output_dir / "audit_report.json"
    audit_summary_path = output_dir / "audit_summary.md"
    manifest_path = output_dir / "evaluation_manifest.json"
    validation_report_path = output_dir / "validation_report.json"
    validation_summary_path = output_dir / "validation_summary.md"
    artifact_index_path = output_dir / "evaluation_artifact_index.json"

    assert not audit_report_path.exists()
    assert not audit_summary_path.exists()
    assert not manifest_path.exists()

    assert validation_report_path.exists()
    assert validation_summary_path.exists()
    assert artifact_index_path.exists()

    validation_payload = json.loads(validation_report_path.read_text(encoding="utf-8"))
    validation_summary = validation_summary_path.read_text(encoding="utf-8")
    index_payload = json.loads(artifact_index_path.read_text(encoding="utf-8"))

    assert validation_payload["valid"] is False
    assert "claims[0] is missing anchor_clip." in validation_payload["errors"]

    assert "# Paper Artifact Validation Summary" in validation_summary
    assert "**Valid:** FAIL" in validation_summary

    assert index_payload["valid"] is False
    assert index_payload["publishable"] is None
    assert index_payload["audit_report_path"] is None
    assert index_payload["validation_report_path"] == str(validation_report_path)