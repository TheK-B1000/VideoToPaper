import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
import urllib.error

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

    results, status = client.search_papers("multi-agent reinforcement learning", limit=5)

    assert status == "ok"
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


def test_semantic_scholar_client_sends_x_api_key_when_provided(tmp_path):
    captured: dict[str, str] = {}

    body = json.dumps(
        {
            "data": [
                {
                    "paperId": "pidKey",
                    "title": "Keyed Request Paper",
                    "year": 2024,
                    "abstract": None,
                    "url": "https://www.semanticscholar.org/paper/pidKey",
                    "externalIds": {},
                    "citationCount": None,
                }
            ]
        }
    ).encode()

    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    def fake_urlopen(request, timeout=None):
        captured.update({k: v for k, v in request.header_items()})
        return mock_resp

    cache = RetrievalCache(cache_dir=tmp_path)
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        client = SemanticScholarClient(
            cache=cache,
            min_request_interval_seconds=0,
            api_key="secret-ss-key",
        )
        papers, status = client.search_papers("unique query for api key header zz01", limit=1)

    assert status == "ok"
    assert len(papers) == 1
    assert captured.get("X-api-key") == "secret-ss-key"


def test_semantic_scholar_search_retries_after_429_then_returns_papers(tmp_path):
    body_ok = json.dumps(
        {
            "data": [
                {
                    "paperId": "pid429",
                    "title": "Paper After Cooldown",
                    "year": 2024,
                    "abstract": None,
                    "url": None,
                    "externalIds": {},
                    "citationCount": None,
                }
            ]
        }
    ).encode()

    mock_resp = MagicMock()
    mock_resp.read.return_value = body_ok
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    rate_err = urllib.error.HTTPError(
        "https://api.semanticscholar.org/graph/v1/paper/search?q=x",
        429,
        "Too Many Requests",
        {},
        BytesIO(),
    )

    attempt = {"n": 0}

    def side_effect(*args, **kwargs):
        attempt["n"] += 1
        if attempt["n"] == 1:
            raise rate_err
        return mock_resp

    cache = RetrievalCache(cache_dir=tmp_path)
    with patch("urllib.request.urlopen", side_effect=side_effect):
        with patch("time.sleep"):
            client = SemanticScholarClient(
                cache=cache,
                max_retries=4,
                retry_initial_sleep_seconds=0.001,
            )
            papers, status = client.search_papers(
                "semantic scholar retry query zz99", limit=1
            )

    assert status == "ok"
    assert len(papers) == 1
    assert papers[0].paper_id == "pid429"
    assert papers[0].title == "Paper After Cooldown"


def test_semantic_scholar_search_returns_empty_when_rate_limited_throughout(tmp_path):
    rate_err = urllib.error.HTTPError(
        "https://api.semanticscholar.org/graph/v1/paper/search?q=x",
        429,
        "Too Many Requests",
        {},
        BytesIO(),
    )

    cache = RetrievalCache(cache_dir=tmp_path)
    with patch("urllib.request.urlopen", side_effect=rate_err):
        with patch("time.sleep"):
            client = SemanticScholarClient(
                cache=cache,
                max_retries=2,
                retry_initial_sleep_seconds=0.001,
            )
            papers, status = client.search_papers("persistent rate limit yy77", limit=1)

    assert papers == []
    assert status == "rate_limited"


