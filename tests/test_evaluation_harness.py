from src.evaluation.evaluation_harness import (
    EvaluationConfig,
    evaluate_citation_integrity,
    evaluate_clip_anchor_accuracy,
    evaluate_evidence_balance,
    evaluate_steelman_accuracy,
    run_evaluation_harness,
)


def test_steelman_accuracy_passes_when_assertions_are_verbatim_anchored():
    claims_by_id = {
        "claim_001": {
            "claim_id": "claim_001",
            "verbatim_quote": "This system needs balanced evidence.",
        }
    }

    speaker_perspective = {
        "expected_qualifications": ["only empirical claims need literature review"],
        "qualifications_preserved": ["only empirical claims need literature review"],
        "narrative_blocks": [
            {
                "assertions": [
                    {
                        "text": "The speaker argues for balanced evidence.",
                        "hedge_drift_detected": False,
                    }
                ],
                "verbatim_anchors": ["claim_001"],
            }
        ],
    }

    result = evaluate_steelman_accuracy(speaker_perspective, claims_by_id)

    assert result.passed is True
    assert result.details["verbatim_anchored_assertions"] == "100%"
    assert result.details["qualifications_preserved"] == "100%"
    assert result.details["hedge_drift_detected"] is False


def test_steelman_accuracy_fails_when_an_assertion_has_no_valid_anchor():
    claims_by_id = {}

    speaker_perspective = {
        "expected_qualifications": [],
        "qualifications_preserved": [],
        "narrative_blocks": [
            {
                "assertions": [
                    {
                        "text": "The speaker made a specific factual claim.",
                        "hedge_drift_detected": False,
                    }
                ],
                "verbatim_anchors": ["missing_claim"],
            }
        ],
    }

    result = evaluate_steelman_accuracy(speaker_perspective, claims_by_id)

    assert result.passed is False
    assert result.details["verbatim_anchored_assertions"] == "0%"
    assert result.details["missing_anchors"][0]["anchors"] == ["missing_claim"]


def test_evidence_balance_flags_false_consensus_from_skewed_retrieval():
    adjudications = [
        {
            "claim_id": "claim_001",
            "balance_score": "supportive_skewed",
            "verdict": "well_supported",
        }
    ]

    result = evaluate_evidence_balance(adjudications)

    assert result.passed is False
    assert result.details["cherry_picking_score"] == "high"
    assert result.details["false_consensus_count"] == 1
    assert result.details["skewed_claims"] == ["claim_001"]


def test_evidence_balance_passes_when_claims_are_balanced():
    adjudications = [
        {
            "claim_id": "claim_001",
            "balance_score": "balanced",
            "verdict": "well_supported_with_qualifications",
        },
        {
            "claim_id": "claim_002",
            "balance_score": "balanced",
            "verdict": "contested",
        },
    ]

    result = evaluate_evidence_balance(adjudications)

    assert result.passed is True
    assert result.details["claims_with_balanced_retrieval"] == "100%"
    assert result.details["cherry_picking_score"] == "low"


def test_citation_integrity_passes_when_references_resolve_to_evidence_records():
    evidence_records_by_id = {
        "evidence_001": {
            "evidence_record_id": "evidence_001",
            "identifier": "10.1234/example",
            "url": "https://example.com/paper",
        }
    }

    references = [
        {
            "evidence_record_id": "evidence_001",
            "identifier": "10.1234/example",
            "url": "https://example.com/paper",
        }
    ]

    result = evaluate_citation_integrity(references, evidence_records_by_id)

    assert result.passed is True
    assert result.details["references_resolved"] == "100%"
    assert result.details["fabricated_references"] == 0


def test_citation_integrity_fails_when_reference_is_not_retrieved():
    evidence_records_by_id = {}

    references = [
        {
            "evidence_record_id": "fake_evidence",
            "identifier": "fake_identifier",
            "url": "https://fake.example",
        }
    ]

    result = evaluate_citation_integrity(references, evidence_records_by_id)

    assert result.passed is False
    assert result.details["references_resolved"] == "0%"
    assert result.details["fabricated_references"] == 1


def test_clip_anchor_accuracy_passes_when_clip_is_inside_tolerance():
    claims = [
        {
            "claim_id": "claim_001",
            "anchor_clip": {"start": 252.4, "end": 263.0},
        }
    ]

    rendered_clips = [
        {
            "claim_id": "claim_001",
            "start": 252,
            "end": 263,
        }
    ]

    config = EvaluationConfig(clip_tolerance_seconds=1.0)

    result = evaluate_clip_anchor_accuracy(claims, rendered_clips, config)

    assert result.passed is True
    assert result.details["clips_within_tolerance"] == "100%"
    assert result.details["drift_detected"] == []


def test_clip_anchor_accuracy_fails_when_clip_drifts_outside_tolerance():
    claims = [
        {
            "claim_id": "claim_001",
            "anchor_clip": {"start": 252.4, "end": 263.0},
        }
    ]

    rendered_clips = [
        {
            "claim_id": "claim_001",
            "start": 249.0,
            "end": 270.0,
        }
    ]

    config = EvaluationConfig(clip_tolerance_seconds=1.0)

    result = evaluate_clip_anchor_accuracy(claims, rendered_clips, config)

    assert result.passed is False
    assert result.details["clips_within_tolerance"] == "0%"
    assert result.details["drift_detected"][0]["claim_id"] == "claim_001"


def test_run_evaluation_harness_returns_publishable_true_for_clean_artifact():
    paper_artifact = {
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

    report = run_evaluation_harness(paper_artifact)

    assert report.publishable is True
    assert report.to_dict()["publishable"] is True
    assert report.to_dict()["clip_anchor_accuracy"]["clips_within_tolerance"] == "100%"
    