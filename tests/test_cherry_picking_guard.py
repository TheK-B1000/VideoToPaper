import pytest

from src.integration.cherry_picking_guard import build_cherry_picking_guard_report


def test_guard_report_marks_clean_batch_publishable():
    adjudications = [
        {
            "claim_id": "claim_001",
            "verdict": "well_supported_with_qualifications",
            "guard_reason": None,
        },
        {
            "claim_id": "claim_002",
            "verdict": "mixed_or_contested",
            "guard_reason": None,
        },
    ]

    report = build_cherry_picking_guard_report(adjudications)

    assert report["total_adjudications"] == 2
    assert report["safe_adjudications"] == 2
    assert report["guarded_adjudications"] == 0
    assert report["publishable_for_week8"] is True
    assert report["guarded_claim_ids"] == []
    assert "No guarded adjudications detected." in report["report_notes"]


def test_guard_report_tracks_guarded_claims():
    adjudications = [
        {
            "claim_id": "claim_001",
            "verdict": "well_supported_with_qualifications",
            "guard_reason": None,
        },
        {
            "claim_id": "claim_002",
            "verdict": "requires_manual_review",
            "guard_reason": "Retrieval is supportive_skewed.",
        },
    ]

    report = build_cherry_picking_guard_report(adjudications)

    assert report["total_adjudications"] == 2
    assert report["safe_adjudications"] == 1
    assert report["guarded_adjudications"] == 1
    assert report["manual_review_count"] == 1
    assert report["guarded_claim_ids"] == ["claim_002"]


def test_guard_report_blocks_week8_when_guarded_ratio_is_too_high():
    adjudications = [
        {
            "claim_id": "claim_001",
            "verdict": "requires_manual_review",
            "guard_reason": "Retrieval is supportive_skewed.",
        },
        {
            "claim_id": "claim_002",
            "verdict": "requires_manual_review",
            "guard_reason": "Retrieval is contrary_skewed.",
        },
        {
            "claim_id": "claim_003",
            "verdict": "mixed_or_contested",
            "guard_reason": None,
        },
    ]

    report = build_cherry_picking_guard_report(
        adjudications,
        max_guarded_ratio_for_publish=0.25,
    )

    assert report["guarded_adjudications"] == 2
    assert report["publishable_for_week8"] is False
    assert any(
        "should not be treated as publishable" in note
        for note in report["report_notes"]
    )


def test_guard_report_counts_insufficient_evidence():
    adjudications = [
        {
            "claim_id": "claim_001",
            "verdict": "insufficient_evidence",
            "guard_reason": "No usable evidence records were retrieved.",
        }
    ]

    report = build_cherry_picking_guard_report(adjudications)

    assert report["insufficient_evidence_count"] == 1
    assert report["guarded_adjudications"] == 1
    assert report["guarded_claim_ids"] == ["claim_001"]


def test_guard_report_rejects_invalid_threshold():
    with pytest.raises(ValueError, match="between 0 and 1"):
        build_cherry_picking_guard_report(
            [],
            max_guarded_ratio_for_publish=1.5,
        )


def test_guard_report_rejects_adjudication_without_claim_id():
    adjudications = [
        {
            "verdict": "mixed_or_contested",
            "guard_reason": None,
        }
    ]

    with pytest.raises(ValueError, match="claim_id"):
        build_cherry_picking_guard_report(adjudications)
