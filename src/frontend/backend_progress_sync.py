from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.frontend.backend_client import BackendClient, BackendResponse
from src.frontend.run_progress import RunProgress


@dataclass(frozen=True)
class BackendProgressSyncResult:
    synced: bool
    run_id: str
    progress: RunProgress | None
    snapshot_path: str | None
    message: str
    response_data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "synced": self.synced,
            "run_id": self.run_id,
            "progress": _progress_to_dict(self.progress),
            "snapshot_path": self.snapshot_path,
            "message": self.message,
            "response_data": self.response_data,
        }


def sync_backend_progress(
    *,
    run_id: str,
    client: BackendClient,
    snapshot_dir: str | Path | None = None,
) -> BackendProgressSyncResult:
    clean_run_id = run_id.strip()

    if not clean_run_id:
        raise ValueError("run_id cannot be empty.")

    response = client.get_run_progress(clean_run_id)

    return backend_response_to_progress_sync_result(
        response,
        run_id=clean_run_id,
        snapshot_dir=snapshot_dir,
    )


def backend_response_to_progress_sync_result(
    response: BackendResponse,
    *,
    run_id: str,
    snapshot_dir: str | Path | None = None,
) -> BackendProgressSyncResult:
    if not response.ok:
        return BackendProgressSyncResult(
            synced=False,
            run_id=run_id,
            progress=None,
            snapshot_path=None,
            message=response.error_message or "Backend progress sync failed.",
            response_data=response.data,
        )

    try:
        progress = RunProgress.from_dict(normalize_backend_progress_payload(response.data, run_id=run_id))
    except ValueError as error:
        return BackendProgressSyncResult(
            synced=False,
            run_id=run_id,
            progress=None,
            snapshot_path=None,
            message=str(error),
            response_data=response.data,
        )

    snapshot_path = None

    if snapshot_dir is not None:
        snapshot_path = save_progress_snapshot(
            progress,
            snapshot_dir=snapshot_dir,
        ).as_posix()

    return BackendProgressSyncResult(
        synced=True,
        run_id=run_id,
        progress=progress,
        snapshot_path=snapshot_path,
        message="Backend progress synced.",
        response_data=response.data,
    )


def normalize_backend_progress_payload(
    payload: dict[str, Any],
    *,
    run_id: str,
) -> dict[str, Any]:
    """
    Convert likely backend progress response shapes into the frontend RunProgress shape.

    Supported backend shapes:

    1. Native frontend shape:
       {
         "run_id": "...",
         "status": "running",
         "current_step": "...",
         "elapsed_seconds": 12.0,
         "steps": [...]
       }

    2. Wrapped shape:
       {
         "progress": {
           "status": "running",
           "steps": [...]
         }
       }

    3. Minimal API shape:
       {
         "status": "running",
         "stage": "claim_inventory",
         "elapsed_seconds": 12.0
       }
    """
    if "progress" in payload and isinstance(payload["progress"], dict):
        progress_payload = dict(payload["progress"])
    else:
        progress_payload = dict(payload)

    progress_payload["run_id"] = (
        str(progress_payload.get("run_id") or payload.get("run_id") or run_id).strip()
    )
    progress_payload.setdefault("status", payload.get("status", "running"))
    progress_payload.setdefault(
        "current_step",
        payload.get("current_step") or payload.get("stage"),
    )
    progress_payload.setdefault("elapsed_seconds", payload.get("elapsed_seconds"))

    if "steps" not in progress_payload:
        current_step = progress_payload.get("current_step") or "backend_execution"

        progress_payload["steps"] = [
            {
                "name": str(current_step),
                "status": str(progress_payload.get("status", "running")).lower(),
                "elapsed_seconds": progress_payload.get("elapsed_seconds"),
                "message": payload.get("message") or "Progress reported by backend.",
            }
        ]

    return progress_payload


def save_progress_snapshot(
    progress: RunProgress,
    *,
    snapshot_dir: str | Path,
) -> Path:
    root = Path(snapshot_dir)
    root.mkdir(parents=True, exist_ok=True)

    output_path = root / f"{progress.run_id}_progress.json"

    output_path.write_text(
        json.dumps(_progress_to_dict(progress), indent=2),
        encoding="utf-8",
    )

    return output_path


def _progress_to_dict(progress: RunProgress | None) -> dict[str, Any] | None:
    if progress is None:
        return None

    return {
        "run_id": progress.run_id,
        "status": progress.status,
        "current_step": progress.current_step,
        "elapsed_seconds": progress.elapsed_seconds,
        "steps": [
            {
                "name": step.name,
                "status": step.status,
                "started_at": step.started_at,
                "finished_at": step.finished_at,
                "elapsed_seconds": step.elapsed_seconds,
                "message": step.message,
            }
            for step in progress.steps
        ],
    }