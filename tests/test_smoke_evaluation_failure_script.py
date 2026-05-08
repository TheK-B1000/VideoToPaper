import json
import subprocess
from pathlib import Path

import pytest

from scripts.smoke_evaluation_failure import (
    assert_exists,
    assert_not_exists,
    main,
    run_command_expect_failure,
    run_command_expect_success,
)


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


def test_run_command_expect_success_raises_for_failed_command():
    with pytest.raises(RuntimeError):
        run_command_expect_success(["python", "-c", "raise SystemExit(3)"])


def test_run_command_expect_failure_accepts_failed_command():
    result = run_command_expect_failure(["python", "-c", "raise SystemExit(3)"])

    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 3


def test_run_command_expect_failure_raises_for_successful_command():
    with pytest.raises(RuntimeError):
        run_command_expect_failure(["python", "-c", "raise SystemExit(0)"])


def test_negative_smoke_evaluation_script_runs_end_to_end(tmp_path):
    output_dir = tmp_path / "negative_smoke"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--run-id",
            "negative_smoke_test_001",
        ]
    )

    assert exit_code == 0

    audit_report_path = output_dir / "bad_audit_report.json"
    audit_summary_path = output_dir / "bad_audit_summary.md"
    manifest_path = output_dir / "bad_evaluation_manifest.json"
    artifact_index_path = output_dir / "bad_evaluation_artifact_index.json"

    assert audit_report_path.exists()
    assert audit_summary_path.exists()
    assert manifest_path.exists()
    assert artifact_index_path.exists()

    audit_payload = json.loads(audit_report_path.read_text(encoding="utf-8"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    index_payload = json.loads(artifact_index_path.read_text(encoding="utf-8"))

    assert audit_payload["publishable"] is False
    assert audit_payload["publishability_decision"]["publishable"] is False
    assert "evidence_balance" in audit_payload["publishability_decision"]["blocking_axes"]
    assert "citation_integrity" in audit_payload["publishability_decision"]["blocking_axes"]
    assert "clip_anchor_accuracy" in audit_payload["publishability_decision"]["blocking_axes"]

    assert manifest_payload["publishable"] is False
    assert manifest_payload["metadata"]["run_id"] == "negative_smoke_test_001"

    assert index_payload["valid"] is True
    assert index_payload["publishable"] is False