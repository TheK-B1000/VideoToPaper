from pathlib import Path

from src.frontend.inquiry_studio import InquiryRecord
from src.frontend.rerun_request import (
    RerunOverrides,
    create_rerun_from_inquiry_record,
    create_rerun_from_run_request,
    save_rerun_request,
)
from src.frontend.run_request import create_inquiry_run_request, load_run_request


def test_create_rerun_from_inquiry_record_preserves_source_and_provenance():
    record = InquiryRecord(
        inquiry_id="inquiry_001",
        title="Original Inquiry",
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        status="completed",
        created_at="2026-05-08T12:00:00+00:00",
        paper_path="data/inquiries/inquiry_001/paper.html",
        audit_report_path="data/inquiries/inquiry_001/audit_report.json",
        parameters={
            "claim_type_filter": ["empirical_technical"],
            "retrieval_depth": 3,
            "source_tiers": [1, 2],
        },
    )

    rerun = create_rerun_from_inquiry_record(
        record,
        overrides=RerunOverrides(
            retrieval_depth=5,
            source_tiers=[1, 2, 3],
            reason="Increase evidence coverage.",
        ),
    )

    assert rerun.request_id.startswith("request_")
    assert rerun.youtube_url == record.youtube_url
    assert rerun.video_id == "ABC123xyz_9"
    assert rerun.rerun_of == "inquiry_001"
    assert rerun.reason == "Increase evidence coverage."
    assert rerun.claim_type_filter == ["empirical_technical"]
    assert rerun.retrieval_depth == 5
    assert rerun.source_tiers == [1, 2, 3]
    assert rerun.metadata["original_inquiry_id"] == "inquiry_001"
    assert rerun.metadata["original_title"] == "Original Inquiry"


def test_create_rerun_from_inquiry_record_uses_defaults_when_parameters_missing():
    record = InquiryRecord(
        inquiry_id="inquiry_002",
        title="Minimal Inquiry",
        youtube_url="https://youtu.be/ABC123xyz_9",
        status="completed",
        created_at="2026-05-08T12:00:00+00:00",
        paper_path=None,
        audit_report_path=None,
        parameters={},
    )

    rerun = create_rerun_from_inquiry_record(
        record,
        overrides=RerunOverrides(),
    )

    assert rerun.video_id == "ABC123xyz_9"
    assert rerun.rerun_of == "inquiry_002"
    assert rerun.retrieval_depth == 3
    assert rerun.source_tiers == [1, 2]
    assert rerun.claim_type_filter == [
        "empirical_historical",
        "empirical_scientific",
        "empirical_technical",
    ]


def test_create_rerun_from_inquiry_record_allows_claim_type_override():
    record = InquiryRecord(
        inquiry_id="inquiry_003",
        title="Claim Override Inquiry",
        youtube_url="https://www.youtube.com/embed/ABC123xyz_9",
        status="completed",
        created_at="2026-05-08T12:00:00+00:00",
        paper_path=None,
        audit_report_path=None,
        parameters={
            "claim_type_filter": ["empirical_technical"],
            "retrieval_depth": 2,
            "source_tiers": [1],
        },
    )

    rerun = create_rerun_from_inquiry_record(
        record,
        overrides=RerunOverrides(
            claim_type_filter=["predictive", "empirical_scientific"],
        ),
    )

    assert rerun.claim_type_filter == ["empirical_scientific", "predictive"]


def test_create_rerun_from_run_request_preserves_original_request_link():
    original = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1, 2],
        stages=["claim_inventory", "evaluation"],
    )

    rerun = create_rerun_from_run_request(
        original,
        overrides=RerunOverrides(
            retrieval_depth=6,
            reason="Retry with deeper retrieval.",
        ),
    )

    assert rerun.youtube_url == original.youtube_url
    assert rerun.video_id == original.video_id
    assert rerun.rerun_of == original.request_id
    assert rerun.retrieval_depth == 6
    assert rerun.source_tiers == [1, 2]
    assert rerun.stages == ["claim_inventory", "evaluation"]
    assert rerun.metadata["original_request_id"] == original.request_id


def test_create_rerun_from_run_request_allows_stage_override():
    original = create_inquiry_run_request(
        youtube_url="https://youtu.be/ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1],
        stages=["source_ingestion", "claim_inventory", "evaluation"],
    )

    rerun = create_rerun_from_run_request(
        original,
        overrides=RerunOverrides(
            stages=["evidence_retrieval", "evaluation"],
        ),
    )

    assert rerun.stages == ["evidence_retrieval", "evaluation"]


def test_save_rerun_request_round_trip(tmp_path: Path):
    record = InquiryRecord(
        inquiry_id="inquiry_004",
        title="Saved Rerun Inquiry",
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        status="completed",
        created_at="2026-05-08T12:00:00+00:00",
        paper_path=None,
        audit_report_path=None,
        parameters={
            "claim_type_filter": ["empirical_technical"],
            "retrieval_depth": 3,
            "source_tiers": [1],
        },
    )

    rerun = create_rerun_from_inquiry_record(
        record,
        overrides=RerunOverrides(reason="Save rerun artifact."),
    )

    output_path = save_rerun_request(rerun, output_dir=tmp_path)

    loaded = load_run_request(output_path)

    assert loaded.request_id == rerun.request_id
    assert loaded.rerun_of == "inquiry_004"
    assert loaded.reason == "Save rerun artifact."
    assert loaded.metadata["original_inquiry_id"] == "inquiry_004"