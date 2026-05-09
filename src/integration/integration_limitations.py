"""
Deterministic ``limitations`` strings for Week 7 evidence-integration documents.

Papers read ``limitations`` via :mod:`src.paper.paper_spec_builder`; previously nothing
wrote the field, so HTML showed only the assembler placeholder.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        text = raw.strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _evidence_looks_like_dry_run(records: Sequence[Mapping[str, Any]]) -> bool:
    for row in records:
        src = str(row.get("source", "")).strip().casefold()
        if src == "dryrun":
            return True
        title = str(row.get("title", "")).strip().casefold()
        if title.startswith("dry-run"):
            return True
    return False


def build_integration_limitations(
    *,
    existing: Any = None,
    evidence_records: Sequence[Mapping[str, Any]] | None = None,
    skipped_claims: Sequence[Mapping[str, Any]] | None = None,
    cherry_picking_guard: Mapping[str, Any] | None = None,
) -> list[str]:
    """
    Merge caller-supplied limitations with standard inquiry caveats.

    Safe to call twice (e.g. Week 7 pipeline and finalize merge): duplicates are removed.
    """
    base: list[str] = []
    if isinstance(existing, list):
        base.extend(str(x).strip() for x in existing if isinstance(x, str) and x.strip())

    suggestions: list[str] = [
        (
            "Retrieval matches bibliographic metadata for each query; passages were not "
            "verified sentence-by-sentence against full-text sources."
        ),
        (
            "Speaker quotations and clip boundaries depend on transcript alignment and "
            "caption quality; timestamps are approximate."
        ),
        (
            "Interpretive, normative, or anecdotal claims may appear in the paper without "
            "literature adjudication when not routed to literature review."
        ),
    ]

    records = list(evidence_records or [])
    if records and _evidence_looks_like_dry_run(records):
        suggestions.append(
            "Evidence rows include dry-run placeholders until live retrieval is configured "
            "with real sources."
        )

    if skipped_claims is not None and len(skipped_claims) > 0:
        suggestions.append(
            "Some claims in the inventory were skipped for adjudication because they were "
            "not routed to literature review."
        )

    if isinstance(cherry_picking_guard, dict):
        if cherry_picking_guard.get("publishable_for_week8") is False:
            suggestions.append(
                "Cherry-picking guard flagged this run as not yet publishable for Week 8; "
                "review retrieval balance before external citation."
            )

    return _dedupe_preserve_order(base + suggestions)


def apply_integration_limitations(
    payload: dict[str, Any],
    *,
    evidence_records_override: Sequence[Mapping[str, Any]] | None = None,
) -> None:
    """
    Mutate ``payload`` to set merged ``limitations``.

    Week 7 integration JSON often omits ``evidence_records`` until finalize; pass
    ``evidence_records_override`` when building limitations before that merge.
    """
    records_source: Sequence[Mapping[str, Any]] | None = evidence_records_override
    if records_source is None:
        raw = payload.get("evidence_records")
        records_source = raw if isinstance(raw, list) else None

    payload["limitations"] = build_integration_limitations(
        existing=payload.get("limitations"),
        evidence_records=records_source,
        skipped_claims=payload.get("skipped_claims"),
        cherry_picking_guard=payload.get("cherry_picking_guard"),
    )
