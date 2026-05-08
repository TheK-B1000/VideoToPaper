from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InquiryRunRequest:
    request_id: str
    created_at: str
    youtube_url: str
    video_id: str
    claim_type_filter: list[str]
    retrieval_depth: int
    source_tiers: list[int]
    stages: list[str]
    rerun_of: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "created_at": self.created_at,
            "youtube_url": self.youtube_url,
            "video_id": self.video_id,
            "claim_type_filter": self.claim_type_filter,
            "retrieval_depth": self.retrieval_depth,
            "source_tiers": self.source_tiers,
            "stages": self.stages,
            "rerun_of": self.rerun_of,
            "reason": self.reason,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class QueuedRunRequest:
    request: InquiryRunRequest
    status: str
    request_path: str
    progress_path: str | None = None
    result_inquiry_id: str | None = None
    last_updated_at: str | None = None

    @property
    def request_id(self) -> str:
        return self.request.request_id

    @property
    def youtube_url(self) -> str:
        return self.request.youtube_url

    @property
    def created_at(self) -> str:
        return self.request.created_at

    @property
    def is_executable(self) -> bool:
        return self.status in {"pending", "queued"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "status": self.status,
            "request_path": self.request_path,
            "progress_path": self.progress_path,
            "result_inquiry_id": self.result_inquiry_id,
            "last_updated_at": self.last_updated_at,
        }


@dataclass(frozen=True)
class RerunOverrides:
    claim_type_filter: list[str] | None = None
    retrieval_depth: int | None = None
    source_tiers: list[int] | None = None
    stages: list[str] | None = None
    reason: str | None = None
    metadata: dict[str, Any] | None = None


__all__ = ["InquiryRunRequest", "QueuedRunRequest", "RerunOverrides"]

