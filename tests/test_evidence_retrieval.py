import json

import pytest

from src.core.evidence_retrieval import (
    EvidenceRecord,
    RetrievalCache,
    build_evidence_result,
    generate_balanced_queries,
    score_evidence_balance,
)


def test_generate_balanced_queries_includes_support_and_contrary_searches():
    queries = generate_balanced_queries(
        "non-stationarity limits single-agent reinforcement learning in multi-agent settings"
    )

    assert len(queries) == 4
    assert any("supporting" in query for query in queries)
    assert any("against" in query for query in queries)
    assert any("limitations" in query for query in queries)


def test_generate_balanced_queries_rejects_empty_claim_text():
    with pytest.raises(ValueError, match="claim_text cannot be empty"):
        generate_balanced_queries("   ")


def test_evidence_record_requires_resolvable_identifier():
    record = EvidenceRecord(
        claim_id="claim_001",
        title="A useful paper",
        source="OpenAlex",
        tier=1,
        stance="supports",
        identifier="",
    )

    with pytest.raises(ValueError, match="identifier"):
        record.validate()


def test_balance_score_flags_balanced_records():
    records = [
        EvidenceRecord(
            claim_id="claim_001",
            title="Supporting paper",
            source="OpenAlex",
            tier=1,
            stance="supports",
            identifier="doi:10.123/support",
            doi="10.123/support",
        ),
        EvidenceRecord(
            claim_id="claim_001",
            title="Qualifying paper",
            source="OpenAlex",
            tier=1,
            stance="qualifies",
            identifier="doi:10.123/qualify",
            doi="10.123/qualify",
        ),
    ]

    assert score_evidence_balance(records) == "balanced"


def test_balance_score_flags_supportive_skew():
    records = [
        EvidenceRecord(
            claim_id="claim_001",
            title="Supporting paper",
            source="OpenAlex",
            tier=1,
            stance="supports",
            identifier="doi:10.123/support",
            doi="10.123/support",
        )
    ]

    assert score_evidence_balance(records) == "supportive_skewed"


def test_balance_score_flags_contrary_skew():
    records = [
        EvidenceRecord(
            claim_id="claim_001",
            title="Contrary paper",
            source="OpenAlex",
            tier=1,
            stance="contradicts",
            identifier="doi:10.123/against",
            doi="10.123/against",
        )
    ]

    assert score_evidence_balance(records) == "contrary_skewed"


def test_balance_score_flags_empty_records_as_insufficient():
    assert score_evidence_balance([]) == "insufficient"


def test_retrieval_cache_prevents_duplicate_payload_work(tmp_path):
    cache = RetrievalCache(cache_dir=tmp_path)

    key = "openalex::non-stationarity MARL"
    payload = {
        "results": [
            {
                "title": "Multi-agent reinforcement learning and non-stationarity",
                "doi": "10.123/example",
            }
        ]
    }

    assert cache.get(key) is None

    cache.set(key, payload)

    cached = cache.get(key)

    assert cached == payload


def test_build_evidence_result_serializes_records():
    records = [
        EvidenceRecord(
            claim_id="claim_001",
            title="Supporting paper",
            source="OpenAlex",
            tier=1,
            stance="supports",
            identifier="doi:10.123/support",
            doi="10.123/support",
            year=2019,
        ),
        EvidenceRecord(
            claim_id="claim_001",
            title="Complicating paper",
            source="Semantic Scholar",
            tier=1,
            stance="complicates",
            identifier="corpus:12345",
            url="https://example.com/paper",
            year=2021,
        ),
    ]

    result = build_evidence_result(
        claim_id="claim_001",
        claim_text="non-stationarity limits single-agent reinforcement learning in multi-agent settings",
        records=records,
    )

    result_dict = result.to_dict()

    assert result_dict["claim_id"] == "claim_001"
    assert result_dict["balance_score"] == "balanced"
    assert len(result_dict["queries_executed"]) == 4
    assert len(result_dict["evidence_records"]) == 2
    assert result_dict["query_traces"] == []
    assert result_dict["retrieval_exhausted_query_count"] == 0

    json.dumps(result_dict)