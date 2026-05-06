from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.core.evidence_retrieval import (
    EvidenceRecord,
    EvidenceRetrievalResult,
    RetrievalCache,
    generate_balanced_queries,
    score_evidence_balance,
)
from src.core.openalex_client import OpenAlexClient, openalex_work_to_evidence_record
from src.core.semantic_scholar_client import (
    SemanticScholarClient,
    semantic_scholar_paper_to_evidence_record,
)


RetrievalSource = Literal["openalex", "semantic_scholar", "all"]


@dataclass(frozen=True)
class ClaimForRetrieval:
    claim_id: str
    claim_text: str
    claim_type: str
    verification_strategy: str

    def validate(self) -> None:
        if not self.claim_id.strip():
            raise ValueError("claim_id cannot be empty.")

        if not self.claim_text.strip():
            raise ValueError("claim_text cannot be empty.")

        if not self.claim_type.strip():
            raise ValueError("claim_type cannot be empty.")

        if not self.verification_strategy.strip():
            raise ValueError("verification_strategy cannot be empty.")


def _infer_stance_from_query(query: str) -> Literal["supports", "contradicts", "qualifies"]:
    lowered = query.lower()

    if "against" in lowered or "contradict" in lowered or "critique" in lowered:
        return "contradicts"

    if "limitations" in lowered or "qualification" in lowered or "qualifies" in lowered:
        return "qualifies"

    return "supports"


def _dedupe_records(records: list[EvidenceRecord]) -> list[EvidenceRecord]:
    seen: set[str] = set()
    unique_records: list[EvidenceRecord] = []

    for record in records:
        dedupe_key = f"{record.source.lower()}::{record.identifier.lower()}"

        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        unique_records.append(record)

    return unique_records


class EvidenceRetrievalPipeline:
    def __init__(
        self,
        *,
        cache: RetrievalCache | None = None,
        openalex_client: OpenAlexClient | None = None,
        semantic_scholar_client: SemanticScholarClient | None = None,
    ) -> None:
        shared_cache = cache or RetrievalCache()

        self.openalex_client = openalex_client or OpenAlexClient(cache=shared_cache)
        self.semantic_scholar_client = semantic_scholar_client or SemanticScholarClient(
            cache=shared_cache
        )

    def retrieve_for_claim(
        self,
        claim: ClaimForRetrieval,
        *,
        source: RetrievalSource = "all",
        per_query_limit: int = 3,
    ) -> EvidenceRetrievalResult:
        claim.validate()

        if claim.verification_strategy != "literature_review":
            return EvidenceRetrievalResult(
                claim_id=claim.claim_id,
                queries_executed=[],
                evidence_records=[],
                balance_score="insufficient",
            )

        if per_query_limit <= 0:
            raise ValueError("per_query_limit must be positive.")

        queries = generate_balanced_queries(claim.claim_text)
        records: list[EvidenceRecord] = []

        for query in queries:
            stance = _infer_stance_from_query(query)

            if source in ("openalex", "all"):
                works = self.openalex_client.search_works(query, per_page=per_query_limit)

                for work in works:
                    records.append(
                        openalex_work_to_evidence_record(
                            claim_id=claim.claim_id,
                            work=work,
                            stance=stance,
                            tier=1,
                        )
                    )

            if source in ("semantic_scholar", "all"):
                papers = self.semantic_scholar_client.search_papers(
                    query,
                    limit=per_query_limit,
                )

                for paper in papers:
                    records.append(
                        semantic_scholar_paper_to_evidence_record(
                            claim_id=claim.claim_id,
                            paper=paper,
                            stance=stance,
                            tier=1,
                        )
                    )

        unique_records = _dedupe_records(records)

        for record in unique_records:
            record.validate()

        return EvidenceRetrievalResult(
            claim_id=claim.claim_id,
            queries_executed=queries,
            evidence_records=unique_records,
            balance_score=score_evidence_balance(unique_records),
        )