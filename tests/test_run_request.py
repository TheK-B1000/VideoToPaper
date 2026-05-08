import json
from pathlib import Path

import pytest

from src.frontend.run_request import (
    DEFAULT_PIPELINE_STAGES,
    create_inquiry_run_request,
    load_run_request,
    run_request_from_dict,
    save_run_request,
    validate_pipeline_stages,
)


def test_create_inquiry_run_request_uses_validated_video_config():
    request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical", "predictive"],
        retrieval_depth=3,
        source_tiers=[2, 1],
    )

    assert request.request_id.startswith("request_")
    assert request.youtube_url == "https://www.youtube.com/watch?v=ABC123xyz_9"
    assert request.video_id == "ABC123xyz_9"
    assert request.claim_type_filter == ["empirical_technical", "predictive"]
    assert request.retrieval_depth == 3
    assert request.source_tiers == [1, 2]
    assert request.stages == DEFAULT_PIPELINE_STAGES
    assert request.rerun_of is None


def test_create_inquiry_run_request_supports_rerun_metadata():
    request = create_inquiry_run_request(
        youtube_url="https://youtu.be/ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=2,
        source_tiers=[1],
        stages=["claim_inventory", "evidence_retrieval", "evaluation"],
        rerun_of="inquiry_001",
        reason="Increase retrieval depth for stronger evidence coverage.",
        metadata={"operator": "local_dev"},
    )

    assert request.rerun_of == "inquiry_001"
    assert request.reason == "Increase retrieval depth for stronger evidence coverage."
    assert request.metadata["operator"] == "local_dev"
    assert request.stages == [
        "claim_inventory",
        "evidence_retrieval",
        "evaluation",
    ]


def test_create_inquiry_run_request_rejects_invalid_youtube_url():
    with pytest.raises(ValueError, match="Could not parse"):
        create_inquiry_run_request(
            youtube_url="https://example.com/video",
            claim_type_filter=["empirical_technical"],
            retrieval_depth=3,
            source_tiers=[1],
        )


def test_validate_pipeline_stages_accepts_known_stages():
    validate_pipeline_stages(["source_ingestion", "evaluation"])


def test_validate_pipeline_stages_rejects_empty_list():
    with pytest.raises(ValueError, match="At least one pipeline stage"):
        validate_pipeline_stages([])


def test_validate_pipeline_stages_rejects_unknown_stage():
    with pytest.raises(ValueError, match="Invalid pipeline stages"):
        validate_pipeline_stages(["source_ingestion", "dragon_summoning"])


def test_save_and_load_run_request_round_trip(tmp_path: Path):
    request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=4,
        source_tiers=[1, 2],
        stages=["source_ingestion", "claim_inventory"],
        metadata={"created_from": "test"},
    )

    output_path = save_run_request(request, tmp_path)

    assert output_path.exists()

    loaded = load_run_request(output_path)

    assert loaded.request_id == request.request_id
    assert loaded.youtube_url == request.youtube_url
    assert loaded.video_id == request.video_id
    assert loaded.retrieval_depth == 4
    assert loaded.source_tiers == [1, 2]
    assert loaded.stages == ["source_ingestion", "claim_inventory"]
    assert loaded.metadata["created_from"] == "test"


def test_run_request_from_dict_rejects_missing_required_fields():
    with pytest.raises(ValueError, match="missing fields"):
        run_request_from_dict(
            {
                "request_id": "request_001",
                "created_at": "2026-05-08T12:00:00+00:00",
            }
        )


def test_load_run_request_rejects_non_object_json(tmp_path: Path):
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(["bad"]), encoding="utf-8")

    with pytest.raises(ValueError, match="JSON object"):
        load_run_request(request_path)