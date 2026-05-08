from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


REQUIRED_ADJUDICATION_FIELDS = {
    "claim_id",
    "speaker_claim_summary",
    "evidence_summary",
    "verdict",
    "confidence",
    "narrative",
    "interactive_payload",
    "narrative_generation",
}

REQUIRED_EVIDENCE_SUMMARY_BUCKETS = {
    "supports",
    "complicates",
    "contradicts",
    "qualifies",
}

REQUIRED_INTERACTIVE_PAYLOAD_BUCKETS = {
    "supporting_sources",
    "contrary_sources",
    "qualifying_sources",
    "complicating_sources",
}

ALLOWED_VERDICTS = {
    "well_supported",
    "well_supported_with_qualifications",
    "mixed_or_contested",
    "contradicted_by_evidence",
    "insufficient_evidence",
    "requires_manual_review",
}

ALLOWED_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}


@dataclass(frozen=True)
class AdjudicationValidationIssue:
    claim_id: str | None
    field: str
    message: str


@dataclass(frozen=True)
class AdjudicationValidationReport:
    is_valid: bool
    total_adjudications: int
    issue_count: int
    issues: list[dict[str, Any]]


def _add_issue(
    issues: list[AdjudicationValidationIssue],
    *,
    claim_id: str | None,
    field: str,
    message: str,
) -> None:
    issues.append(
        AdjudicationValidationIssue(
            claim_id=claim_id,
            field=field,
            message=message,
        )
    )


def validate_evidence_summary(
    evidence_summary: Any,
    *,
    claim_id: str | None,
    issues: list[AdjudicationValidationIssue],
) -> None:
    if not isinstance(evidence_summary, Mapping):
        _add_issue(
            issues,
            claim_id=claim_id,
            field="evidence_summary",
            message="evidence_summary must be an object.",
        )
        return

    missing_buckets = REQUIRED_EVIDENCE_SUMMARY_BUCKETS - set(evidence_summary.keys())

    for bucket in sorted(missing_buckets):
        _add_issue(
            issues,
            claim_id=claim_id,
            field=f"evidence_summary.{bucket}",
            message="Missing evidence summary bucket.",
        )

    for bucket in REQUIRED_EVIDENCE_SUMMARY_BUCKETS:
        value = evidence_summary.get(bucket)

        if value is None:
            continue

        if not isinstance(value, list):
            _add_issue(
                issues,
                claim_id=claim_id,
                field=f"evidence_summary.{bucket}",
                message="Evidence summary bucket must be a list.",
            )
            continue

        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                _add_issue(
                    issues,
                    claim_id=claim_id,
                    field=f"evidence_summary.{bucket}[{index}]",
                    message="Evidence summary entries must be non-empty strings.",
                )


def validate_interactive_payload(
    interactive_payload: Any,
    *,
    claim_id: str | None,
    issues: list[AdjudicationValidationIssue],
) -> None:
    if not isinstance(interactive_payload, Mapping):
        _add_issue(
            issues,
            claim_id=claim_id,
            field="interactive_payload",
            message="interactive_payload must be an object.",
        )
        return

    missing_buckets = REQUIRED_INTERACTIVE_PAYLOAD_BUCKETS - set(interactive_payload.keys())

    for bucket in sorted(missing_buckets):
        _add_issue(
            issues,
            claim_id=claim_id,
            field=f"interactive_payload.{bucket}",
            message="Missing interactive payload bucket.",
        )

    for bucket in REQUIRED_INTERACTIVE_PAYLOAD_BUCKETS:
        value = interactive_payload.get(bucket)

        if value is None:
            continue

        if not isinstance(value, list):
            _add_issue(
                issues,
                claim_id=claim_id,
                field=f"interactive_payload.{bucket}",
                message="Interactive payload bucket must be a list.",
            )
            continue

        for index, item in enumerate(value):
            if not isinstance(item, Mapping):
                _add_issue(
                    issues,
                    claim_id=claim_id,
                    field=f"interactive_payload.{bucket}[{index}]",
                    message="Interactive payload entries must be objects.",
                )


