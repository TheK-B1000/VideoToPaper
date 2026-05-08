import json

import pytest

from src.evaluation.audit_report_writer import (
    load_audit_report,
    write_audit_report,
)
from src.evaluation.evaluation_harness import AxisResult, EvaluationReport


def make_report(publishable=True):
    return EvaluationReport(
        steelman_accuracy=AxisResult(
            score="100%",
            passed=True,
            details={
                "verbatim_anchored_assertions": "100%",
                "qualifications_preserved": "100%",
                "hedge_drift_detected": False,
                "missing_anchors": [],
            },
        ),
        evidence_balance=AxisResult(
            score="100%",
            passed=True,
            details={
                "claims_with_balanced_retrieval": "100%",
                "cherry_picking_score": "low",
                "false_consensus_count": 0,
                "skewed_claims": [],
            },
        ),
        citation_integrity=AxisResult(
            score="100%",
            passed=True,
            details={
                "references_resolved": "100%",
                "fabricated_references": 0,
                "unresolved_references": [],
            },
        ),
        clip_anchor_accuracy=AxisResult(
            score="100%",
            passed=True,
            details={
                "clips_within_tolerance": "100%",
                "tolerance_seconds": 1.0,
                "drift_detected": [],
            },
        ),
        publishable=publishable,
    )


def test_write_audit_report_creates_json_file(tmp_path):
    report = make_report()
    output_path = tmp_path / "reports" / "audit_report.json"

    written_path = write_audit_report(report, output_path)

    assert written_path == output_path
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["publishable"] is True
    assert payload["steelman_accuracy"]["verbatim_anchored_assertions"] == "100%"
    assert payload["evidence_balance"]["cherry_picking_score"] == "low"
    assert payload["citation_integrity"]["fabricated_references"] == 0
    assert payload["clip_anchor_accuracy"]["clips_within_tolerance"] == "100%"
    assert payload["publishability_decision"]["publishable"] is True
    assert payload["publishability_decision"]["blocking_axes"] == []
    assert payload["publishability_decision"]["reasons"] == [
        "All evaluation gates passed."
    ]


def test_write_audit_report_includes_blocking_reasons(tmp_path):
    report = EvaluationReport(
        steelman_accuracy=AxisResult(
            score="100%",
            passed=True,
            details={
                "verbatim_anchored_assertions": "100%",
                "qualifications_preserved": "100%",
                "hedge_drift_detected": False,
                "missing_anchors": [],
            },
        ),
        evidence_balance=AxisResult(
            score="0%",
            passed=False,
            details={
                "claims_with_balanced_retrieval": "0%",
                "cherry_picking_score": "high",
                "false_consensus_count": 1,
                "skewed_claims": ["claim_001"],
            },
        ),
        citation_integrity=AxisResult(
            score="100%",
            passed=True,
            details={
                "references_resolved": "100%",
                "fabricated_references": 0,
                "unresolved_references": [],
            },
        ),
        clip_anchor_accuracy=AxisResult(
            score="100%",
            passed=True,
            details={
                "clips_within_tolerance": "100%",
                "tolerance_seconds": 1.0,
                "drift_detected": [],
            },
        ),
        publishable=False,
    )

    output_path = tmp_path / "audit_report.json"

    write_audit_report(report, output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["publishability_decision"]["publishable"] is False
    assert payload["publishability_decision"]["blocking_axes"] == [
        "evidence_balance"
    ]
    assert (
        "1 claim(s) present a strong verdict despite skewed retrieval."
        in payload["publishability_decision"]["reasons"]
    )


def test_write_audit_report_creates_parent_directories(tmp_path):
    report = make_report()
    output_path = tmp_path / "nested" / "audit" / "report.json"

    write_audit_report(report, output_path)

    assert output_path.exists()


def test_load_audit_report_reads_written_report(tmp_path):
    report = make_report(publishable=False)
    output_path = tmp_path / "audit_report.json"

    write_audit_report(report, output_path)
    loaded = load_audit_report(output_path)

    assert loaded["publishable"] is False
    assert loaded["steelman_accuracy"]["hedge_drift_detected"] is False


def test_load_audit_report_raises_for_missing_file(tmp_path):
    missing_path = tmp_path / "missing_report.json"

    with pytest.raises(FileNotFoundError):
        load_audit_report(missing_path)