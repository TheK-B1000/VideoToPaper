import pytest

from src.core.evidence_retrieval import RetrievalCache
from src.core.semantic_scholar_client import (
    SemanticScholarClient,
    _extract_doi,
    parse_semantic_scholar_paper,
    semantic_scholar_paper_to_evidence_record,
)


def test_extract_doi_from_external_ids():
    doi = _extract_doi({"DOI": "10.1234/example"})

    assert doi == "10.1234/example"


def test_extract_doi_returns_none_when_missing():
    assert _extract_doi({}) is None
    assert _extract_doi(None) is None


def test_parse_semantic_scholar_paper_extracts_core_metadata():
    raw_paper = {
        "paperId": "abc123",
        "title": "A Survey of Multi-Agent Reinforcement Learning",
        "year": 2019,
        "abstract": "Multi-agent reinforcement learning studies learning in shared environments.",
        "url": "https://www.semanticscholar.org/paper/abc123",
        "externalIds": {
            "DOI": "10.5555/example"
        },
        "citationCount": 42,
    }

    paper = parse_semantic_scholar_paper(raw_paper)

    assert paper.paper_id == "abc123"
    assert paper.title == "A Survey of Multi-Agent Reinforcement Learning"
    assert paper.year == 2019
    assert paper.abstract.startswith("Multi-agent")
    assert paper.url == "https://www.semanticscholar.org/paper/abc123"
    assert paper.doi == "10.5555/example"
    assert paper.citation_count == 42


def test_parse_semantic_scholar_paper_rejects_missing_title():
    with pytest.raises(ValueError, match="title"):
        parse_semantic_scholar_paper(
            {
                "paperId": "abc123",
                "year": 2019,
            }
        )


def test_parse_semantic_scholar_paper_rejects_missing_paper_id():
    with pytest.raises(ValueError, match="paperId"):
        parse_semantic_scholar_paper(
            {
                "title": "Paper Without ID",
                "year": 2019,
            }
        )


def test_semantic_scholar_paper_converts_to_evidence_record_with_doi():
    raw_paper = {
        "paperId": "abc123",
        "title": "A Survey of Multi-Agent Reinforcement Learning",
        "year": 2019,
        "abstract": "MARL survey abstract.",
        "url": "https://www.semanticscholar.org/paper/abc123",
        "externalIds": {
            "DOI": "10.5555/example"
        },
        "citationCount": 42,
    }

    paper = parse_semantic_scholar_paper(raw_paper)

    record = semantic_scholar_paper_to_evidence_record(
        claim_id="claim_001",
        paper=paper,
        stance="supports",
        tier=1,
    )

    record.validate()

    assert record.claim_id == "claim_001"
    assert record.source == "Semantic Scholar"
    assert record.identifier == "10.5555/example"
    assert record.doi == "10.5555/example"
    assert record.stance == "supports"
    assert record.tier == 1


def test_semantic_scholar_paper_converts_to_evidence_record_without_doi():
    raw_paper = {
        "paperId": "abc123",
        "title": "A Paper Without DOI",
        "year": 2021,
        "abstract": "No DOI here.",
        "url": "https://www.semanticscholar.org/paper/abc123",
        "externalIds": {},
        "citationCount": 5,
    }

    paper = parse_semantic_scholar_paper(raw_paper)

    record = semantic_scholar_paper_to_evidence_record(
        claim_id="claim_002",
        paper=paper,
        stance="qualifies",
        tier=1,
    )

    record.validate()

    assert record.identifier == "semantic_scholar:abc123"
    assert record.doi is None


def test_semantic_scholar_client_reads_from_cache_without_network(tmp_path):
    cache = RetrievalCache(cache_dir=tmp_path)

    cached_payload = {
        "data": [
            {
                "paperId": "abc123",
                "title": "Cached Semantic Scholar Paper",
                "year": 2020,
                "abstract": "Cached abstract.",
                "url": "https://www.semanticscholar.org/paper/abc123",
                "externalIds": {
                    "DOI": "10.7777/cached"
                },
                "citationCount": 10,
            }
        ]
    }

    cache.set(
        "semantic_scholar::multi-agent reinforcement learning::limit=5",
        cached_payload,
    )

    client = SemanticScholarClient(cache=cache)

    results = client.search_papers("multi-agent reinforcement learning", limit=5)

    assert len(results) == 1
    assert results[0].title == "Cached Semantic Scholar Paper"
    assert results[0].doi == "10.7777/cached"


def test_semantic_scholar_client_rejects_empty_query():
    client = SemanticScholarClient(cache=RetrievalCache())

    with pytest.raises(ValueError, match="query cannot be empty"):
        client.search_papers("   ")


def test_semantic_scholar_client_rejects_non_positive_limit():
    client = SemanticScholarClient(cache=RetrievalCache())

    with pytest.raises(ValueError, match="limit must be positive"):
        client.search_papers("multi-agent reinforcement learning", limit=0)