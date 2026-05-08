"""
Conservative fallbacks when heuristic Week 2 extraction yields no supporting points.

Week 3 needs grounded rows in ``argument_map["supporting_points"]``; this module
adds minimal candidates from chunk text when the list would otherwise be empty.
"""

from __future__ import annotations

from typing import Any


def ensure_argument_map_has_supporting_points(
    argument_map: dict[str, Any],
    chunks: list[dict[str, Any]],
    *,
    max_points: int = 5,
) -> dict[str, Any]:
    """
    If ``supporting_points`` is empty but ``chunks`` carry text, add a few safe rows.

    Each row matches the shape produced by :func:`src.argument.argument_map_builder._build_argument_item`
    (so Week 3 :func:`candidate_claims_from_argument_map` can consume it), with
    ``fallback_generated: True`` for downstream auditing.

    Returns ``argument_map`` mutated in place (same object).
    """
    if not isinstance(argument_map, dict):
        raise TypeError("argument_map must be a dictionary")

    if not isinstance(chunks, list):
        raise TypeError("chunks must be a list")

    existing = argument_map.get("supporting_points")
    if isinstance(existing, list) and len(existing) > 0:
        argument_map.setdefault("fallback_supporting_points_used", False)
        return argument_map

    fallback_points: list[dict[str, Any]] = []

    for index, chunk in enumerate(chunks[:max_points]):
        if not isinstance(chunk, dict):
            continue

        chunk_id = chunk.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            continue

        source = chunk.get("source_text")
        if not isinstance(source, str) or not source:
            continue

        try:
            chunk_g_start = int(chunk["char_start"])
            chunk_g_end = int(chunk["char_end"])
            t0 = float(chunk["start_seconds"])
            t1 = float(chunk["end_seconds"])
        except (KeyError, TypeError, ValueError):
            continue

        span = chunk_g_end - chunk_g_start
        if span <= 0:
            continue

        # Prefix of chunk ``source_text`` only (global char offsets align with this string).
        max_take = min(500, len(source), span)
        verbatim = source[:max_take]
        if not verbatim.strip():
            continue

        g_start = chunk_g_start
        g_end = g_start + len(verbatim)
        if g_end > chunk_g_end:
            verbatim = source[: max(1, chunk_g_end - g_start)]
            g_end = g_start + len(verbatim)

        if g_end <= g_start:
            continue

        local_start = g_start - chunk_g_start
        if local_start != 0 or source[: len(verbatim)] != verbatim:
            continue

        anchor_id = f"anchor_fallback_{index + 1:04d}"
        item_id = f"supporting_point_fallback_{index + 1:04d}"

        fallback_points.append(
            {
                "item_id": item_id,
                "item_type": "supporting_point",
                "anchor_id": anchor_id,
                "chunk_id": chunk_id,
                "source_text": verbatim,
                "context_text": source,
                "char_start": g_start,
                "char_end": g_end,
                "start_seconds": t0,
                "end_seconds": t1,
                "confidence": "fallback",
                "fallback_generated": True,
            }
        )

    argument_map["supporting_points"] = fallback_points
    argument_map["fallback_supporting_points_used"] = bool(fallback_points)
    return argument_map
