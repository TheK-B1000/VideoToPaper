from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REQUIRED_SECTION_IDS = [
    "perspective",
    "claims",
    "evidence",
    "agreement",
    "complexity",
    "limitations",
    "reading",
    "references",
]


@dataclass(frozen=True)
class HtmlAuditFinding:
    code: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class HtmlAuditReport:
    html_path: str
    passed: bool
    checks_run: int
    findings: list[HtmlAuditFinding]

    def to_dict(self) -> dict[str, Any]:
        return {
            "html_path": self.html_path,
            "passed": self.passed,
            "checks_run": self.checks_run,
            "findings": [asdict(finding) for finding in self.findings],
        }


class HtmlAuditError(ValueError):
    """Raised when the HTML paper audit cannot run."""


def audit_html_paper(
    *,
    html_path: str | Path,
    paper_spec_path: str | Path,
    report_output_path: str | Path | None = None,
) -> HtmlAuditReport:
    """
    Audit a generated Week 8 HTML paper against the paper spec.

    This is not the full Week 10 evaluation harness. It is a Week 8 structural
    audit that checks whether the assembled artifact keeps the promises of the
    HTML paper assembly module.
    """
    html_target = Path(html_path)
    spec_target = Path(paper_spec_path)

    if not html_target.exists():
        raise HtmlAuditError(f"HTML paper does not exist: {html_target}")

    if not spec_target.exists():
        raise HtmlAuditError(f"Paper spec does not exist: {spec_target}")

    html = html_target.read_text(encoding="utf-8")
    spec = _load_json_object(spec_target)

    findings: list[HtmlAuditFinding] = []

    findings.extend(_check_required_sections(html))
    findings.extend(_check_claim_clip_embeds(html, spec))
    findings.extend(_check_privacy_respecting_embeds(html))
    findings.extend(_check_reference_resolution(html, spec))
    findings.extend(_check_limitations_section(html))

    report = HtmlAuditReport(
        html_path=str(html_target),
        passed=not any(finding.severity == "error" for finding in findings),
        checks_run=5,
        findings=findings,
    )

    if report_output_path is not None:
        output_target = Path(report_output_path)
        output_target.parent.mkdir(parents=True, exist_ok=True)
        output_target.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    return report


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HtmlAuditError(f"Invalid paper spec JSON: {path}") from exc

    if not isinstance(data, dict):
        raise HtmlAuditError("Paper spec must be a JSON object.")

    return data


def _check_required_sections(html: str) -> list[HtmlAuditFinding]:
    findings: list[HtmlAuditFinding] = []

    for section_id in REQUIRED_SECTION_IDS:
        if f'id="{section_id}"' not in html:
            findings.append(
                HtmlAuditFinding(
                    code="missing_required_section",
                    message=f'Missing required section id="{section_id}".',
                )
            )

    return findings


def _check_claim_clip_embeds(
    html: str,
    spec: dict[str, Any],
) -> list[HtmlAuditFinding]:
    findings: list[HtmlAuditFinding] = []
    claims = spec.get("claims", [])

    if not isinstance(claims, list):
        return [
            HtmlAuditFinding(
                code="invalid_claims_spec",
                message="Paper spec claims field must be a list.",
            )
        ]

    iframe_sources = _extract_iframe_sources(html)

    for claim in claims:
        if not isinstance(claim, dict):
            findings.append(
                HtmlAuditFinding(
                    code="invalid_claim_spec",
                    message="Every claim in the paper spec must be an object.",
                )
            )
            continue

        claim_id = str(claim.get("claim_id", "")).strip()

        if not claim_id:
            findings.append(
                HtmlAuditFinding(
                    code="missing_claim_id",
                    message="A claim is missing claim_id.",
                )
            )
            continue

        if f'id="{claim_id}"' not in html:
            findings.append(
                HtmlAuditFinding(
                    code="missing_claim_card",
                    message=f"Missing rendered claim card for {claim_id}.",
                )
            )

        expected_start = _rounded_second(claim.get("anchor_clip_start"))
        expected_end = _rounded_second(claim.get("anchor_clip_end"))

        if expected_start is None or expected_end is None:
            findings.append(
                HtmlAuditFinding(
                    code="invalid_claim_timing",
                    message=f"Claim {claim_id} has invalid timing fields.",
                )
            )
            continue

        has_matching_iframe = any(
            f"start={expected_start}" in src and f"end={expected_end}" in src
            for src in iframe_sources
        )

        if not has_matching_iframe:
            findings.append(
                HtmlAuditFinding(
                    code="missing_claim_iframe",
                    message=(
                        f"Claim {claim_id} is missing an iframe with "
                        f"start={expected_start} and end={expected_end}."
                    ),
                )
            )

    return findings


