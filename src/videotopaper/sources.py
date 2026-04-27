"""Source ingestion and speaker-context modeling.

Week 1 exercise: implement the source registry manually.
"""

from collections.abc import Mapping
from typing import Any

SpeakerContext = dict[str, str | list[str]]
VideoRecord = dict[str, Any]


def capture_speaker_context(context: Mapping[str, Any]) -> SpeakerContext:
    """Validate and normalize speaker metadata for downstream steelmanning."""
    raise NotImplementedError(
        "Week 1 exercise: implement capture_speaker_context manually."
    )


def register_video(metadata: Mapping[str, Any]) -> VideoRecord:
    """Record one video source with provenance and normalized speaker context."""
    raise NotImplementedError("Week 1 exercise: implement register_video manually.")
