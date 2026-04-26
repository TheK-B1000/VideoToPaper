"""Transcript ingestion, cleaning, validation, and persistence.

Week 1 exercise: implement these functions manually.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

TranscriptSegment = dict[str, str | float]


def clean_text(text: str) -> str:
    """Normalize transcript text before it enters the pipeline."""
    raise NotImplementedError("Week 1 exercise: implement clean_text manually.")


def validate_segment(segment: Mapping[str, Any]) -> TranscriptSegment:
    """Validate one transcript segment against the canonical schema."""
    raise NotImplementedError("Week 1 exercise: implement validate_segment manually.")


def load_transcript(path: str | Path) -> list[TranscriptSegment]:
    """Load and validate transcript segments from disk."""
    raise NotImplementedError("Week 1 exercise: implement load_transcript manually.")


def save_transcript(segments: list[TranscriptSegment], path: str | Path) -> None:
    """Persist canonical transcript segments to disk as stable JSON."""
    raise NotImplementedError("Week 1 exercise: implement save_transcript manually.")
