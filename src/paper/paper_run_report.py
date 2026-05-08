from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PaperAssemblyRunReport:
    stage: str
    started_at: str
    finished_at: str
    source_registry_path: str
    claim_inventory_path: str
    evidence_integration_path: str
    paper_spec_path: str
    html_output_path: str
    audit_report_path: str | None
    audit_requested: bool
    audit_passed: bool | None
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PaperRunReportError(ValueError):
    """Raised when a paper assembly run report cannot be written."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_paper_assembly_run_report(
    *,
    output_path: str | Path,
    started_at: str,
    source_registry_path: str | Path,
    claim_inventory_path: str | Path,
    evidence_integration_path: str | Path,
    paper_spec_path: str | Path,
    html_output_path: str | Path,
    audit_requested: bool,
    audit_report_path: str | Path | None = None,
    audit_passed: bool | None = None,
    status: str = "completed",
) -> Path:
    """
    Write a Week 8 paper assembly run report.

    This records the artifact trail for one paper assembly run:
    upstream inputs, generated paper spec, generated HTML, and optional audit result.
    """
    if audit_requested and audit_passed is None:
        raise PaperRunReportError(
            "audit_passed must be provided when audit_requested is True."
        )

    if audit_passed is not None and not audit_requested:
        raise PaperRunReportError(
            "audit_passed cannot be provided when audit_requested is False."
        )

    report = PaperAssemblyRunReport(
        stage="assemble_paper",
        started_at=started_at,
        finished_at=utc_now_iso(),
        source_registry_path=str(source_registry_path),
        claim_inventory_path=str(claim_inventory_path),
        evidence_integration_path=str(evidence_integration_path),
        paper_spec_path=str(paper_spec_path),
        html_output_path=str(html_output_path),
        audit_report_path=str(audit_report_path) if audit_report_path else None,
        audit_requested=audit_requested,
        audit_passed=audit_passed,
        status=status,
    )

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    return target