"""Transcript chunking utilities.

Week 2 exercise: implement the chunking algorithm manually.
"""

from collections.abc import Mapping, Sequence
from typing import Any


def chunk_transcript(
    segments: Sequence[Mapping[str, Any]],
    max_words: int = 100,
) -> list[dict[str, Any]]:
    """Group timestamped transcript segments into traceable chunks.

    Expected chunk shape:
        {
            "chunk_id": "chunk_001",
            "text": "...",
            "start_time": 12.4,
            "end_time": 145.2,
            "word_count": 650,
        }
    """
    raise NotImplementedError("Week 2 exercise: implement chunk_transcript manually.")
