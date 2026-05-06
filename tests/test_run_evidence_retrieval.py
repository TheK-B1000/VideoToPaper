import pytest

from src.core.openalex_client import OpenAlexWork
from src.core.semantic_scholar_client import SemanticScholarPaper
from src.pipelines.run_evidence_retrieval import (
    ClaimForRetrieval,
    EvidenceRetrievalPipeline,
    _dedupe_records,
    _infer_stance_from_query,
)


class FakeOpenAlexClient:
    def search_works(self, query: str, *, per_page: int = 3):
        return [
            OpenAlexWork(
                title=f"OpenAlex result for {query}",
                openalex_id=f"https://openalex.org/{query.replace(' ', '_')}",
                publication_year=2020,
                doi=f"10.1234/{abs(hash(query))}",
                url="https://example.com/openalex",
                abstract="A test abstract.",
            )
        ]


class FakeSemanticScholarClient:
    def search_papers(self, query: str, *, limit: int = 3):
        return [
            SemanticScholarPaper(
                title=f"Semantic Scholar result for {query}",
                paper_id=f"paper-{abs(hash(query))}",
                year=2021,
                abstract="A test abstract.",
                url="https://example.com/semantic-scholar",
                doi=f"10.5678/{abs(hash(query))}",
                citation_count=12,
            )
        ]


def test_infer_stance_from_query_supports():
    assert _infer_stance_from_query("evidence supporting multi-agent RL") == "supports"


def test_infer_stance_from_query_contradicts():
    assert _infer_stance_from_query("evidence against multi-agent RL") == "contradicts"


def test_infer_stance_from_query_qualifies():
    assert _infer_stance_from_query("limitations qualifications multi-agent RL") == "qualifies"


def test_claim_for_retrieval_rejects_empty_claim_id():
    claim = ClaimForRetrieval(
        claim_id="",
        claim_text="A real claim.",
        claim_type="empirical_technical",
        verification_strategy="literature_review",
    )

    with pytest.raises(ValueError, match="claim_id"):
        claim.validate()


def test_claim_for_retrieval_rejects_empty_claim_text():
    claim = ClaimForRetrieval(
        claim_id="claim_001",
        claim_text="   ",
        claim_type="empirical_technical",
        verification_strategy="literature_review",
    )

    with pytest.raises(ValueError, match="claim_text"):
        claim.validate()


def test_pipeline_returns_insufficient_for_non_literature_review_claim():
    pipeline = EvidenceRetrievalPipeline(
        openalex_client=FakeOpenAlexClient(),
        semantic_scholar_client=FakeSemanticScholarClient(),
    )

    claim = ClaimForRetrieval(
        claim_id="claim_001",
        claim_text="This is a moral claim.",
        claim_type="normative",
        verification_strategy="argument_analysis",
    )

    result = pipeline.retrieve_for_claim(claim)

    assert result.claim_id == "claim_001"
    assert result.queries_executed == []
    assert result.evidence_records == []
    assert result.balance_score == "insufficient"


def test_pipeline_retrieves_from_both_sources_and_scores_balance():
    pipeline = EvidenceRetrievalPipeline(
        openalex_client=FakeOpenAlexClient(),
        semantic_scholar_client=FakeSemanticScholarClient(),
    )

    claim = ClaimForRetrieval(
        claim_id="claim_001",
        claim_text="non-stationarity limits single-agent reinforcement learning in multi-agent settings",
        claim_type="empirical_technical",
        verification_strategy="literature_review",
    )

    result = pipeline.retrieve_for_claim(claim, source="all", per_query_limit=2)

    assert result.claim_id == "claim_001"
    assert len(result.queries_executed) == 4
    assert len(result.evidence_records) == 8
    assert result.balance_score == "balanced"

    sources = {record.source for record in result.evidence_records}
    stances = {record.stance for record in result.evidence_records}

    assert sources == {"OpenAlex", "Semantic Scholar"}
    assert "supports" in stances
    assert "contradicts" in stances
    assert "qualifies" in stances


def test_pipeline_can_use_openalex_only():
    pipeline = EvidenceRetrievalPipeline(
        openalex_client=FakeOpenAlexClient(),
        semantic_scholar_client=FakeSemanticScholarClient(),
    )

    claim = ClaimForRetrieval(
        claim_id="claim_001",
        claim_text="multi-agent systems require coordination",
        claim_type="empirical_technical",
        verification_strategy="literature_review",
    )

    result = pipeline.retrieve_for_claim(claim, source="openalex", per_query_limit=1)

    assert len(result.evidence_records) == 4
    assert {record.source for record in result.evidence_records} == {"OpenAlex"}


def test_pipeline_can_use_semantic_scholar_only():
    pipeline = EvidenceRetrievalPipeline(
        openalex_client=FakeOpenAlexClient(),
        semantic_scholar_client=FakeSemanticScholarClient(),
    )

    claim = ClaimForRetrieval(
        claim_id="claim_001",
        claim_text="multi-agent systems require coordination",
        claim_type="empirical_technical",
        verification_strategy="literature_review",
    )

    result = pipeline.retrieve_for_claim(
        claim,
        source="semantic_scholar",
        per_query_limit=1,
    )

    assert len(result.evidence_records) == 4
    assert {record.source for record in result.evidence_records} == {"Semantic Scholar"}


def test_pipeline_rejects_non_positive_per_query_limit():
    pipeline = EvidenceRetrievalPipeline(
        openalex_client=FakeOpenAlexClient(),
        semantic_scholar_client=FakeSemanticScholarClient(),
    )

    claim = ClaimForRetrieval(
        claim_id="claim_001",
        claim_text="multi-agent systems require coordination",
        claim_type="empirical_technical",
        verification_strategy="literature_review",
    )

    with pytest.raises(ValueError, match="per_query_limit"):
        pipeline.retrieve_for_claim(claim, per_query_limit=0)


def test_dedupe_records_removes_duplicate_source_identifier_pairs():
    pipeline = EvidenceRetrievalPipeline(
        openalex_client=FakeOpenAlexClient(),
        semantic_scholar_client=FakeSemanticScholarClient(),
    )

    claim = ClaimForRetrieval(
        claim_id="claim_001",
        claim_text="multi-agent systems require coordination",
        claim_type="empirical_technical",
        verification_strategy="literature_review",
    )

    result = pipeline.retrieve_for_claim(claim, source="openalex", per_query_limit=1)

    duplicated = result.evidence_records + result.evidence_records
    deduped = _dedupe_records(duplicated)

    assert len(deduped) == len(result.evidence_records)