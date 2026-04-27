"""Transcript ingestion, normalization, and offset validation.

Week 1 exercise: implement these functions manually.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

TranscriptSegment = dict[str, str | float | int]
TranscriptDocument = dict[str, str | list[TranscriptSegment]]


def clean_text(text: str) -> str:
    """Normalize transcript text without invalidating downstream offsets."""
    raise NotImplementedError("Week 1 exercise: implement clean_text manually.")


def validate_segment(
    segment: Mapping[str, Any],
    source_text: str,
) -> TranscriptSegment:
    """Validate one transcript segment against the offset-preserving schema."""
    raise NotImplementedError("Week 1 exercise: implement validate_segment manually.")


def load_transcript(path: str | Path) -> TranscriptDocument:
    """Load transcript text plus timestamped, character-anchored segments."""
    raise NotImplementedError("Week 1 exercise: implement load_transcript manually.")
