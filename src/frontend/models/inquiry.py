from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


YOUTUBE_ID_PATTERN = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_-]{11})"
)


@dataclass(frozen=True)
class RunParameters:
    youtube_url: str
    video_id: str
    claim_type_filter: list[str]
    retrieval_depth: int
    source_tiers: list[int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "youtube_url": self.youtube_url,
            "video_id": self.video_id,
            "claim_type_filter": self.claim_type_filter,
            "retrieval_depth": self.retrieval_depth,
            "source_tiers": self.source_tiers,
        }


@dataclass(frozen=True)
class InquiryRecord:
    inquiry_id: str
    title: str
    youtube_url: str
    status: str
    created_at: str
    paper_path: str | None
    audit_report_path: str | None
    parameters: dict[str, Any]

    @classmethod
    def from_manifest(cls, manifest_path: Path) -> "InquiryRecord":
        import json

        with manifest_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object in {manifest_path}")

        return cls(
            inquiry_id=str(data.get("inquiry_id", manifest_path.parent.name)),
            title=str(data.get("title", "Untitled inquiry")),
            youtube_url=str(data.get("youtube_url", "")),
            status=str(data.get("status", "unknown")),
            created_at=str(data.get("created_at", "")),
            paper_path=_optional_string(data.get("paper_path")),
            audit_report_path=_optional_string(data.get("audit_report_path")),
            parameters=dict(data.get("parameters", {})),
        )


def parse_youtube_video_id(url: str) -> str:
    match = YOUTUBE_ID_PATTERN.search(url.strip())

    if not match:
        raise ValueError("Could not parse a valid YouTube video id from the URL.")

    return match.group(1)


def build_run_parameters(
    *,
    youtube_url: str,
    claim_type_filter: Iterable[str],
    retrieval_depth: int,
    source_tiers: Iterable[int],
) -> RunParameters:
    video_id = parse_youtube_video_id(youtube_url)

    if retrieval_depth < 1:
        raise ValueError("retrieval_depth must be at least 1.")

    normalized_tiers = sorted(set(int(tier) for tier in source_tiers))

    if not normalized_tiers:
        raise ValueError("At least one source tier must be selected.")

    if any(tier < 1 or tier > 3 for tier in normalized_tiers):
        raise ValueError("source_tiers must only contain tiers 1, 2, or 3.")

    normalized_claim_types = sorted(set(claim_type_filter))

    return RunParameters(
        youtube_url=youtube_url.strip(),
        video_id=video_id,
        claim_type_filter=normalized_claim_types,
        retrieval_depth=retrieval_depth,
        source_tiers=normalized_tiers,
    )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None

    value_as_string = str(value).strip()
    return value_as_string or None


__all__ = [
    "InquiryRecord",
    "RunParameters",
    "build_run_parameters",
    "parse_youtube_video_id",
]
