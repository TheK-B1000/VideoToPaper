from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.frontend.run_queue import QueuedRunRequest, load_queued_run_request
from src.frontend.run_request import DEFAULT_PIPELINE_STAGES


@dataclass(frozen=True)
class LocalRunLaunch:
    run_id: str
    run_dir: str
    request_snapshot_path: str
    progress_path: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "run_dir": self.run_dir,
            "request_snapshot_path": self.request_snapshot_path,
            "progress_path": self.progress_path,
            "status": self.status,
        }


def launch_local_run_from_request_file(
    request_path: str | Path,
    *,
    runs_dir: str | Path = "logs/runs",
) -> LocalRunLaunch:
    queued_request = load_queued_run_request(request_path)
    return launch_local_run(queued_request, runs_dir=runs_dir)


def launch_local_run(
    queued_request: QueuedRunRequest,
    *,
    runs_dir: str | Path = "logs/runs",
) -> LocalRunLaunch:
    """
    Create a local run folder and initial progress log for a queued request.

    This is intentionally a launcher stub. It prepares the frontend/backend handoff
    without executing the full inquiry pipeline yet.
    """
    if not queued_request.is_executable:
        raise ValueError(
            f"Request {queued_request.request_id} is not executable from status "
            f"{queued_request.status!r}."
        )

    run_id = build_run_id(queued_request.request.request_id)
    run_dir = Path(runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    request_snapshot_path = run_dir / "request.json"
    progress_path = run_dir / "progress.json"

    if queued_request.request_path:
        source_path = Path(queued_request.request_path)
        if source_path.exists():
            shutil.copyfile(source_path, request_snapshot_path)
        else:
            request_snapshot_path.write_text(
                json.dumps(queued_request.request.to_dict(), indent=2),
                encoding="utf-8",
            )
    else:
        request_snapshot_path.write_text(
            json.dumps(queued_request.request.to_dict(), indent=2),
            encoding="utf-8",
        )

    initial_progress = build_initial_progress_log(
        run_id=run_id,
        request_id=queued_request.request_id,
        stages=queued_request.request.stages,
    )

    progress_path.write_text(
        json.dumps(initial_progress, indent=2),
        encoding="utf-8",
    )

    return LocalRunLaunch(
        run_id=run_id,
        run_dir=run_dir.as_posix(),
        request_snapshot_path=request_snapshot_path.as_posix(),
        progress_path=progress_path.as_posix(),
        status="queued",
    )


def build_run_id(request_id: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_request_id = request_id.replace("/", "_").replace("\\", "_")
    return f"run_{timestamp}_{safe_request_id}"


def build_initial_progress_log(
    *,
    run_id: str,
    request_id: str,
    stages: list[str] | None = None,
) -> dict[str, Any]:
    selected_stages = DEFAULT_PIPELINE_STAGES if stages is None else stages

    if not selected_stages:
        raise ValueError("At least one stage is required to build a progress log.")

    now = datetime.now(timezone.utc).isoformat()

    return {
        "run_id": run_id,
        "request_id": request_id,
        "status": "queued",
        "current_step": selected_stages[0],
        "created_at": now,
        "started_at": None,
        "finished_at": None,
        "elapsed_seconds": 0.0,
        "steps": [
            {
                "name": stage,
                "status": "queued",
                "started_at": None,
                "finished_at": None,
                "elapsed_seconds": None,
                "message": "Waiting to execute.",
            }
            for stage in selected_stages
        ],
    }