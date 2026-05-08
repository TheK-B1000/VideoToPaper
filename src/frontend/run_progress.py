from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VALID_STEP_STATUSES = {"queued", "running", "completed", "failed", "skipped"}


@dataclass(frozen=True)
class ProgressStep:
    name: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    elapsed_seconds: float | None = None
    message: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProgressStep":
        name = str(data.get("name", "")).strip()
        status = str(data.get("status", "")).strip().lower()

        if not name:
            raise ValueError("Progress step is missing a name.")

        if status not in VALID_STEP_STATUSES:
            raise ValueError(f"Invalid progress step status: {status}")

        elapsed = data.get("elapsed_seconds")

        return cls(
            name=name,
            status=status,
            started_at=_optional_string(data.get("started_at")),
            finished_at=_optional_string(data.get("finished_at")),
            elapsed_seconds=float(elapsed) if elapsed is not None else None,
            message=_optional_string(data.get("message")),
        )


@dataclass(frozen=True)
class RunProgress:
    run_id: str
    status: str
    current_step: str | None
    elapsed_seconds: float | None
    steps: list[ProgressStep]

    @property
    def completion_ratio(self) -> float:
        if not self.steps:
            return 0.0

        completed_count = sum(1 for step in self.steps if step.status == "completed")
        return completed_count / len(self.steps)

    @property
    def has_failed(self) -> bool:
        return any(step.status == "failed" for step in self.steps)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunProgress":
        run_id = str(data.get("run_id", "")).strip()
        status = str(data.get("status", "")).strip().lower()

        if not run_id:
            raise ValueError("Run progress is missing run_id.")

        if status not in VALID_STEP_STATUSES:
            raise ValueError(f"Invalid run status: {status}")

        raw_steps = data.get("steps", [])

        if not isinstance(raw_steps, list):
            raise ValueError("Run progress steps must be a list.")

        steps = [ProgressStep.from_dict(step) for step in raw_steps]

        elapsed = data.get("elapsed_seconds")

        return cls(
            run_id=run_id,
            status=status,
            current_step=_optional_string(data.get("current_step")),
            elapsed_seconds=float(elapsed) if elapsed is not None else None,
            steps=steps,
        )


def load_run_progress(path: str | Path) -> RunProgress | None:
    progress_path = Path(path)

    if not progress_path.exists():
        return None

    with progress_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Run progress file must contain a JSON object.")

    return RunProgress.from_dict(data)


def summarize_progress(progress: RunProgress) -> dict[str, Any]:
    completed = sum(1 for step in progress.steps if step.status == "completed")
    failed = sum(1 for step in progress.steps if step.status == "failed")
    running = sum(1 for step in progress.steps if step.status == "running")
    queued = sum(1 for step in progress.steps if step.status == "queued")
    skipped = sum(1 for step in progress.steps if step.status == "skipped")

    return {
        "run_id": progress.run_id,
        "status": progress.status,
        "current_step": progress.current_step,
        "elapsed_seconds": progress.elapsed_seconds,
        "completion_ratio": progress.completion_ratio,
        "completed_steps": completed,
        "failed_steps": failed,
        "running_steps": running,
        "queued_steps": queued,
        "skipped_steps": skipped,
        "total_steps": len(progress.steps),
        "has_failed": progress.has_failed,
    }


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None