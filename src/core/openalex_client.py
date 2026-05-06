from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from src.core.evidence_retrieval import EvidenceRecord, RetrievalCache


OPENALEX_BASE_URL = "https://api.openalex.org/works"


@dataclass(frozen=True)
class OpenAlexWork:
    title: str
    openalex_id: str
    publication_year: int | None
    doi: str | None
    url: str | None
    abstract: str | None


def _reconstruct_abstract(abstract_inverted_index: dict[str, list[int]] | None) -> str | None:
    """
    OpenAlex returns abstracts as an inverted index:
    {
        "multi-agent": [0],
        "reinforcement": [1],
        "learning": [2]
    }

    This converts that structure back into readable text.
    """
    if not abstract_inverted_index:
        return None

    positioned_words: list[tuple[int, str]] = []

    for word, positions in abstract_inverted_index.items():
        for position in positions:
            positioned_words.append((position, word))

    positioned_words.sort(key=lambda item: item[0])

    return " ".join(word for _, word in positioned_words)


def _normalize_doi(raw_doi: str | None) -> str | None:
    if not raw_doi:
        return None

    return raw_doi.replace("https://doi.org/", "").strip()


def parse_openalex_work(raw_work: dict[str, Any]) -> OpenAlexWork:
    title = raw_work.get("title") or raw_work.get("display_name")
    openalex_id = raw_work.get("id")

    if not title:
        raise ValueError("OpenAlex work is missing a title.")

    if not openalex_id:
        raise ValueError("OpenAlex work is missing an id.")

    doi = _normalize_doi(raw_work.get("doi"))

    return OpenAlexWork(
        title=title,
        openalex_id=openalex_id,
        publication_year=raw_work.get("publication_year"),
        doi=doi,
        url=raw_work.get("primary_location", {}).get("landing_page_url")
        or raw_work.get("open_access", {}).get("oa_url")
        or raw_work.get("id"),
        abstract=_reconstruct_abstract(raw_work.get("abstract_inverted_index")),
    )


def openalex_work_to_evidence_record(
    *,
    claim_id: str,
    work: OpenAlexWork,
    stance: str,
    tier: int = 1,
) -> EvidenceRecord:
    identifier = work.doi or work.openalex_id

    return EvidenceRecord(
        claim_id=claim_id,
        title=work.title,
        source="OpenAlex",
        tier=tier,  # type: ignore[arg-type]
        stance=stance,  # type: ignore[arg-type]
        identifier=identifier,
        url=work.url,
        doi=work.doi,
        abstract=work.abstract,
        year=work.publication_year,
    )


class OpenAlexClient:
    def __init__(
        self,
        cache: RetrievalCache | None = None,
        base_url: str = OPENALEX_BASE_URL,
        timeout_seconds: int = 15,
    ) -> None:
        self.cache = cache or RetrievalCache()
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def search_works(
        self,
        query: str,
        *,
        per_page: int = 5,
        use_cache: bool = True,
    ) -> list[OpenAlexWork]:
        clean_query = " ".join(query.split())

        if not clean_query:
            raise ValueError("OpenAlex query cannot be empty.")

        if per_page <= 0:
            raise ValueError("per_page must be positive.")

        cache_key = f"openalex::{clean_query}::per_page={per_page}"

        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return [parse_openalex_work(item) for item in cached["results"]]

        params = urllib.parse.urlencode(
            {
                "search": clean_query,
                "per-page": per_page,
            }
        )

        url = f"{self.base_url}?{params}"

        with urllib.request.urlopen(url, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))

        results = payload.get("results", [])

        if use_cache:
            self.cache.set(cache_key, {"results": results})

        return [parse_openalex_work(item) for item in results]