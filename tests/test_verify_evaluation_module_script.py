import subprocess
from pathlib import Path

import pytest

from scripts.verify_evaluation_module import assert_exists, main, run_command


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
        run_command(["python", "-c", "raise SystemExit(9)"])


def test_verify_evaluation_module_runs_smoke_suite_and_closeout(tmp_path):
    smoke_output_dir = tmp_path / "smoke_suite"
    export_smoke_output_dir = tmp_path / "export_smoke"
    docs_output_dir = tmp_path / "docs"
    status_output = tmp_path / "docs" / "evaluation_module_status.md"

    exit_code = main(
        [
            "--smoke-output-dir",
            str(smoke_output_dir),
            "--export-smoke-output-dir",
            str(export_smoke_output_dir),
            "--docs-output-dir",
            str(docs_output_dir),
            "--status-output",
            str(status_output),
            "--run-prefix",
            "verify_test",
        ]
    )

    assert exit_code == 0

    assert (smoke_output_dir / "summary.md").exists()

    assert (smoke_output_dir / "passing" / "audit_report.json").exists()
    assert (smoke_output_dir / "passing" / "audit_summary.md").exists()
    assert (smoke_output_dir / "passing" / "evaluation_manifest.json").exists()
    assert (smoke_output_dir / "passing" / "evaluation_artifact_index.json").exists()

    assert (smoke_output_dir / "unpublishable" / "bad_audit_report.json").exists()
    assert (smoke_output_dir / "unpublishable" / "bad_audit_summary.md").exists()
    assert (
        smoke_output_dir / "unpublishable" / "bad_evaluation_manifest.json"
    ).exists()
    assert (
        smoke_output_dir / "unpublishable" / "bad_evaluation_artifact_index.json"
    ).exists()

    assert (smoke_output_dir / "malformed" / "validation_report.json").exists()
    assert (smoke_output_dir / "malformed" / "validation_summary.md").exists()
    assert (
        smoke_output_dir / "malformed" / "evaluation_artifact_index.json"
    ).exists()
    assert (export_smoke_output_dir / "paper_artifact.json").exists()
    assert (export_smoke_output_dir / "audit_report.json").exists()
    assert (export_smoke_output_dir / "evaluation_artifact_index.json").exists()

    assert (docs_output_dir / "evaluation_readme_section.md").exists()
    assert (docs_output_dir / "evaluation_architecture.md").exists()
    assert (docs_output_dir / "evaluation_dev_log.md").exists()
    assert (docs_output_dir / "evaluation_completion_checklist.md").exists()
    assert (docs_output_dir / "evaluation_handoff_note.md").exists()
    assert status_output.exists()

    summary = (smoke_output_dir / "summary.md").read_text(encoding="utf-8")
    architecture = (docs_output_dir / "evaluation_architecture.md").read_text(
        encoding="utf-8"
    )
    handoff = (docs_output_dir / "evaluation_handoff_note.md").read_text(
        encoding="utf-8"
    )
    status = status_output.read_text(encoding="utf-8")

    assert "# Evaluation Smoke Suite Summary" in summary
    assert "# Evaluation System Architecture" in architecture
    assert "# Evaluation Module Handoff Note" in handoff
    assert "**Module Ready:** YES" in status
    assert "## Export-And-Evaluate Bridge Artifacts" in status
    assert "- [x] `paper_artifact.json`" in status