def validate_narrative_generation(
    narrative_generation: Any,
    *,
    claim_id: str | None,
    issues: list[AdjudicationValidationIssue],
) -> None:
    if not isinstance(narrative_generation, Mapping):
        _add_issue(
            issues,
            claim_id=claim_id,
            field="narrative_generation",
            message="narrative_generation must be an object.",
        )
        return

    used_llm = narrative_generation.get("used_llm")

    if not isinstance(used_llm, bool):
        _add_issue(
            issues,
            claim_id=claim_id,
            field="narrative_generation.used_llm",
            message="used_llm must be a boolean.",
        )

    fallback_reason = narrative_generation.get("fallback_reason")

    if fallback_reason is not None and not isinstance(fallback_reason, str):
        _add_issue(
            issues,
            claim_id=claim_id,
            field="narrative_generation.fallback_reason",
            message="fallback_reason must be null or a string.",
        )


def validate_adjudication_record(
    adjudication: Mapping[str, Any],
    *,
    issues: list[AdjudicationValidationIssue],
) -> None:
    claim_id_value = adjudication.get("claim_id")
    claim_id = claim_id_value if isinstance(claim_id_value, str) else None

    missing_fields = REQUIRED_ADJUDICATION_FIELDS - set(adjudication.keys())

    for field in sorted(missing_fields):
        _add_issue(
            issues,
            claim_id=claim_id,
            field=field,
            message="Missing required adjudication field.",
        )

    if not isinstance(claim_id_value, str) or not claim_id_value.strip():
        _add_issue(
            issues,
            claim_id=claim_id,
            field="claim_id",
            message="claim_id must be a non-empty string.",
        )

    speaker_claim_summary = adjudication.get("speaker_claim_summary")
    if not isinstance(speaker_claim_summary, str) or not speaker_claim_summary.strip():
        _add_issue(
            issues,
            claim_id=claim_id,
            field="speaker_claim_summary",
            message="speaker_claim_summary must be a non-empty string.",
        )

    verdict = adjudication.get("verdict")
    if verdict not in ALLOWED_VERDICTS:
        _add_issue(
            issues,
            claim_id=claim_id,
            field="verdict",
            message="verdict is not in the allowed verdict taxonomy.",
        )

    confidence = adjudication.get("confidence")
    if confidence not in ALLOWED_CONFIDENCE_LEVELS:
        _add_issue(
            issues,
            claim_id=claim_id,
            field="confidence",
            message="confidence is not in the allowed confidence taxonomy.",
        )

    narrative = adjudication.get("narrative")
    if not isinstance(narrative, str) or not narrative.strip():
        _add_issue(
            issues,
            claim_id=claim_id,
            field="narrative",
            message="narrative must be a non-empty string.",
        )

    validate_evidence_summary(
        adjudication.get("evidence_summary"),
        claim_id=claim_id,
        issues=issues,
    )

    validate_interactive_payload(
        adjudication.get("interactive_payload"),
        claim_id=claim_id,
        issues=issues,
    )

    validate_narrative_generation(
        adjudication.get("narrative_generation"),
        claim_id=claim_id,
        issues=issues,
    )


def validate_adjudications_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    adjudications = payload.get("adjudications")

    issues: list[AdjudicationValidationIssue] = []

    if not isinstance(adjudications, list):
        _add_issue(
            issues,
            claim_id=None,
            field="adjudications",
            message="Payload must contain an adjudications list.",
        )

        report = AdjudicationValidationReport(
            is_valid=False,
            total_adjudications=0,
            issue_count=len(issues),
            issues=[asdict(issue) for issue in issues],
        )
        return asdict(report)

    for adjudication in adjudications:
        if not isinstance(adjudication, Mapping):
            _add_issue(
                issues,
                claim_id=None,
                field="adjudications[]",
                message="Each adjudication must be an object.",
            )
            continue

        validate_adjudication_record(adjudication, issues=issues)

    report = AdjudicationValidationReport(
        is_valid=len(issues) == 0,
        total_adjudications=len(adjudications),
        issue_count=len(issues),
        issues=[asdict(issue) for issue in issues],
    )

    return asdict(report)
