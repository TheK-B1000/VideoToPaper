import json

import pytest

from src.core.evidence_retrieval import RetrievalCache
from src.core.openalex_client import (
    OpenAlexClient,
    _reconstruct_abstract,
    openalex_work_to_evidence_record,
    parse_openalex_work,
)


def test_reconstruct_abstract_from_inverted_index():
    abstract = _reconstruct_abstract(
        {
            "Multi-agent": [0],
            "reinforcement": [1],
            "learning": [2],
            "is": [3],
            "non-stationary": [4],
        }
    )

    assert abstract == "Multi-agent reinforcement learning is non-stationary"


def test_reconstruct_abstract_returns_none_for_missing_index():
    assert _reconstruct_abstract(None) is None


def test_parse_openalex_work_extracts_core_metadata():
    raw_work = {
        "id": "https://openalex.org/W123",
        "title": "Multi-Agent Reinforcement Learning: A Selective Overview",
        "publication_year": 2019,
        "doi": "https://doi.org/10.1234/example",
        "primary_location": {
            "landing_page_url": "https://example.com/paper"
        },
        "abstract_inverted_index": {
            "Coordination": [0],
            "matters": [1],
        },
    }

    work = parse_openalex_work(raw_work)

    assert work.title == "Multi-Agent Reinforcement Learning: A Selective Overview"
    assert work.openalex_id == "https://openalex.org/W123"
    assert work.publication_year == 2019
    assert work.doi == "10.1234/example"
    assert work.url == "https://example.com/paper"
    assert work.abstract == "Coordination matters"


def test_parse_openalex_work_rejects_missing_title():
    with pytest.raises(ValueError, match="title"):
        parse_openalex_work(
            {
                "id": "https://openalex.org/W123",
                "publication_year": 2019,
            }
        )


def test_parse_openalex_work_rejects_missing_id():
    with pytest.raises(ValueError, match="id"):
        parse_openalex_work(
            {
                "title": "A Paper Without an ID",
                "publication_year": 2019,
            }
        )


def test_openalex_work_converts_to_evidence_record():
    raw_work = {
        "id": "https://openalex.org/W123",
        "title": "Multi-Agent Reinforcement Learning: A Selective Overview",
        "publication_year": 2019,
        "doi": "https://doi.org/10.1234/example",
        "primary_location": {
            "landing_page_url": "https://example.com/paper"
        },
    }

    work = parse_openalex_work(raw_work)

    record = openalex_work_to_evidence_record(
        claim_id="claim_001",
        work=work,
        stance="supports",
        tier=1,
    )

    record.validate()

    assert record.claim_id == "claim_001"
    assert record.source == "OpenAlex"
    assert record.stance == "supports"
    assert record.tier == 1
    assert record.identifier == "10.1234/example"
    assert record.doi == "10.1234/example"


def test_openalex_client_reads_from_cache_without_network(tmp_path):
    cache = RetrievalCache(cache_dir=tmp_path)

    cached_payload = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "title": "Cached MARL Paper",
                "publication_year": 2020,
                "doi": "https://doi.org/10.5555/cached",
                "primary_location": {
                    "landing_page_url": "https://example.com/cached"
                },
            }
        ]
    }

    cache.set("openalex::multi-agent reinforcement learning::per_page=5", cached_payload)

    client = OpenAlexClient(cache=cache)

    results, status = client.search_works("multi-agent reinforcement learning", per_page=5)

    assert status == "ok"
    assert len(results) == 1
    assert results[0].title == "Cached MARL Paper"
    assert results[0].doi == "10.5555/cached"


def test_openalex_client_rejects_empty_query():
    client = OpenAlexClient(cache=RetrievalCache())

    with pytest.raises(ValueError, match="query cannot be empty"):
        client.search_works("   ")


def test_openalex_client_rejects_non_positive_per_page():
    client = OpenAlexClient(cache=RetrievalCache())

    with pytest.raises(ValueError, match="per_page must be positive"):
        client.search_works("multi-agent reinforcement learning", per_page=0)