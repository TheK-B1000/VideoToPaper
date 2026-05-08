from pathlib import Path

import pytest

from scripts.smoke_evaluation_suite import main, run_command


def test_run_command_raises_for_failed_command():
    with pytest.raises(RuntimeError):
        run_command(["python", "-c", "raise SystemExit(7)"])


def test_smoke_evaluation_suite_runs_all_smoke_scripts(tmp_path):
    output_dir = tmp_path / "suite"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--run-prefix",
            "suite_test",
        ]
    )

    assert exit_code == 0

    passing_dir = output_dir / "passing"
    unpublishable_dir = output_dir / "unpublishable"
    malformed_dir = output_dir / "malformed"

    assert (passing_dir / "audit_report.json").exists()
    assert (passing_dir / "audit_summary.md").exists()
    assert (passing_dir / "evaluation_manifest.json").exists()
    assert (passing_dir / "evaluation_artifact_index.json").exists()

    assert (unpublishable_dir / "bad_audit_report.json").exists()
    assert (unpublishable_dir / "bad_audit_summary.md").exists()
    assert (unpublishable_dir / "bad_evaluation_manifest.json").exists()
    assert (unpublishable_dir / "bad_evaluation_artifact_index.json").exists()

    assert not (malformed_dir / "audit_report.json").exists()
    assert not (malformed_dir / "audit_summary.md").exists()
    assert not (malformed_dir / "evaluation_manifest.json").exists()
    assert (malformed_dir / "validation_report.json").exists()
    assert (malformed_dir / "validation_summary.md").exists()
    assert (malformed_dir / "evaluation_artifact_index.json").exists()