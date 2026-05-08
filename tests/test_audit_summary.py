from src.evaluation.audit_summary import render_audit_summary


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