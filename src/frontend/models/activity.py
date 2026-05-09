from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OperatorActivity:
    activity_id: str
    activity_type: str
    created_at: str
    message: str
    request_id: str | None = None
    inquiry_id: str | None = None
    run_id: str | None = None
    artifact_path: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "activity_id": self.activity_id,
            "activity_type": self.activity_type,
            "created_at": self.created_at,
            "message": self.message,
            "request_id": self.request_id,
            "inquiry_id": self.inquiry_id,
            "run_id": self.run_id,
            "artifact_path": self.artifact_path,
            "metadata": self.metadata or {},
        }


__all__ = ["OperatorActivity"]
