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


OPENALEX_BASE_URL = "https://api.openalex.org/works"

_RETRYABLE_HTTP_CODES = frozenset({429, 502, 503, 504})


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
    title_raw = raw_work.get("title") or raw_work.get("display_name")
    title = title_raw.strip() if isinstance(title_raw, str) else None
    openalex_id = raw_work.get("id")

    if not openalex_id:
        raise ValueError("OpenAlex work is missing an id.")

    if not title:
        title = "(Untitled)"

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
        min_request_interval_seconds: float = 0.25,
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

    def _fetch_works_payload(self, url: str) -> JsonFetchOutcome:
        sleep_s = self.retry_initial_sleep_seconds

        for attempt in range(self.max_retries + 1):
            try:
                self._respect_rate_limit()
                with urllib.request.urlopen(
                    url,
                    timeout=self.timeout_seconds,
                ) as response:
                    raw = response.read().decode("utf-8")
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError:
                        if attempt >= self.max_retries:
                            return JsonFetchOutcome(
                                {"results": []},
                                cacheable=False,
                                exhausted_reason="json_error",
                            )
                        time.sleep(sleep_s)
                        sleep_s = min(sleep_s * 2.0, 60.0)
                        continue
                    if not isinstance(parsed, dict):
                        if attempt >= self.max_retries:
                            return JsonFetchOutcome(
                                {"results": []},
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
                    return JsonFetchOutcome({"results": []}, False, exhausted)
                raise
            except urllib.error.URLError:
                if attempt >= self.max_retries:
                    return JsonFetchOutcome(
                        {"results": []},
                        cacheable=False,
                        exhausted_reason="url_error",
                    )
                time.sleep(sleep_s)
                sleep_s = min(sleep_s * 2.0, 60.0)

        return JsonFetchOutcome({"results": []}, False, "url_error")

    def search_works(
        self,
        query: str,
        *,
        per_page: int = 5,
        use_cache: bool = True,
    ) -> tuple[list[OpenAlexWork], Literal["ok", "rate_limited", "error"]]:
        clean_query = " ".join(query.split())

        if not clean_query:
            raise ValueError("OpenAlex query cannot be empty.")

        if per_page <= 0:
            raise ValueError("per_page must be positive.")

        cache_key = f"openalex::{clean_query}::per_page={per_page}"

        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return [
                    parse_openalex_work(item) for item in cached["results"]
                ], "ok"

        params = urllib.parse.urlencode(
            {
                "search": clean_query,
                "per-page": per_page,
            }
        )

        url = f"{self.base_url}?{params}"

        outcome = self._fetch_works_payload(url)

        results = outcome.payload.get("results", [])
        if not isinstance(results, list):
            results = []

        if use_cache and outcome.cacheable:
            self.cache.set(cache_key, {"results": results})

        works = [parse_openalex_work(item) for item in results]
        status = retrieval_provider_status_from_outcome(outcome)
        return works, status