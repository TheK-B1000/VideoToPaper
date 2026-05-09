from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

from src.frontend.run_request import DEFAULT_PIPELINE_STAGES


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


def advance_pipeline_tick(
    progress: dict[str, Any],
    *,
    tick_seconds: float = 2.5,
) -> dict[str, Any]:
    """
    Advance pipeline simulation by one transition (queued→running or running→completed).

    Idempotent when all steps are already completed.
    """
    p = copy.deepcopy(progress)
    steps: list[dict[str, Any]] = list(p.get("steps") or [])

    if not steps:
        p["status"] = "completed"
        p["current_step"] = None
        return p

    base_elapsed = float(p.get("elapsed_seconds") or 0.0)
    p["elapsed_seconds"] = base_elapsed + tick_seconds

    if all(str(s.get("status", "")).lower() == "completed" for s in steps):
        p["status"] = "completed"
        p["current_step"] = None
        return p

    now = datetime.now(timezone.utc).isoformat()

    for i, step in enumerate(steps):
        status = str(step.get("status", "")).lower()

        if status == "queued":
            step["status"] = "running"
            step["started_at"] = step.get("started_at") or now
            step["elapsed_seconds"] = tick_seconds
            step["message"] = f"Executing {step['name']}."
            p["steps"] = steps
            p["status"] = "running"
            p["current_step"] = str(step["name"])
            return p

        if status == "running":
            prev_elapsed = float(step.get("elapsed_seconds") or 0.0)
            step["status"] = "completed"
            step["finished_at"] = now
            step["elapsed_seconds"] = prev_elapsed + tick_seconds
            step["message"] = f"{step['name']} completed."

            remaining = steps[i + 1 :]
            if remaining:
                nxt = remaining[0]
                if str(nxt.get("status", "")).lower() == "queued":
                    nxt["status"] = "running"
                    nxt["started_at"] = now
                    nxt["elapsed_seconds"] = tick_seconds
                    nxt["message"] = f"Executing {nxt['name']}."
                    p["steps"] = steps
                    p["status"] = "running"
                    p["current_step"] = str(nxt["name"])
                    return p

            p["steps"] = steps
            p["status"] = "completed"
            p["current_step"] = None
            p["finished_at"] = now
            return p

    p["steps"] = steps
    return p
