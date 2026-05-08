import json
from pathlib import Path

from src.docs.sample_artifact_index import (
    build_sample_artifact,
    build_sample_artifact_index,
    load_inquiry_records_from_library,
    write_sample_artifact_index,
)
from src.frontend.inquiry_studio import InquiryRecord


def test_build_sample_artifact_detects_existing_paper_and_audit(tmp_path: Path):
    paper_path = tmp_path / "paper.html"
    audit_path = tmp_path / "audit_report.json"

    paper_path.write_text(
        "<html><head><title>Sample Paper</title></head></html>",
        encoding="utf-8",
    )

    audit_path.write_text(
        json.dumps(
            {
                "publishable": True,
                "steelman_accuracy": {
                    "verbatim_anchored_assertions": "100%",
                    "qualifications_preserved": "100%",
                    "hedge_drift_detected": False,
                },
                "evidence_balance": {
                    "claims_with_balanced_retrieval": "90%",
                    "cherry_picking_score": "low",
                    "false_consensus_count": 0,
                },
                "citation_integrity": {
                    "references_resolved": "100%",
                    "fabricated_references": 0,
                },
                "clip_anchor_accuracy": {
                    "clips_within_tolerance": "100%",
                    "drift_detected": [],
                },
            }
        ),
        encoding="utf-8",
    )

    record = InquiryRecord(
        inquiry_id="inquiry_001",
        title="Sample Inquiry",
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        status="completed",
        created_at="2026-05-08T12:00:00+00:00",
        paper_path=paper_path.as_posix(),
        audit_report_path=audit_path.as_posix(),
        parameters={},
    )

    sample = build_sample_artifact(record)

    assert sample.inquiry_id == "inquiry_001"
    assert sample.paper_exists is True
    assert sample.audit_exists is True
    assert sample.audit_publishable is True


def test_build_sample_artifact_handles_missing_files(tmp_path: Path):
    record = InquiryRecord(
        inquiry_id="inquiry_002",
        title="Missing Sample",
        youtube_url="https://youtu.be/ABC123xyz_9",
        status="completed",
        created_at="2026-05-08T12:00:00+00:00",
        paper_path=(tmp_path / "missing.html").as_posix(),
        audit_report_path=(tmp_path / "missing.json").as_posix(),
        parameters={},
    )

    sample = build_sample_artifact(record)

    assert sample.paper_exists is False
    assert sample.audit_exists is False
    assert sample.audit_publishable is None


def test_build_sample_artifact_index_renders_samples(tmp_path: Path):
    record = InquiryRecord(
        inquiry_id="inquiry_003",
        title="Rendered Sample",
        youtube_url="https://www.youtube.com/embed/ABC123xyz_9",
        status="completed",
        created_at="2026-05-08T12:00:00+00:00",
        paper_path=None,
        audit_report_path=None,
        parameters={},
    )

    index = build_sample_artifact_index([record])

    assert index.title == "Sample Inquiry Artifacts"
    assert "Rendered Sample" in index.content
    assert "Reviewer checklist" in index.content
    assert len(index.samples) == 1


def test_write_sample_artifact_index_creates_file(tmp_path: Path):
    record = InquiryRecord(
        inquiry_id="inquiry_004",
        title="Saved Sample",
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        status="completed",
        created_at="2026-05-08T12:00:00+00:00",
        paper_path=None,
        audit_report_path=None,
        parameters={},
    )

    output_path = tmp_path / "docs" / "sample_artifacts.md"

    written_path = write_sample_artifact_index(
        [record],
        output_path=output_path,
    )

    assert written_path == output_path
    assert written_path.exists()

    content = written_path.read_text(encoding="utf-8")

    assert "# Sample Inquiry Artifacts" in content
    assert "Saved Sample" in content


def test_load_inquiry_records_from_library_reads_manifests(tmp_path: Path):
    inquiry_dir = tmp_path / "inquiry_001"
    inquiry_dir.mkdir(parents=True)

    (inquiry_dir / "manifest.json").write_text(
        json.dumps(
            {
                "inquiry_id": "inquiry_001",
                "title": "Library Sample",
                "youtube_url": "https://www.youtube.com/watch?v=ABC123xyz_9",
                "status": "completed",
                "created_at": "2026-05-08T12:00:00+00:00",
                "paper_path": None,
                "audit_report_path": None,
                "parameters": {},
            }
        ),
        encoding="utf-8",
    )

    records = load_inquiry_records_from_library(tmp_path)

    assert len(records) == 1
    assert records[0].title == "Library Sample"