from src.evaluation.evaluation_harness import AxisResult, EvaluationReport
from src.evaluation.publishability_gate import (
    attach_publishability_decision,
    decide_publishability,
)


def make_axis(score="100%", passed=True, details=None):
    return AxisResult(
        score=score,
        passed=passed,
        details=details or {},
    )


def test_decide_publishability_passes_when_all_axes_pass():
    report = EvaluationReport(
        steelman_accuracy=make_axis(
            details={
                "verbatim_anchored_assertions": "100%",
                "qualifications_preserved": "100%",
                "hedge_drift_detected": False,
                "missing_anchors": [],
            }
        ),
        evidence_balance=make_axis(
            details={
                "claims_with_balanced_retrieval": "100%",
                "cherry_picking_score": "low",
                "false_consensus_count": 0,
                "skewed_claims": [],
            }
        ),
        citation_integrity=make_axis(
            details={
                "references_resolved": "100%",
                "fabricated_references": 0,
                "unresolved_references": [],
            }
        ),
        clip_anchor_accuracy=make_axis(
            details={
                "clips_within_tolerance": "100%",
                "tolerance_seconds": 1.0,
                "drift_detected": [],
            }
        ),
        publishable=True,
    )

    decision = decide_publishability(report)

    assert decision.publishable is True
    assert decision.blocking_axes == []
    assert decision.reasons == ["All evaluation gates passed."]


def test_decide_publishability_blocks_for_steelman_drift():
    report = EvaluationReport(
        steelman_accuracy=make_axis(
            score="0%",
            passed=False,
            details={
                "verbatim_anchored_assertions": "0%",
                "qualifications_preserved": "100%",
                "hedge_drift_detected": True,
                "missing_anchors": [
                    {
                        "text": "Unsupported assertion.",
                        "anchors": ["missing_claim"],
                    }
                ],
            },
        ),
        evidence_balance=make_axis(),
        citation_integrity=make_axis(),
        clip_anchor_accuracy=make_axis(),
        publishable=False,
    )

    decision = decide_publishability(report)

    assert decision.publishable is False
    assert "steelman_accuracy" in decision.blocking_axes
    assert "The speaker perspective contains hedge drift." in decision.reasons
    assert (
        "1 speaker-perspective assertion(s) lack valid verbatim anchors."
        in decision.reasons
    )


def test_decide_publishability_blocks_for_skewed_evidence():
    report = EvaluationReport(
        steelman_accuracy=make_axis(),
        evidence_balance=make_axis(
            score="0%",
            passed=False,
            details={
                "claims_with_balanced_retrieval": "0%",
                "cherry_picking_score": "high",
                "false_consensus_count": 1,
                "skewed_claims": ["claim_001"],
            },
        ),
        citation_integrity=make_axis(),
        clip_anchor_accuracy=make_axis(),
        publishable=False,
    )

    decision = decide_publishability(report)

    assert decision.publishable is False
    assert "evidence_balance" in decision.blocking_axes
    assert (
        "1 claim(s) present a strong verdict despite skewed retrieval."
        in decision.reasons
    )
    assert "1 claim(s) have skewed retrieval." in decision.reasons


def test_decide_publishability_blocks_for_unresolved_references():
    report = EvaluationReport(
        steelman_accuracy=make_axis(),
        evidence_balance=make_axis(),
        citation_integrity=make_axis(
            score="0%",
            passed=False,
            details={
                "references_resolved": "0%",
                "fabricated_references": 2,
                "unresolved_references": [{}, {}],
            },
        ),
        clip_anchor_accuracy=make_axis(),
        publishable=False,
    )

    decision = decide_publishability(report)

    assert decision.publishable is False
    assert "citation_integrity" in decision.blocking_axes
    assert (
        "2 reference(s) could not be resolved to retrieved evidence."
        in decision.reasons
    )


def test_decide_publishability_blocks_for_clip_drift():
    report = EvaluationReport(
        steelman_accuracy=make_axis(),
        evidence_balance=make_axis(),
        citation_integrity=make_axis(),
        clip_anchor_accuracy=make_axis(
            score="0%",
            passed=False,
            details={
                "clips_within_tolerance": "0%",
                "tolerance_seconds": 1.0,
                "drift_detected": [
                    {
                        "claim_id": "claim_001",
                        "start_drift": 3.0,
                    }
                ],
            },
        ),
        publishable=False,
    )

    decision = decide_publishability(report)

    assert decision.publishable is False
    assert "clip_anchor_accuracy" in decision.blocking_axes
    assert (
        "1 rendered clip(s) drift outside the allowed timestamp tolerance."
        in decision.reasons
    )


def test_attach_publishability_decision_adds_decision_payload():
    audit_payload = {
        "publishable": False,
        "clip_anchor_accuracy": {
            "clips_within_tolerance": "0%",
        },
    }

    decision = decide_publishability(
        EvaluationReport(
            steelman_accuracy=make_axis(),
            evidence_balance=make_axis(),
            citation_integrity=make_axis(),
            clip_anchor_accuracy=make_axis(
                passed=False,
                details={
                    "drift_detected": [{"claim_id": "claim_001"}],
                },
            ),
            publishable=False,
        )
    )

    enriched = attach_publishability_decision(audit_payload, decision)

    assert enriched["publishability_decision"]["publishable"] is False
    assert enriched["publishability_decision"]["blocking_axes"] == [
        "clip_anchor_accuracy"
    ]