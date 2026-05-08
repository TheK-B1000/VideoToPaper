import pytest

from src.core.evidence_retrieval_output import (
    validate_evidence_record_payload,
    validate_evidence_retrieval_output,
    validate_retrieval_result_payload,
    validate_retrieval_summary_payload,
)


def _valid_record():
    return {
        "claim_id": "claim_001",
        "title": "A valid academic source",
        "source": "OpenAlex",
        "tier": 1,
        "stance": "supports",
        "identifier": "10.1234/example",
        "doi": "10.1234/example",
        "url": "https://example.com/source",
        "abstract": "A short abstract.",
        "year": 2021,
    }


def _valid_summary():
    return {
        "total_claims": 1,
        "total_evidence_records": 1,
        "balance_counts": {
            "balanced": 1,
            "supportive_skewed": 0,
            "contrary_skewed": 0,
            "insufficient": 0,
        },
        "balance_rate": 1.0,
        "claims_needing_review": [],
        "sources_seen": ["OpenAlex"],
        "publishable_for_week5": True,
    }


def _valid_result():
    return {
        "claim_id": "claim_001",
        "queries_executed": [
            "multi-agent reinforcement learning non-stationarity",
            "evidence supporting multi-agent reinforcement learning non-stationarity",
            "evidence against multi-agent reinforcement learning non-stationarity",
            "limitations qualifications multi-agent reinforcement learning non-stationarity",
        ],
        "evidence_records": [_valid_record()],
        "balance_score": "balanced",
    }


def _valid_output():
    return {
        "source_claim_inventory": "data/processed/claim_inventory.json",
        "retrieval_count": 1,
        "dry_run": False,
        "source": "all",
        "per_query_limit": 1,
        "retrieval_summary": _valid_summary(),
        "retrieval_results": [_valid_result()],
    }


def test_validate_evidence_record_payload_accepts_valid_record():
    validate_evidence_record_payload(_valid_record())


def test_validate_evidence_record_payload_rejects_missing_required_key():
    record = _valid_record()
    del record["identifier"]

    with pytest.raises(ValueError, match="missing required keys"):
        validate_evidence_record_payload(record)


def test_validate_retrieval_result_payload_accepts_valid_result():
    validate_retrieval_result_payload(_valid_result())


def test_validate_retrieval_result_payload_rejects_invalid_balance_score():
    result = _valid_result()
    result["balance_score"] = "vibes_only"

    with pytest.raises(ValueError, match="Invalid balance_score"):
        validate_retrieval_result_payload(result)


def test_validate_retrieval_result_payload_requires_list_of_records():
    result = _valid_result()
    result["evidence_records"] = {}

    with pytest.raises(ValueError, match="evidence_records must be a list"):
        validate_retrieval_result_payload(result)


def test_validate_retrieval_summary_payload_accepts_valid_summary():
    validate_retrieval_summary_payload(_valid_summary())


def test_validate_retrieval_summary_payload_rejects_missing_balance_count():
    summary = _valid_summary()
    del summary["balance_counts"]["insufficient"]

    with pytest.raises(ValueError, match="missing balance count"):
        validate_retrieval_summary_payload(summary)


def test_validate_retrieval_summary_payload_rejects_invalid_balance_rate():
    summary = _valid_summary()
    summary["balance_rate"] = 1.5

    with pytest.raises(ValueError, match="between 0 and 1"):
        validate_retrieval_summary_payload(summary)


def test_validate_evidence_retrieval_output_accepts_valid_output():
    validate_evidence_retrieval_output(_valid_output())


def test_validate_evidence_retrieval_output_rejects_mismatched_count():
    output = _valid_output()
    output["retrieval_count"] = 2

    with pytest.raises(ValueError, match="retrieval_count must match"):
        validate_evidence_retrieval_output(output)


def test_validate_evidence_retrieval_output_rejects_missing_summary():
    output = _valid_output()
    del output["retrieval_summary"]

    with pytest.raises(ValueError, match="missing required keys"):
        validate_evidence_retrieval_output(output)
    