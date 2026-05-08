import json

import pytest

from src.evaluation.evaluation_artifact_index import (
    build_evaluation_artifact_index,
    load_evaluation_artifact_index,
    write_evaluation_artifact_index,
)


def test_build_evaluation_artifact_index_records_all_paths():
    index = build_evaluation_artifact_index(
        paper_artifact_path="data/outputs/paper_artifact.json",
        audit_report_path="data/outputs/audit_report.json",
        audit_summary_path="data/outputs/audit_summary.md",
        manifest_path="data/outputs/evaluation_manifest.json",
        validation_report_path="data/outputs/validation_report.json",
        validation_summary_path="data/outputs/validation_summary.md",
        publishable=True,
        valid=True,
        metadata={"run_id": "run_001"},
    )

    payload = index.to_dict()

    assert payload["paper_artifact_path"] == "data/outputs/paper_artifact.json"
    assert payload["audit_report_path"] == "data/outputs/audit_report.json"
    assert payload["audit_summary_path"] == "data/outputs/audit_summary.md"
    assert payload["manifest_path"] == "data/outputs/evaluation_manifest.json"
    assert payload["validation_report_path"] == "data/outputs/validation_report.json"
    assert payload["validation_summary_path"] == "data/outputs/validation_summary.md"
    assert payload["publishable"] is True
    assert payload["valid"] is True
    assert payload["metadata"]["run_id"] == "run_001"


def test_write_evaluation_artifact_index_creates_json_file(tmp_path):
    index = build_evaluation_artifact_index(
        paper_artifact_path="paper.json",
        audit_report_path="audit.json",
        audit_summary_path="summary.md",
        manifest_path="manifest.json",
        validation_report_path=None,
        validation_summary_path=None,
        publishable=True,
        valid=True,
    )

    output_path = tmp_path / "runs" / "artifact_index.json"

    written_path = write_evaluation_artifact_index(index, output_path)

    assert written_path == output_path
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["publishable"] is True
    assert payload["valid"] is True
    assert payload["validation_report_path"] is None


def test_load_evaluation_artifact_index_reads_json(tmp_path):
    index = build_evaluation_artifact_index(
        paper_artifact_path="paper.json",
        audit_report_path="audit.json",
        publishable=False,
        valid=True,
    )

    output_path = tmp_path / "artifact_index.json"
    write_evaluation_artifact_index(index, output_path)

    loaded = load_evaluation_artifact_index(output_path)

    assert loaded["paper_artifact_path"] == "paper.json"
    assert loaded["audit_report_path"] == "audit.json"
    assert loaded["publishable"] is False


def test_load_evaluation_artifact_index_raises_for_missing_file(tmp_path):
    missing_path = tmp_path / "missing_artifact_index.json"

    with pytest.raises(FileNotFoundError):
        load_evaluation_artifact_index(missing_path)