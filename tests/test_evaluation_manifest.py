import json

import pytest

from src.evaluation.evaluation_manifest import (
    build_evaluation_manifest,
    load_evaluation_manifest,
    write_evaluation_manifest,
)


def test_build_evaluation_manifest_records_paths_and_status():
    manifest = build_evaluation_manifest(
        paper_artifact_path="data/outputs/paper_artifact.json",
        audit_report_path="data/outputs/audit_report.json",
        audit_summary_path="data/outputs/audit_summary.md",
        publishable=True,
        started_at="2026-05-08T10:00:00+00:00",
        finished_at="2026-05-08T10:00:02+00:00",
        metadata={"run_id": "run_001"},
    )

    payload = manifest.to_dict()

    assert payload["paper_artifact_path"] == "data/outputs/paper_artifact.json"
    assert payload["audit_report_path"] == "data/outputs/audit_report.json"
    assert payload["audit_summary_path"] == "data/outputs/audit_summary.md"
    assert payload["publishable"] is True
    assert payload["metadata"]["run_id"] == "run_001"


def test_write_evaluation_manifest_creates_json_file(tmp_path):
    manifest = build_evaluation_manifest(
        paper_artifact_path="paper.json",
        audit_report_path="audit.json",
        audit_summary_path=None,
        publishable=False,
        started_at="2026-05-08T10:00:00+00:00",
        finished_at="2026-05-08T10:00:02+00:00",
    )

    output_path = tmp_path / "runs" / "manifest.json"

    written_path = write_evaluation_manifest(manifest, output_path)

    assert written_path == output_path
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["publishable"] is False
    assert payload["audit_summary_path"] is None


def test_load_evaluation_manifest_reads_json(tmp_path):
    manifest = build_evaluation_manifest(
        paper_artifact_path="paper.json",
        audit_report_path="audit.json",
        audit_summary_path="summary.md",
        publishable=True,
        started_at="2026-05-08T10:00:00+00:00",
        finished_at="2026-05-08T10:00:02+00:00",
    )

    output_path = tmp_path / "manifest.json"
    write_evaluation_manifest(manifest, output_path)

    loaded = load_evaluation_manifest(output_path)

    assert loaded["paper_artifact_path"] == "paper.json"
    assert loaded["publishable"] is True


def test_load_evaluation_manifest_raises_for_missing_file(tmp_path):
    missing_path = tmp_path / "missing_manifest.json"

    with pytest.raises(FileNotFoundError):
        load_evaluation_manifest(missing_path)