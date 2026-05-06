from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Literal

from src.core.evidence_retrieval import EvidenceRecord, RetrievalCache
from src.core.retrieval_http_retry import (
    ExhaustedReason,
    JsonFetchOutcome,
    retrieval_provider_status_from_outcome,
    retry_after_sleep_seconds,
)


SEMANTIC_SCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

# Semantic Scholar rate-limits aggressively on the public tier; treat these as retryable.
_RETRYABLE_HTTP_CODES = frozenset({429, 502, 503, 504})


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
        min_request_interval_seconds: float = 1.0,
        *,
        max_retries: int = 4,
        retry_initial_sleep_seconds: float = 2.0,
    ) -> None:
        self.cache = cache or RetrievalCache()
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.min_request_interval_seconds = min_request_interval_seconds
        self._last_request_time: float | None = None
        self.max_retries = max_retries
        self.retry_initial_sleep_seconds = retry_initial_sleep_seconds

    def _respect_rate_limit(self) -> None:
        if self.min_request_interval_seconds <= 0:
            return

        now = time.monotonic()

        if self._last_request_time is None:
            self._last_request_time = now
            return

        elapsed = now - self._last_request_time
        wait_seconds = self.min_request_interval_seconds - elapsed

        if wait_seconds > 0:
            time.sleep(wait_seconds)

        self._last_request_time = time.monotonic()

    def _fetch_search_payload(self, url: str) -> JsonFetchOutcome:
        """
        GET JSON from Semantic Scholar with retries on rate limits / transient errors.

        Empty payloads after exhaustion are **not cacheable** so disk cache cannot
        pin a rate-limit artifact forever.
        """
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "InquiryEngine/0.1 academic-retrieval",
            },
        )
        sleep_s = self.retry_initial_sleep_seconds

        for attempt in range(self.max_retries + 1):
            try:
                self._respect_rate_limit()
                with urllib.request.urlopen(
                    request,
                    timeout=self.timeout_seconds,
                ) as response:
                    raw = response.read().decode("utf-8")
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError:
                        if attempt >= self.max_retries:
                            return JsonFetchOutcome(
                                {"data": []},
                                cacheable=False,
                                exhausted_reason="json_error",
                            )
                        time.sleep(sleep_s)
                        sleep_s = min(sleep_s * 2.0, 60.0)
                        continue
                    if not isinstance(parsed, dict):
                        if attempt >= self.max_retries:
                            return JsonFetchOutcome(
                                {"data": []},
                                cacheable=False,
                                exhausted_reason="json_error",
                            )
                        time.sleep(sleep_s)
                        sleep_s = min(sleep_s * 2.0, 60.0)
                        continue
                    return JsonFetchOutcome(parsed, cacheable=True)
            except urllib.error.HTTPError as exc:
                if (
                    exc.code in _RETRYABLE_HTTP_CODES
                    and attempt < self.max_retries
                ):
                    wait = retry_after_sleep_seconds(
                        exc.headers.get("Retry-After"),
                        fallback_seconds=sleep_s,
                        cap_seconds=120.0,
                    )
                    time.sleep(wait)
                    sleep_s = min(sleep_s * 2.0, 60.0)
                    continue
                if exc.code in _RETRYABLE_HTTP_CODES:
                    exhausted: ExhaustedReason
                    exhausted = "429" if exc.code == 429 else "transient_http"
                    return JsonFetchOutcome({"data": []}, False, exhausted)
                raise
            except urllib.error.URLError:
                if attempt >= self.max_retries:
                    return JsonFetchOutcome(
                        {"data": []},
                        cacheable=False,
                        exhausted_reason="url_error",
                    )
                time.sleep(sleep_s)
                sleep_s = min(sleep_s * 2.0, 60.0)

        return JsonFetchOutcome({"data": []}, False, "url_error")

    def search_papers(
        self,
        query: str,
        *,
        limit: int = 5,
        use_cache: bool = True,
    ) -> tuple[list[SemanticScholarPaper], Literal["ok", "rate_limited", "error"]]:
        clean_query = " ".join(query.split())

        if not clean_query:
            raise ValueError("Semantic Scholar query cannot be empty.")

        if limit <= 0:
            raise ValueError("limit must be positive.")

        cache_key = f"semantic_scholar::{clean_query}::limit={limit}"

        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return [
                    parse_semantic_scholar_paper(item) for item in cached["data"]
                ], "ok"

        params = urllib.parse.urlencode(
            {
                "query": clean_query,
                "limit": limit,
                "fields": "title,paperId,year,abstract,url,externalIds,citationCount",
            }
        )

        url = f"{self.base_url}?{params}"

        outcome = self._fetch_search_payload(url)

        results = outcome.payload.get("data", [])
        if not isinstance(results, list):
            results = []

        if use_cache and outcome.cacheable:
            self.cache.set(cache_key, {"data": results})

        papers = [parse_semantic_scholar_paper(item) for item in results]
        status = retrieval_provider_status_from_outcome(outcome)
        return papers, status