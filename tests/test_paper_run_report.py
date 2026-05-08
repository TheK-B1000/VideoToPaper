import json
from pathlib import Path

import pytest

from src.paper.paper_run_report import (
    PaperRunReportError,
    write_paper_assembly_run_report,
)


def test_write_paper_assembly_run_report_without_audit(tmp_path: Path) -> None:
    report_path = tmp_path / "paper_assembly_run_report.json"

    result = write_paper_assembly_run_report(
        output_path=report_path,
        started_at="2026-05-08T12:00:00+00:00",
        source_registry_path="data/processed/source_registry.json",
        claim_inventory_path="data/processed/claim_inventory.json",
        evidence_integration_path="data/outputs/evidence_integration.json",
        paper_spec_path="data/outputs/paper_spec.json",
        html_output_path="data/outputs/inquiry_paper.html",
        audit_requested=False,
    )

    assert result == report_path
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["stage"] == "assemble_paper"
    assert report["started_at"] == "2026-05-08T12:00:00+00:00"
    assert report["source_registry_path"] == "data/processed/source_registry.json"
    assert report["claim_inventory_path"] == "data/processed/claim_inventory.json"
    assert report["evidence_integration_path"] == "data/outputs/evidence_integration.json"
    assert report["paper_spec_path"] == "data/outputs/paper_spec.json"
    assert report["html_output_path"] == "data/outputs/inquiry_paper.html"
    assert report["audit_requested"] is False
    assert report["audit_passed"] is None
    assert report["audit_report_path"] is None
    assert report["status"] == "completed"


def test_write_paper_assembly_run_report_with_audit(tmp_path: Path) -> None:
    report_path = tmp_path / "paper_assembly_run_report.json"

    write_paper_assembly_run_report(
        output_path=report_path,
        started_at="2026-05-08T12:00:00+00:00",
        source_registry_path="data/processed/source_registry.json",
        claim_inventory_path="data/processed/claim_inventory.json",
        evidence_integration_path="data/outputs/evidence_integration.json",
        paper_spec_path="data/outputs/paper_spec.json",
        html_output_path="data/outputs/inquiry_paper.html",
        audit_requested=True,
        audit_report_path="data/outputs/html_audit_report.json",
        audit_passed=True,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["audit_requested"] is True
    assert report["audit_passed"] is True
    assert report["audit_report_path"] == "data/outputs/html_audit_report.json"


def test_write_paper_assembly_run_report_requires_audit_result_when_audit_requested(
    tmp_path: Path,
) -> None:
    with pytest.raises(PaperRunReportError, match="audit_passed must be provided"):
        write_paper_assembly_run_report(
            output_path=tmp_path / "report.json",
            started_at="2026-05-08T12:00:00+00:00",
            source_registry_path="data/processed/source_registry.json",
            claim_inventory_path="data/processed/claim_inventory.json",
            evidence_integration_path="data/outputs/evidence_integration.json",
            paper_spec_path="data/outputs/paper_spec.json",
            html_output_path="data/outputs/inquiry_paper.html",
            audit_requested=True,
        )


def test_write_paper_assembly_run_report_rejects_audit_result_when_audit_not_requested(
    tmp_path: Path,
) -> None:
    with pytest.raises(PaperRunReportError, match="audit_passed cannot be provided"):
        write_paper_assembly_run_report(
            output_path=tmp_path / "report.json",
            started_at="2026-05-08T12:00:00+00:00",
            source_registry_path="data/processed/source_registry.json",
            claim_inventory_path="data/processed/claim_inventory.json",
            evidence_integration_path="data/outputs/evidence_integration.json",
            paper_spec_path="data/outputs/paper_spec.json",
            html_output_path="data/outputs/inquiry_paper.html",
            audit_requested=False,
            audit_passed=True,
        )