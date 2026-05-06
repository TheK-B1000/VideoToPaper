from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from src.core.evidence_retrieval import EvidenceRecord, RetrievalCache


SEMANTIC_SCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


@dataclass(frozen=True)
class SemanticScholarPaper:
    title: str
    paper_id: str
    year: int | None
    abstract: str | None
    url: str | None
    doi: str | None
    citation_count: int | None


def _extract_doi(external_ids: dict[str, Any] | None) -> str | None:
    if not external_ids:
        return None

    doi = external_ids.get("DOI")

    if not doi:
        return None

    return str(doi).strip()


def parse_semantic_scholar_paper(raw_paper: dict[str, Any]) -> SemanticScholarPaper:
    title = raw_paper.get("title")
    paper_id = raw_paper.get("paperId")

    if not title:
        raise ValueError("Semantic Scholar paper is missing a title.")

    if not paper_id:
        raise ValueError("Semantic Scholar paper is missing a paperId.")

    return SemanticScholarPaper(
        title=title,
        paper_id=paper_id,
        year=raw_paper.get("year"),
        abstract=raw_paper.get("abstract"),
        url=raw_paper.get("url"),
        doi=_extract_doi(raw_paper.get("externalIds")),
        citation_count=raw_paper.get("citationCount"),
    )


def semantic_scholar_paper_to_evidence_record(
    *,
    claim_id: str,
    paper: SemanticScholarPaper,
    stance: str,
    tier: int = 1,
) -> EvidenceRecord:
    identifier = paper.doi or f"semantic_scholar:{paper.paper_id}"

    return EvidenceRecord(
        claim_id=claim_id,
        title=paper.title,
        source="Semantic Scholar",
        tier=tier,  # type: ignore[arg-type]
        stance=stance,  # type: ignore[arg-type]
        identifier=identifier,
        url=paper.url,
        doi=paper.doi,
        abstract=paper.abstract,
        year=paper.year,
    )


class SemanticScholarClient:
    def __init__(
        self,
        cache: RetrievalCache | None = None,
        base_url: str = SEMANTIC_SCHOLAR_BASE_URL,
        timeout_seconds: int = 15,
    ) -> None:
        self.cache = cache or RetrievalCache()
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def search_papers(
        self,
        query: str,
        *,
        limit: int = 5,
        use_cache: bool = True,
    ) -> list[SemanticScholarPaper]:
        clean_query = " ".join(query.split())

        if not clean_query:
            raise ValueError("Semantic Scholar query cannot be empty.")

        if limit <= 0:
            raise ValueError("limit must be positive.")

        cache_key = f"semantic_scholar::{clean_query}::limit={limit}"

        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return [parse_semantic_scholar_paper(item) for item in cached["data"]]

        params = urllib.parse.urlencode(
            {
                "query": clean_query,
                "limit": limit,
                "fields": "title,paperId,year,abstract,url,externalIds,citationCount",
            }
        )

        url = f"{self.base_url}?{params}"

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "InquiryEngine/0.1 academic-retrieval"
            },
        )

        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))

        results = payload.get("data", [])

        if use_cache:
            self.cache.set(cache_key, {"data": results})

        return [parse_semantic_scholar_paper(item) for item in results]