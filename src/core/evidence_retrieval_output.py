from __future__ import annotations

from typing import Any

from src.core.evidence_retrieval import EvidenceRecord


VALID_BALANCE_SCORES = {
    "balanced",
    "supportive_skewed",
    "contrary_skewed",
    "insufficient",
}


def _require_keys(payload: dict[str, Any], required_keys: set[str], context: str) -> None:
    missing = required_keys - set(payload.keys())

    if missing:
        raise ValueError(f"{context} missing required keys: {sorted(missing)}")


def validate_evidence_record_payload(record_payload: dict[str, Any]) -> None:
    _require_keys(
        record_payload,
        {
            "claim_id",
            "title",
            "source",
            "tier",
            "stance",
            "identifier",
        },
        "evidence record",
    )

    record = EvidenceRecord(
        claim_id=str(record_payload["claim_id"]),
        title=str(record_payload["title"]),
        source=str(record_payload["source"]),
        tier=record_payload["tier"],
        stance=record_payload["stance"],
        identifier=str(record_payload["identifier"]),
        url=record_payload.get("url"),
        doi=record_payload.get("doi"),
        abstract=record_payload.get("abstract"),
        year=record_payload.get("year"),
    )

    record.validate()


def validate_retrieval_result_payload(result_payload: dict[str, Any]) -> None:
    _require_keys(
        result_payload,
        {
            "claim_id",
            "queries_executed",
            "evidence_records",
            "balance_score",
        },
        "retrieval result",
    )

    if not isinstance(result_payload["queries_executed"], list):
        raise ValueError("retrieval result queries_executed must be a list.")

    if not isinstance(result_payload["evidence_records"], list):
        raise ValueError("retrieval result evidence_records must be a list.")

    balance_score = result_payload["balance_score"]

    if balance_score not in VALID_BALANCE_SCORES:
        raise ValueError(f"Invalid balance_score: {balance_score}")

    for record_payload in result_payload["evidence_records"]:
        if not isinstance(record_payload, dict):
            raise ValueError("Each evidence record must be an object.")

        validate_evidence_record_payload(record_payload)


def validate_retrieval_summary_payload(summary_payload: dict[str, Any]) -> None:
    _require_keys(
        summary_payload,
        {
            "total_claims",
            "total_evidence_records",
            "balance_counts",
            "balance_rate",
            "claims_needing_review",
            "sources_seen",
            "publishable_for_week5",
        },
        "retrieval summary",
    )

    if not isinstance(summary_payload["balance_counts"], dict):
        raise ValueError("retrieval summary balance_counts must be an object.")

    for score in VALID_BALANCE_SCORES:
        if score not in summary_payload["balance_counts"]:
            raise ValueError(f"retrieval summary missing balance count for: {score}")

    if not isinstance(summary_payload["claims_needing_review"], list):
        raise ValueError("claims_needing_review must be a list.")

    if not isinstance(summary_payload["sources_seen"], list):
        raise ValueError("sources_seen must be a list.")

    balance_rate = summary_payload["balance_rate"]

    if not isinstance(balance_rate, int | float):
        raise ValueError("balance_rate must be numeric.")

    if balance_rate < 0 or balance_rate > 1:
        raise ValueError("balance_rate must be between 0 and 1.")


def validate_evidence_retrieval_output(payload: dict[str, Any]) -> None:
    """
    Validate the full Week 5 evidence retrieval artifact.

    This protects later stages from quietly consuming malformed retrieval data.
    """
    _require_keys(
        payload,
        {
            "source_claim_inventory",
            "retrieval_count",
            "dry_run",
            "source",
            "per_query_limit",
            "retrieval_summary",
            "retrieval_results",
        },
        "evidence retrieval output",
    )

    if not isinstance(payload["retrieval_results"], list):
        raise ValueError("retrieval_results must be a list.")

    if payload["retrieval_count"] != len(payload["retrieval_results"]):
        raise ValueError("retrieval_count must match retrieval_results length.")

    validate_retrieval_summary_payload(payload["retrieval_summary"])

    for result_payload in payload["retrieval_results"]:
        if not isinstance(result_payload, dict):
            raise ValueError("Each retrieval result must be an object.")

        validate_retrieval_result_payload(result_payload)