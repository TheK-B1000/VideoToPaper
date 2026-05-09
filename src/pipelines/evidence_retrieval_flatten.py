"""Helpers for turning Week 5 retrieval payloads into flat evidence record lists."""

from __future__ import annotations

from typing import Any


def flatten_evidence_records(retrieval_document: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Collect ``evidence_records`` from each entry in ``retrieval_results``.

    Week 7 integration expects a list or ``{\"evidence_records\": [...]}`` shape;
    the retrieval CLI writes nested results instead.
    """
    flat: list[dict[str, Any]] = []
    results = retrieval_document.get("retrieval_results")

    if not isinstance(results, list):
        return flat

    for item in results:
        if not isinstance(item, dict):
            continue
        records = item.get("evidence_records")
        if isinstance(records, list):
            flat.extend(r for r in records if isinstance(r, dict))

    return flat