def _check_privacy_respecting_embeds(html: str) -> list[HtmlAuditFinding]:
    findings: list[HtmlAuditFinding] = []
    iframe_sources = _extract_iframe_sources(html)

    for src in iframe_sources:
        if "youtube-nocookie.com/embed/" not in src:
            findings.append(
                HtmlAuditFinding(
                    code="non_privacy_respecting_embed",
                    message=f"Embed does not use youtube-nocookie.com: {src}",
                )
            )

        if "rel=0" not in src:
            findings.append(
                HtmlAuditFinding(
                    code="embed_missing_rel_zero",
                    message=f"Embed is missing rel=0: {src}",
                    severity="warning",
                )
            )

    return findings


def _check_reference_resolution(
    html: str,
    spec: dict[str, Any],
) -> list[HtmlAuditFinding]:
    findings: list[HtmlAuditFinding] = []
    evidence_records = spec.get("evidence_records", [])

    if not isinstance(evidence_records, list):
        return [
            HtmlAuditFinding(
                code="invalid_evidence_spec",
                message="Paper spec evidence_records field must be a list.",
            )
        ]

    for record in evidence_records:
        if not isinstance(record, dict):
            findings.append(
                HtmlAuditFinding(
                    code="invalid_evidence_record",
                    message="Every evidence record must be an object.",
                )
            )
            continue

        evidence_id = str(record.get("evidence_id", "")).strip()
        title = str(record.get("title", "")).strip()
        url = str(record.get("url", "")).strip()

        if not evidence_id:
            findings.append(
                HtmlAuditFinding(
                    code="missing_evidence_id",
                    message="Evidence record is missing evidence_id.",
                )
            )
            continue

        if f'id="{evidence_id}"' not in html:
            findings.append(
                HtmlAuditFinding(
                    code="missing_reference_id",
                    message=f"Reference list is missing evidence id {evidence_id}.",
                )
            )

        if title and title not in html:
            findings.append(
                HtmlAuditFinding(
                    code="missing_reference_title",
                    message=f"Reference title is missing from HTML: {title}",
                )
            )

        if url and url not in html:
            findings.append(
                HtmlAuditFinding(
                    code="missing_reference_url",
                    message=f"Reference URL is missing from HTML: {url}",
                )
            )

    return findings


def _check_limitations_section(html: str) -> list[HtmlAuditFinding]:
    if 'id="limitations"' not in html:
        return [
            HtmlAuditFinding(
                code="missing_limitations_section",
                message="Limitations section is required even when empty.",
            )
        ]

    if "Open Questions" not in html and "Limitations" not in html:
        return [
            HtmlAuditFinding(
                code="limitations_section_unlabeled",
                message="Limitations section exists but is not clearly labeled.",
            )
        ]

    return []


def _extract_iframe_sources(html: str) -> list[str]:
    return re.findall(r'<iframe[^>]+src="([^"]+)"', html, flags=re.IGNORECASE)


def _rounded_second(value: Any) -> int | None:
    if not isinstance(value, int | float):
        return None

    return int(round(value))
