from src.evaluation.audit_summary import render_audit_summary
from src.frontend.audit_summary import (
    summarize_audit_axis,
    summarize_audit_report,
)


def test_render_audit_summary_for_publishable_payload():
    audit_payload = {
        "publishable": True,
        "publishability_decision": {
            "publishable": True,
            "reasons": ["All evaluation gates passed."],
            "blocking_axes": [],
        },
        "steelman_accuracy": {
            "verbatim_anchored_assertions": "100%",
            "qualifications_preserved": "100%",
            "hedge_drift_detected": False,
            "missing_anchors": [],
        },
        "evidence_balance": {
            "claims_with_balanced_retrieval": "100%",
            "cherry_picking_score": "low",
            "false_consensus_count": 0,
            "skewed_claims": [],
        },
        "citation_integrity": {
            "references_resolved": "100%",
            "fabricated_references": 0,
            "unresolved_references": [],
        },
        "clip_anchor_accuracy": {
            "clips_within_tolerance": "100%",
            "tolerance_seconds": 1.0,
            "drift_detected": [],
        },
    }

    summary = render_audit_summary(audit_payload)

    assert "# Inquiry Audit Summary" in summary
    assert "**Publishable:** PASS" in summary
    assert "- All evaluation gates passed." in summary
    assert "| Steelman anchored assertions | 100% |" in summary
    assert "| Cherry-picking score | low |" in summary
    assert "- None" in summary


def test_render_audit_summary_for_unpublishable_payload():
    audit_payload = {
        "publishable": False,
        "publishability_decision": {
            "publishable": False,
            "reasons": [
                "1 reference(s) could not be resolved to retrieved evidence.",
                "1 rendered clip(s) drift outside the allowed timestamp tolerance.",
            ],
            "blocking_axes": [
                "citation_integrity",
                "clip_anchor_accuracy",
            ],
        },
        "steelman_accuracy": {
            "verbatim_anchored_assertions": "100%",
            "qualifications_preserved": "100%",
            "hedge_drift_detected": False,
            "missing_anchors": [],
        },
        "evidence_balance": {
            "claims_with_balanced_retrieval": "100%",
            "cherry_picking_score": "low",
            "false_consensus_count": 0,
            "skewed_claims": [],
        },
        "citation_integrity": {
            "references_resolved": "50%",
            "fabricated_references": 1,
            "unresolved_references": [
                {
                    "evidence_record_id": "fake_evidence",
                    "identifier": "fake-source",
                }
            ],
        },
        "clip_anchor_accuracy": {
            "clips_within_tolerance": "0%",
            "tolerance_seconds": 1.0,
            "drift_detected": [
                {
                    "claim_id": "claim_001",
                    "start_drift": 30.0,
                    "end_drift": 0.0,
                }
            ],
        },
    }

    summary = render_audit_summary(audit_payload)

    assert "**Publishable:** FAIL" in summary
    assert "- citation_integrity" in summary
    assert "- clip_anchor_accuracy" in summary
    assert "## Unresolved References" in summary
    assert "`fake_evidence` / `fake-source`" in summary
    assert "## Clip Drift" in summary
    assert "`claim_001` start drift: 30.0, end drift: 0.0" in summary


def test_render_audit_summary_handles_missing_optional_fields():
    audit_payload = {
        "publishability_decision": {
            "publishable": False,
            "reasons": [],
            "blocking_axes": [],
        }
    }

    summary = render_audit_summary(audit_payload)

    assert "**Publishable:** FAIL" in summary
    assert "- No reasons provided." in summary
    assert "| References resolved | unknown |" in summary
    assert "| Clips within tolerance | unknown |" in summary


def test_summarize_audit_report_marks_clean_report_publishable():
    report = {
        "publishable": True,
        "steelman_accuracy": {
            "verbatim_anchored_assertions": "100%",
            "qualifications_preserved": "100%",
            "hedge_drift_detected": False,
        },
        "evidence_balance": {
            "claims_with_balanced_retrieval": "92%",
            "cherry_picking_score": "low",
            "false_consensus_count": 0,
        },
        "citation_integrity": {
            "references_resolved": "100%",
            "fabricated_references": 0,
        },
        "clip_anchor_accuracy": {
            "clips_within_tolerance": "100%",
            "tolerance_seconds": 1.0,
            "drift_detected": [],
        },
    }

    summary = summarize_audit_report(report)

    assert summary.publishable is True
    assert summary.status_label == "publishable"
    assert summary.blocking_issues == []
    assert all(axis.status == "pass" for axis in summary.axes)


def test_summarize_audit_report_detects_fabricated_references():
    report = {
        "publishable": False,
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
            "references_resolved": "98%",
            "fabricated_references": 2,
        },
        "clip_anchor_accuracy": {
            "clips_within_tolerance": "100%",
            "drift_detected": [],
        },
    }

    summary = summarize_audit_report(report)

    assert summary.publishable is False
    assert summary.status_label == "not_publishable"
    assert any("fabricated reference" in issue for issue in summary.blocking_issues)

    citation_axis = next(
        axis for axis in summary.axes if axis.axis == "citation_integrity"
    )

    assert citation_axis.status == "fail"


def test_summarize_audit_report_detects_clip_drift():
    report = {
        "publishable": False,
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
            "clips_within_tolerance": "80%",
            "drift_detected": [
                {"claim_id": "claim_001", "expected_start": 12, "actual_start": 20}
            ],
        },
    }

    summary = summarize_audit_report(report)

    assert any("clip drift" in issue for issue in summary.blocking_issues)

    clip_axis = next(
        axis for axis in summary.axes if axis.axis == "clip_anchor_accuracy"
    )

    assert clip_axis.status == "fail"


def test_summarize_audit_report_warns_on_low_balance_without_blocking():
    report = {
        "publishable": False,
        "steelman_accuracy": {
            "verbatim_anchored_assertions": "100%",
            "qualifications_preserved": "100%",
            "hedge_drift_detected": False,
        },
        "evidence_balance": {
            "claims_with_balanced_retrieval": "65%",
            "cherry_picking_score": "medium",
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

    summary = summarize_audit_report(report)

    assert summary.blocking_issues == []
    assert any("Balanced retrieval" in issue for issue in summary.warning_issues)

    balance_axis = next(
        axis for axis in summary.axes if axis.axis == "evidence_balance"
    )

    assert balance_axis.status == "warning"


def test_summarize_audit_axis_fails_malformed_axis():
    axis = summarize_audit_axis("citation_integrity", None)

    assert axis.status == "fail"
    assert axis.issues == ["Axis report is missing or malformed."]


def test_summarize_audit_report_detects_hedge_drift():
    report = {
        "publishable": False,
        "steelman_accuracy": {
            "verbatim_anchored_assertions": "100%",
            "qualifications_preserved": "100%",
            "hedge_drift_detected": True,
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

    summary = summarize_audit_report(report)

    assert any("Hedge drift" in issue for issue in summary.blocking_issues)

    steelman_axis = next(
        axis for axis in summary.axes if axis.axis == "steelman_accuracy"
    )

    assert steelman_axis.status == "fail"