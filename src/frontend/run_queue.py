from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.frontend.run_request import InquiryRunRequest, run_request_from_dict


VALID_QUEUE_STATUSES = {"pending", "queued", "running", "completed", "failed"}


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


def discover_run_requests(request_dir: str | Path) -> list[QueuedRunRequest]:
    root = Path(request_dir)

    if not root.exists():
        return []

    queued: list[QueuedRunRequest] = []

    for request_path in sorted(root.glob("*.json")):
        try:
            queued.append(load_queued_run_request(request_path))
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            continue

    return sorted(
        queued,
        key=lambda item: item.request.created_at,
        reverse=True,
    )


def load_queued_run_request(path: str | Path) -> QueuedRunRequest:
    request_path = Path(path)

    with request_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Queued run request file must contain a JSON object.")

    if "request" in data:
        request_data = data["request"]
        status = str(data.get("status", "pending")).strip().lower()
        progress_path = _optional_string(data.get("progress_path"))
        result_inquiry_id = _optional_string(data.get("result_inquiry_id"))
        last_updated_at = _optional_string(data.get("last_updated_at"))
    else:
        request_data = data
        status = "pending"
        progress_path = None
        result_inquiry_id = None
        last_updated_at = None

    if status not in VALID_QUEUE_STATUSES:
        raise ValueError(f"Invalid queue status: {status}")

    if not isinstance(request_data, dict):
        raise ValueError("Queued run request is missing request data.")

    request = run_request_from_dict(request_data)

    return QueuedRunRequest(
        request=request,
        status=status,
        request_path=request_path.as_posix(),
        progress_path=progress_path,
        result_inquiry_id=result_inquiry_id,
        last_updated_at=last_updated_at,
    )


def filter_queued_requests(
    queued_requests: list[QueuedRunRequest],
    *,
    query: str = "",
    status: str = "all",
) -> list[QueuedRunRequest]:
    normalized_query = query.strip().lower()
    normalized_status = status.strip().lower()

    filtered: list[QueuedRunRequest] = []

    for item in queued_requests:
        query_matches = (
            not normalized_query
            or normalized_query in item.request_id.lower()
            or normalized_query in item.youtube_url.lower()
            or normalized_query in item.request.video_id.lower()
        )

        status_matches = (
            normalized_status == "all"
            or item.status == normalized_status
        )

        if query_matches and status_matches:
            filtered.append(item)

    return filtered


def summarize_queue(queued_requests: list[QueuedRunRequest]) -> dict[str, int]:
    summary = {status: 0 for status in VALID_QUEUE_STATUSES}
    summary["total"] = len(queued_requests)
    summary["executable"] = 0

    for item in queued_requests:
        summary[item.status] += 1

        if item.is_executable:
            summary["executable"] += 1

    return summary


def wrap_request_for_queue(
    request: InquiryRunRequest,
    *,
    status: str = "pending",
    request_path: str = "",
    progress_path: str | None = None,
    result_inquiry_id: str | None = None,
    last_updated_at: str | None = None,
) -> QueuedRunRequest:
    normalized_status = status.strip().lower()

    if normalized_status not in VALID_QUEUE_STATUSES:
        raise ValueError(f"Invalid queue status: {normalized_status}")

    return QueuedRunRequest(
        request=request,
        status=normalized_status,
        request_path=request_path,
        progress_path=progress_path,
        result_inquiry_id=result_inquiry_id,
        last_updated_at=last_updated_at,
    )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None