@pytest.mark.parametrize("status_code", [502, 503, 504])
def test_semantic_scholar_retries_transient_http_then_ok(status_code, tmp_path):
    body_ok = json.dumps(
        {
            "data": [
                {
                    "paperId": "pid503",
                    "title": "Transient recovery",
                    "year": 2022,
                    "abstract": None,
                    "url": None,
                    "externalIds": {},
                    "citationCount": None,
                }
            ]
        }
    ).encode()

    mock_resp = MagicMock()
    mock_resp.read.return_value = body_ok
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    transient_err = urllib.error.HTTPError(
        "https://api.semanticscholar.org/graph/v1/paper/search?q=x",
        status_code,
        "Transient",
        {},
        BytesIO(),
    )

    calls = {"n": 0}

    def side_effect(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise transient_err
        return mock_resp

    cache = RetrievalCache(cache_dir=tmp_path)
    with patch("urllib.request.urlopen", side_effect=side_effect):
        with patch("time.sleep"):
            client = SemanticScholarClient(
                cache=cache,
                max_retries=4,
                retry_initial_sleep_seconds=0.001,
            )
            papers, status = client.search_papers(
                f"transient http query {status_code} aa11", limit=1
            )

    assert status == "ok"
    assert papers[0].paper_id == "pid503"


def test_semantic_scholar_retry_after_numeric_seconds_used_for_sleep(tmp_path):
    body_ok = json.dumps(
        {
            "data": [
                {
                    "paperId": "slow429",
                    "title": "Honored delay",
                    "year": 2021,
                    "abstract": None,
                    "url": None,
                    "externalIds": {},
                    "citationCount": None,
                }
            ]
        }
    ).encode()

    mock_resp = MagicMock()
    mock_resp.read.return_value = body_ok
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    rate_err = urllib.error.HTTPError(
        "https://api.semanticscholar.org/graph/v1/paper/search?q=x",
        429,
        "Too Many Requests",
        {"Retry-After": "88"},
        BytesIO(),
    )

    sleeps: list[float] = []

    def capture_sleep(seconds):
        sleeps.append(float(seconds))

    attempt = {"n": 0}

    def side_effect(*args, **kwargs):
        attempt["n"] += 1
        if attempt["n"] == 1:
            raise rate_err
        return mock_resp

    cache = RetrievalCache(cache_dir=tmp_path)
    with patch("urllib.request.urlopen", side_effect=side_effect):
        with patch("time.sleep", side_effect=capture_sleep):
            client = SemanticScholarClient(
                cache=cache,
                max_retries=4,
                retry_initial_sleep_seconds=0.001,
            )
            papers, status = client.search_papers(
                "retry after numeric sleep bb22", limit=1
            )

    assert status == "ok"
    assert sleeps and sleeps[0] == pytest.approx(88.0)
    assert papers[0].paper_id == "slow429"


def test_semantic_scholar_retry_after_non_numeric_date_string_falls_back_to_backoff(
    tmp_path,
):
    body_ok = json.dumps(
        {
            "data": [
                {
                    "paperId": "hdr429",
                    "title": "Fallback delay",
                    "year": 2020,
                    "abstract": None,
                    "url": None,
                    "externalIds": {},
                    "citationCount": None,
                }
            ]
        }
    ).encode()

    mock_resp = MagicMock()
    mock_resp.read.return_value = body_ok
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    rate_err = urllib.error.HTTPError(
        "https://api.semanticscholar.org/graph/v1/paper/search?q=x",
        429,
        "Too Many Requests",
        {"Retry-After": "Wed, not-a-real-http-date"},
        BytesIO(),
    )

    sleeps: list[float] = []

    def capture_sleep(seconds):
        sleeps.append(float(seconds))

    attempt = {"n": 0}

    def side_effect(*args, **kwargs):
        attempt["n"] += 1
        if attempt["n"] == 1:
            raise rate_err
        return mock_resp

    fallback = 0.037
    cache = RetrievalCache(cache_dir=tmp_path)
    with patch("urllib.request.urlopen", side_effect=side_effect):
        with patch("time.sleep", side_effect=capture_sleep):
            client = SemanticScholarClient(
                cache=cache,
                max_retries=4,
                retry_initial_sleep_seconds=fallback,
            )
            papers, status = client.search_papers(
                "retry after junk header cc33", limit=1
            )

    assert status == "ok"
    assert sleeps and sleeps[0] == pytest.approx(fallback)
    assert papers[0].paper_id == "hdr429"


def test_semantic_scholar_urlerror_then_success(tmp_path):
    body_ok = json.dumps(
        {
            "data": [
                {
                    "paperId": "urlerr",
                    "title": "After URL error",
                    "year": 2019,
                    "abstract": None,
                    "url": None,
                    "externalIds": {},
                    "citationCount": None,
                }
            ]
        }
    ).encode()

    mock_resp = MagicMock()
    mock_resp.read.return_value = body_ok
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    calls = {"n": 0}

    def side_effect(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.URLError(reason="timeout stub")
        return mock_resp

    cache = RetrievalCache(cache_dir=tmp_path)
    with patch("urllib.request.urlopen", side_effect=side_effect):
        with patch("time.sleep"):
            client = SemanticScholarClient(
                cache=cache,
                max_retries=4,
                retry_initial_sleep_seconds=0.001,
            )
            papers, status = client.search_papers("url error recovery dd44", limit=1)

    assert status == "ok"
    assert papers[0].paper_id == "urlerr"


def test_semantic_scholar_malformed_json_then_success(tmp_path):
    body_ok = json.dumps(
        {
            "data": [
                {
                    "paperId": "jsonfix",
                    "title": "After bad JSON",
                    "year": 2018,
                    "abstract": None,
                    "url": None,
                    "externalIds": {},
                    "citationCount": None,
                }
            ]
        }
    ).encode()

    bad_resp = MagicMock()
    bad_resp.read.return_value = b"NOT_JSON{{{ "
    bad_resp.__enter__.return_value = bad_resp
    bad_resp.__exit__.return_value = None

    good_resp = MagicMock()
    good_resp.read.return_value = body_ok
    good_resp.__enter__.return_value = good_resp
    good_resp.__exit__.return_value = None

    calls = {"n": 0}

    def side_effect(*args, **kwargs):
        calls["n"] += 1
        return bad_resp if calls["n"] == 1 else good_resp

    cache = RetrievalCache(cache_dir=tmp_path)
    with patch("urllib.request.urlopen", side_effect=side_effect):
        with patch("time.sleep"):
            client = SemanticScholarClient(
                cache=cache,
                max_retries=4,
                retry_initial_sleep_seconds=0.001,
            )
            papers, status = client.search_papers("json decode retry ee55", limit=1)

    assert status == "ok"
    assert papers[0].paper_id == "jsonfix"


def test_semantic_scholar_rate_limit_exhaustion_does_not_write_cache(tmp_path):
    rate_err = urllib.error.HTTPError(
        "https://api.semanticscholar.org/graph/v1/paper/search?q=x",
        429,
        "Too Many Requests",
        {},
        BytesIO(),
    )

    cache = RetrievalCache(cache_dir=tmp_path)
    with patch("urllib.request.urlopen", side_effect=rate_err):
        with patch("time.sleep"):
            client = SemanticScholarClient(
                cache=cache,
                max_retries=1,
                retry_initial_sleep_seconds=0.001,
            )
            client.search_papers("cache bypass degraded ff66", limit=2)

    assert list(tmp_path.glob("*.json")) == []


def test_semantic_scholar_client_rate_limit_waits_between_requests():
    client = SemanticScholarClient(
        cache=RetrievalCache(),
        min_request_interval_seconds=1.0,
    )

    with patch(
        "src.core.semantic_scholar_client.time.monotonic",
        side_effect=[20.0, 20.4, 21.0],
    ):
        with patch("src.core.semantic_scholar_client.time.sleep") as sleep_mock:
            client._respect_rate_limit()
            client._respect_rate_limit()

    sleep_mock.assert_called_once()
    assert sleep_mock.call_args.args[0] == pytest.approx(0.6)


def test_semantic_scholar_client_rate_limit_can_be_disabled():
    client = SemanticScholarClient(
        cache=RetrievalCache(),
        min_request_interval_seconds=0,
    )

    with patch("src.core.semantic_scholar_client.time.sleep") as sleep_mock:
        client._respect_rate_limit()
        client._respect_rate_limit()

    sleep_mock.assert_not_called()
