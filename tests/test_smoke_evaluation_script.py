import json
import subprocess
from pathlib import Path

import pytest

from scripts.smoke_evaluation import assert_exists, main, run_command


def test_assert_exists_accepts_existing_file(tmp_path):
    path = tmp_path / "artifact.json"
    path.write_text("{}", encoding="utf-8")

    assert_exists(path)


def test_assert_exists_raises_for_missing_file(tmp_path):
    missing_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        assert_exists(missing_path)


def test_run_command_raises_for_failed_command():
    with pytest.raises(RuntimeError):
        run_command(["python", "-c", "raise SystemExit(3)"])


def test_smoke_evaluation_script_runs_end_to_end(tmp_path):
    output_dir = tmp_path / "smoke"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--run-id",
            "test_smoke_001",
        ]
    )

    assert exit_code == 0

    audit_report_path = output_dir / "audit_report.json"
    audit_summary_path = output_dir / "audit_summary.md"
    manifest_path = output_dir / "evaluation_manifest.json"
    artifact_index_path = output_dir / "evaluation_artifact_index.json"

    assert audit_report_path.exists()
    assert audit_summary_path.exists()
    assert manifest_path.exists()
    assert artifact_index_path.exists()

    audit_payload = json.loads(audit_report_path.read_text(encoding="utf-8"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    index_payload = json.loads(artifact_index_path.read_text(encoding="utf-8"))

    assert audit_payload["publishable"] is True
    assert manifest_payload["metadata"]["run_id"] == "test_smoke_001"
    assert index_payload["valid"] is True
    assert index_payload["publishable"] is True