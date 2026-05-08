import pytest

from src.evaluation.paper_artifact_validator import validate_paper_artifact


def make_valid_artifact():
    return {
        "claims": [
            {
                "claim_id": "claim_001",
                "verbatim_quote": "Balanced evidence matters.",
                "anchor_clip": {"start": 10.0, "end": 20.0},
            }
        ],
        "speaker_perspective": {
            "expected_qualifications": ["the literature may be mixed"],
            "qualifications_preserved": ["the literature may be mixed"],
            "narrative_blocks": [
                {
                    "assertions": [
                        {
                            "text": "The speaker presents a claim that requires evidence.",
                            "hedge_drift_detected": False,
                        }
                    ],
                    "verbatim_anchors": ["claim_001"],
                }
            ],
        },
        "adjudications": [
            {
                "claim_id": "claim_001",
                "balance_score": "balanced",
                "verdict": "well_supported_with_qualifications",
            }
        ],
        "evidence_records": [
            {
                "evidence_record_id": "evidence_001",
                "identifier": "10.1234/example",
                "url": "https://example.com/paper",
            }
        ],
        "references": [
            {
                "evidence_record_id": "evidence_001",
                "identifier": "10.1234/example",
                "url": "https://example.com/paper",
            }
        ],
        "rendered_clips": [
            {
                "claim_id": "claim_001",
                "start": 10.0,
                "end": 20.0,
            }
        ],
    }


def test_validate_paper_artifact_accepts_valid_artifact():
    result = validate_paper_artifact(make_valid_artifact())

    assert result.valid is True
    assert result.errors == []


def test_validate_paper_artifact_rejects_missing_top_level_fields():
    artifact = make_valid_artifact()
    del artifact["references"]

    result = validate_paper_artifact(artifact)

    assert result.valid is False
    assert "Missing required top-level field: references" in result.errors


def test_validate_paper_artifact_rejects_duplicate_claim_ids():
    artifact = make_valid_artifact()
    artifact["claims"].append(
        {
            "claim_id": "claim_001",
            "verbatim_quote": "Duplicate claim.",
            "anchor_clip": {"start": 30.0, "end": 40.0},
        }
    )

    result = validate_paper_artifact(artifact)

    assert result.valid is False
    assert "Duplicate claim_id found: claim_001" in result.errors


def test_validate_paper_artifact_rejects_invalid_clip_range():
    artifact = make_valid_artifact()
    artifact["claims"][0]["anchor_clip"] = {"start": 20.0, "end": 10.0}

    result = validate_paper_artifact(artifact)

    assert result.valid is False
    assert "claims[0].anchor_clip.end must be greater than start." in result.errors


def test_validate_paper_artifact_rejects_unknown_speaker_anchor():
    artifact = make_valid_artifact()
    artifact["speaker_perspective"]["narrative_blocks"][0]["verbatim_anchors"] = [
        "missing_claim"
    ]

    result = validate_paper_artifact(artifact)

    assert result.valid is False
    assert (
        "speaker_perspective.narrative_blocks[0] references unknown claim_id: missing_claim"
        in result.errors
    )


def test_validate_paper_artifact_rejects_unknown_reference_evidence_id():
    artifact = make_valid_artifact()
    artifact["references"][0]["evidence_record_id"] = "missing_evidence"

    result = validate_paper_artifact(artifact)

    assert result.valid is False
    assert (
        "references[0] references unknown evidence_record_id: missing_evidence"
        in result.errors
    )


def test_validation_result_can_raise_value_error():
    artifact = make_valid_artifact()
    artifact["rendered_clips"][0]["claim_id"] = "ghost_claim"

    result = validate_paper_artifact(artifact)

    with pytest.raises(ValueError, match="Paper artifact validation failed"):
        result.raise_if_invalid()