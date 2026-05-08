import json

from src.evaluation.evaluation_runner import run_paper_evaluation
from src.evaluation.sample_artifacts import (
    build_publishable_sample_artifact,
    build_unpublishable_sample_artifact,
    write_sample_artifact,
)


def test_publishable_sample_artifact_passes_evaluation(tmp_path):
    artifact = build_publishable_sample_artifact()
    audit_report_path = tmp_path / "audit_report.json"

    result = run_paper_evaluation(
        paper_artifact=artifact,
        audit_report_path=audit_report_path,
    )

    assert result.publishable is True

    payload = json.loads(audit_report_path.read_text(encoding="utf-8"))

    assert payload["publishable"] is True
    assert payload["steelman_accuracy"]["verbatim_anchored_assertions"] == "100%"
    assert payload["evidence_balance"]["cherry_picking_score"] == "low"
    assert payload["citation_integrity"]["fabricated_references"] == 0
    assert payload["clip_anchor_accuracy"]["drift_detected"] == []


def test_unpublishable_sample_artifact_fails_evaluation(tmp_path):
    artifact = build_unpublishable_sample_artifact()
    audit_report_path = tmp_path / "audit_report.json"

    result = run_paper_evaluation(
        paper_artifact=artifact,
        audit_report_path=audit_report_path,
    )

    assert result.publishable is False

    payload = json.loads(audit_report_path.read_text(encoding="utf-8"))

    assert payload["publishable"] is False
    assert payload["evidence_balance"]["cherry_picking_score"] == "high"
    assert payload["citation_integrity"]["fabricated_references"] == 1
    assert payload["clip_anchor_accuracy"]["clips_within_tolerance"] == "0%"


def test_write_sample_artifact_creates_publishable_json(tmp_path):
    output_path = tmp_path / "fixtures" / "paper_artifact.json"

    written_path = write_sample_artifact(output_path, publishable=True)

    assert written_path == output_path
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["claims"][0]["claim_id"] == "claim_001"
    assert payload["rendered_clips"][0]["start"] == 10.0


def test_write_sample_artifact_creates_unpublishable_json(tmp_path):
    output_path = tmp_path / "fixtures" / "bad_paper_artifact.json"

    write_sample_artifact(output_path, publishable=False)

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["rendered_clips"][0]["start"] == 40.0
    assert payload["references"][-1]["evidence_record_id"] == "evidence_001"