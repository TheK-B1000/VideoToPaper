"""Argument-structure extraction utilities.

Week 2 exercise: implement the argument mapper manually.
"""

from collections.abc import Mapping, Sequence
from typing import Any


def extract_argument_map(
    video_id: str,
    chunks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Extract a speaker-centric argument map from transcript chunks.

    Expected output shape:
        {
            "video_id": "vid_001",
            "thesis": "...",
            "supporting_points": [
                {
                    "claim": "...",
                    "evidence_offered": ["..."],
                    "qualifications": ["..."],
                    "anchor_chunks": ["vid_001_chunk_001"],
                }
            ],
            "examples_used": ["..."],
            "explicit_concessions": ["..."],
        }
    """
    raise NotImplementedError(
        "Week 2 exercise: implement extract_argument_map manually."
    )
