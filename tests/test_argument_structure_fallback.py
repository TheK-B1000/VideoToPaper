"""Tests for Week 2 supporting_points fallback when extraction is sparse."""

from __future__ import annotations

import pytest

from src.argument.argument_map_fallback import ensure_argument_map_has_supporting_points
from src.argument.argument_map_validator import validate_argument_item
from src.pipelines.claim_inventory_pipeline import candidate_claims_from_argument_map


def test_fallback_fills_empty_supporting_points_from_chunks() -> None:
    argument_map: dict = {
        "map_type": "heuristic_argument_map",
        "thesis_candidates": [],
        "supporting_points": [],
        "qualifications": [],
        "examples": [],
        "summary_claims": [],
    }
    chunks = [
        {
            "chunk_id": "c1",
            "source_text": "First chunk claim about the topic.",
            "char_start": 0,
            "char_end": 40,
            "start_seconds": 0.0,
            "end_seconds": 5.0,
        },
        {
            "chunk_id": "c2",
            "source_text": "Second supporting sentence here.",
            "char_start": 40,
            "char_end": 80,
            "start_seconds": 5.0,
            "end_seconds": 10.0,
        },
    ]

    out = ensure_argument_map_has_supporting_points(argument_map, chunks, max_points=5)

    assert out is argument_map
    assert out["fallback_supporting_points_used"] is True
    pts = out["supporting_points"]
    assert len(pts) == 2
    assert pts[0]["chunk_id"] == "c1"
    assert pts[0]["fallback_generated"] is True
    assert pts[0]["source_text"] == "First chunk claim about the topic."
    assert pts[0]["char_start"] == 0
    assert pts[0]["char_end"] == len(pts[0]["source_text"])

    by_id = {c["chunk_id"]: c for c in chunks}
    candidates = candidate_claims_from_argument_map(out, by_id)
    assert len(candidates) == 2


def test_fallback_respects_existing_supporting_points() -> None:
    existing = [
        {
            "item_id": "supporting_point_001",
            "item_type": "supporting_point",
            "anchor_id": "anchor_001",
            "chunk_id": "c1",
            "source_text": "x",
            "char_start": 0,
            "char_end": 1,
            "start_seconds": 0.0,
            "end_seconds": 1.0,
        }
    ]
    argument_map: dict = {
        "map_type": "heuristic_argument_map",
        "thesis_candidates": [],
        "supporting_points": existing,
        "qualifications": [],
        "examples": [],
        "summary_claims": [],
    }
    chunks = [
        {
            "chunk_id": "c1",
            "source_text": "Ignored because supporting_points already set.",
            "char_start": 0,
            "char_end": 50,
            "start_seconds": 0.0,
            "end_seconds": 1.0,
        },
    ]

    out = ensure_argument_map_has_supporting_points(argument_map, chunks)

    assert out["supporting_points"] is existing
    assert out["fallback_supporting_points_used"] is False


def test_fallback_empty_chunks_leaves_supporting_points_empty() -> None:
    argument_map: dict = {
        "map_type": "heuristic_argument_map",
        "thesis_candidates": [],
        "supporting_points": [],
        "qualifications": [],
        "examples": [],
        "summary_claims": [],
    }

    out = ensure_argument_map_has_supporting_points(argument_map, [], max_points=5)

    assert out["supporting_points"] == []
    assert out["fallback_supporting_points_used"] is False


def test_validate_item_accepts_fallback_without_known_anchor() -> None:
    item = {
        "item_id": "supporting_point_fallback_0001",
        "item_type": "supporting_point",
        "anchor_id": "anchor_fallback_0001",
        "chunk_id": "c1",
        "source_text": "hello",
        "char_start": 0,
        "char_end": 5,
        "start_seconds": 0.0,
        "end_seconds": 1.0,
        "fallback_generated": True,
    }
    res = validate_argument_item(item, known_anchor_ids=set())
    assert res["valid"] is True
    assert res["anchor_reference_valid"] is True


def test_validate_item_non_fallback_still_requires_anchor() -> None:
    item = {
        "item_id": "supporting_point_001",
        "item_type": "supporting_point",
        "anchor_id": "anchor_missing",
        "chunk_id": "c1",
        "source_text": "hello",
        "char_start": 0,
        "char_end": 5,
        "start_seconds": 0.0,
        "end_seconds": 1.0,
    }
    res = validate_argument_item(item, known_anchor_ids={"anchor_real"})
    assert res["valid"] is False
    assert res["anchor_reference_valid"] is False
