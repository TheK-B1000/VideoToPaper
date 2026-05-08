from src.evaluation.audit_summary_writer import write_audit_summary


def test_write_audit_summary_creates_markdown_file(tmp_path):
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

    output_path = tmp_path / "reports" / "audit_summary.md"

    written_path = write_audit_summary(audit_payload, output_path)

    assert written_path == output_path
    assert output_path.exists()

    summary = output_path.read_text(encoding="utf-8")

    assert "# Inquiry Audit Summary" in summary
    assert "**Publishable:** PASS" in summary
    assert "- All evaluation gates passed." in summary
    assert "| References resolved | 100% |" in summary


def test_write_audit_summary_creates_parent_directories(tmp_path):
    audit_payload = {
        "publishability_decision": {
            "publishable": False,
            "reasons": [],
            "blocking_axes": [],
        }
    }

    output_path = tmp_path / "nested" / "summaries" / "audit_summary.md"

    write_audit_summary(audit_payload, output_path)

    assert output_path.exists()