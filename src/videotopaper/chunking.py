"""Transcript chunking utilities.

Week 2 exercise: implement chunking with offset propagation manually.
"""

from collections.abc import Mapping, Sequence
from typing import Any


def chunk_transcript(
    video_id: str,
    segments: Sequence[Mapping[str, Any]],
    max_words: int = 100,
) -> list[dict[str, Any]]:
    """Group transcript segments into traceable chunks.

    Expected chunk shape:
        {
            "chunk_id": "vid_001_chunk_001",
            "video_id": "vid_001",
            "text": "...",
            "start_time": 12.4,
            "end_time": 145.2,
            "char_offset_start": 120,
            "char_offset_end": 480,
            "word_count": 650,
        }
    """
    raise NotImplementedError("Week 2 exercise: implement chunk_transcript manually.")
