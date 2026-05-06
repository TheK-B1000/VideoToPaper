"""
Shared HTTP retry helpers for academic retrieval clients (Semantic Scholar, OpenAlex).

``Retry-After`` may be delay-seconds (preferred) or an HTTP-date; non-numeric values
fall back to exponential backoff rather than raising.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Literal


def retry_after_sleep_seconds(
    retry_after_header: str | None,
    *,
    fallback_seconds: float,
    cap_seconds: float = 120.0,
) -> float:
    """
    Compute sleep duration from ``Retry-After``.

    - Numeric seconds: ``min(float(value), cap_seconds)``.
    - HTTP-date (RFC 7231): seconds until that instant, capped (must be in the future).
    - Missing, invalid, or non-positive delay: ``fallback_seconds``.
    """
    if retry_after_header is None:
        return fallback_seconds

    raw = retry_after_header.strip()
    if not raw:
        return fallback_seconds

    try:
        sec = float(raw)
        if sec >= 0:
            return min(sec, cap_seconds)
        return fallback_seconds
    except ValueError:
        pass

    try:
        when = parsedate_to_datetime(raw)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        delta = (when - datetime.now(timezone.utc)).total_seconds()
        if delta > 0:
            return min(delta, cap_seconds)
    except (TypeError, ValueError, OSError):
        pass

    return fallback_seconds


ExhaustedReason = Literal["429", "transient_http", "url_error", "json_error"]


@dataclass(frozen=True)
class JsonFetchOutcome:
    """Result of a JSON GET with retry semantics."""

    payload: dict[str, Any]
    cacheable: bool
    exhausted_reason: ExhaustedReason | None = None


def retrieval_provider_status_from_outcome(outcome: JsonFetchOutcome) -> Literal[
    "ok",
    "rate_limited",
    "error",
]:
    """Map low-level fetch outcome to pipeline JSON statuses."""
    if outcome.cacheable:
        return "ok"
    if outcome.exhausted_reason == "429":
        return "rate_limited"
    return "error"
