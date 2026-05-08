import json

import pytest

from scripts.smoke_export_and_evaluate import assert_exists, main, run_command


def test_assert_exists_accepts_existing_file(tmp_path):
    path = tmp_path / "artifact.json"
    path.write_text("{}", encoding="utf-8")

    assert_exists(path)


def test_assert_exists_raises_for_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        assert_exists(tmp_path / "missing.json")


def test_run_command_raises_for_failed_command():
    with pytest.raises(RuntimeError):
        run_command(["python", "-c", "raise SystemExit(5)"])


def test_smoke_export_and_evaluate_runs_end_to_end(tmp_path):
    output_dir = tmp_path / "export_eval_smoke"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--run-id",
            "export_eval_smoke_test_001",
        ]
    )

    assert exit_code == 0

    assert (output_dir / "claims.json").exists()
    assert (output_dir / "speaker_perspective.json").exists()
    assert (output_dir / "adjudications.json").exists()
    assert (output_dir / "evidence_records.json").exists()
    assert (output_dir / "paper_artifact.json").exists()
    assert (output_dir / "audit_report.json").exists()
    assert (output_dir / "audit_summary.md").exists()
    assert (output_dir / "evaluation_manifest.json").exists()
    assert (output_dir / "evaluation_artifact_index.json").exists()

    audit = json.loads((output_dir / "audit_report.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (output_dir / "evaluation_manifest.json").read_text(encoding="utf-8")
    )
    index = json.loads(
        (output_dir / "evaluation_artifact_index.json").read_text(encoding="utf-8")
    )

    assert audit["publishable"] is True
    assert manifest["metadata"]["run_id"] == "export_eval_smoke_test_001"
    assert index["valid"] is True
    assert index["publishable"] is True
