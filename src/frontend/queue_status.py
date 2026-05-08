from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.frontend.run_queue import (
    VALID_QUEUE_STATUSES,
    QueuedRunRequest,
    load_queued_run_request,
)


def update_queue_status_file(
    request_path: str | Path,
    *,
    status: str,
    progress_path: str | None = None,
    result_inquiry_id: str | None = None,
) -> Path:
    """
    Update a run request file into the wrapped queue format.

    Plain request files are supported. They are converted into:

    {
      "request": {...},
      "status": "queued",
      "progress_path": "...",
      "result_inquiry_id": null,
      "last_updated_at": "..."
    }
    """
    normalized_status = status.strip().lower()

    if normalized_status not in VALID_QUEUE_STATUSES:
        raise ValueError(f"Invalid queue status: {normalized_status}")

    path = Path(request_path)
    queued = load_queued_run_request(path)

    payload = build_queue_status_payload(
        queued,
        status=normalized_status,
        progress_path=progress_path,
        result_inquiry_id=result_inquiry_id,
    )

    path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    return path


def build_queue_status_payload(
    queued: QueuedRunRequest,
    *,
    status: str,
    progress_path: str | None = None,
    result_inquiry_id: str | None = None,
) -> dict[str, Any]:
    normalized_status = status.strip().lower()

    if normalized_status not in VALID_QUEUE_STATUSES:
        raise ValueError(f"Invalid queue status: {normalized_status}")

    return {
        "request": queued.request.to_dict(),
        "status": normalized_status,
        "request_path": queued.request_path,
        "progress_path": progress_path if progress_path is not None else queued.progress_path,
        "result_inquiry_id": (
            result_inquiry_id
            if result_inquiry_id is not None
            else queued.result_inquiry_id
        ),
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
    }


def mark_request_queued(
    request_path: str | Path,
    *,
    progress_path: str,
) -> Path:
    return update_queue_status_file(
        request_path,
        status="queued",
        progress_path=progress_path,
    )


def mark_request_running(
    request_path: str | Path,
    *,
    progress_path: str | None = None,
) -> Path:
    return update_queue_status_file(
        request_path,
        status="running",
        progress_path=progress_path,
    )


def mark_request_completed(
    request_path: str | Path,
    *,
    result_inquiry_id: str,
    progress_path: str | None = None,
) -> Path:
    return update_queue_status_file(
        request_path,
        status="completed",
        progress_path=progress_path,
        result_inquiry_id=result_inquiry_id,
    )


def mark_request_failed(
    request_path: str | Path,
    *,
    progress_path: str | None = None,
) -> Path:
    return update_queue_status_file(
        request_path,
        status="failed",
        progress_path=progress_path,
    )