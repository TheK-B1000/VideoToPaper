"""Unit tests for Retry-After parsing used by retrieval HTTP clients."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.core.retrieval_http_retry import (
    JsonFetchOutcome,
    retrieval_provider_status_from_outcome,
    retry_after_sleep_seconds,
)


def test_retry_after_numeric_seconds_honored_and_capped():
    assert retry_after_sleep_seconds(
        "45",
        fallback_seconds=99.0,
        cap_seconds=120.0,
    ) == pytest.approx(45.0)

    assert retry_after_sleep_seconds(
        "999",
        fallback_seconds=1.0,
        cap_seconds=120.0,
    ) == pytest.approx(120.0)


def test_retry_after_negative_numeric_falls_back():
    assert retry_after_sleep_seconds(
        "-5",
        fallback_seconds=2.5,
    ) == pytest.approx(2.5)


def test_retry_after_http_date_future_uses_delta_capped():
    future = datetime.now(timezone.utc) + timedelta(hours=6)
    header = future.strftime("%a, %d %b %Y %H:%M:%S GMT")

    wait = retry_after_sleep_seconds(
        header,
        fallback_seconds=9.0,
        cap_seconds=120.0,
    )

    assert wait == pytest.approx(120.0)


def test_retry_after_http_date_past_falls_back():
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    header = past.strftime("%a, %d %b %Y %H:%M:%S GMT")

    assert retry_after_sleep_seconds(
        header,
        fallback_seconds=3.14,
    ) == pytest.approx(3.14)


def test_retry_after_junk_falls_back_to_exponential_placeholder():
    assert retry_after_sleep_seconds(
        "not-a-number-or-date",
        fallback_seconds=7.0,
    ) == pytest.approx(7.0)


def test_retrieval_provider_status_mapping():
    assert (
        retrieval_provider_status_from_outcome(
            JsonFetchOutcome({"data": []}, True, None),
        )
        == "ok"
    )
    assert (
        retrieval_provider_status_from_outcome(
            JsonFetchOutcome({"data": []}, False, "429"),
        )
        == "rate_limited"
    )
    assert (
        retrieval_provider_status_from_outcome(
            JsonFetchOutcome({"data": []}, False, "url_error"),
        )
        == "error"
    )
