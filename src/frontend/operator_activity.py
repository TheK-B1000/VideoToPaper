from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


VALID_ACTIVITY_TYPES = {
    "request_created",
    "rerun_created",
    "run_launched",
    "queue_status_changed",
    "audit_opened",
    "paper_opened",
    "progress_viewed",
    "inquiry_imported",
}


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OperatorActivity":
        activity_type = str(data.get("activity_type", "")).strip()

        if activity_type not in VALID_ACTIVITY_TYPES:
            raise ValueError(f"Invalid activity type: {activity_type}")

        message = str(data.get("message", "")).strip()

        if not message:
            raise ValueError("Operator activity is missing a message.")

        return cls(
            activity_id=str(data.get("activity_id", "")),
            activity_type=activity_type,
            created_at=str(data.get("created_at", "")),
            message=message,
            request_id=_optional_string(data.get("request_id")),
            inquiry_id=_optional_string(data.get("inquiry_id")),
            run_id=_optional_string(data.get("run_id")),
            artifact_path=_optional_string(data.get("artifact_path")),
            metadata=dict(data.get("metadata", {})),
        )


def create_activity(
    *,
    activity_type: str,
    message: str,
    request_id: str | None = None,
    inquiry_id: str | None = None,
    run_id: str | None = None,
    artifact_path: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> OperatorActivity:
    normalized_type = activity_type.strip()

    if normalized_type not in VALID_ACTIVITY_TYPES:
        raise ValueError(f"Invalid activity type: {normalized_type}")

    clean_message = message.strip()

    if not clean_message:
        raise ValueError("Operator activity message cannot be empty.")

    return OperatorActivity(
        activity_id=f"activity_{uuid4().hex}",
        activity_type=normalized_type,
        created_at=datetime.now(timezone.utc).isoformat(),
        message=clean_message,
        request_id=_optional_string(request_id),
        inquiry_id=_optional_string(inquiry_id),
        run_id=_optional_string(run_id),
        artifact_path=_optional_string(artifact_path),
        metadata=metadata or {},
    )


def append_activity(
    activity: OperatorActivity,
    log_path: str | Path = "logs/operator_activity.jsonl",
) -> Path:
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(activity.to_dict()) + "\n")

    return path


def record_activity(
    *,
    activity_type: str,
    message: str,
    log_path: str | Path = "logs/operator_activity.jsonl",
    request_id: str | None = None,
    inquiry_id: str | None = None,
    run_id: str | None = None,
    artifact_path: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> OperatorActivity:
    activity = create_activity(
        activity_type=activity_type,
        message=message,
        request_id=request_id,
        inquiry_id=inquiry_id,
        run_id=run_id,
        artifact_path=artifact_path,
        metadata=metadata,
    )

    append_activity(activity, log_path=log_path)

    return activity


def read_activity_log(
    log_path: str | Path = "logs/operator_activity.jsonl",
    *,
    limit: int | None = None,
) -> list[OperatorActivity]:
    path = Path(log_path)

    if not path.exists():
        return []

    activities: list[OperatorActivity] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            clean_line = line.strip()

            if not clean_line:
                continue

            try:
                data = json.loads(clean_line)
                if isinstance(data, dict):
                    activities.append(OperatorActivity.from_dict(data))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue

    activities = sorted(
        activities,
        key=lambda item: item.created_at,
        reverse=True,
    )

    if limit is not None:
        return activities[:limit]

    return activities


def filter_activities(
    activities: list[OperatorActivity],
    *,
    activity_type: str = "all",
    query: str = "",
) -> list[OperatorActivity]:
    normalized_type = activity_type.strip()
    normalized_query = query.strip().lower()

    filtered: list[OperatorActivity] = []

    for activity in activities:
        type_matches = normalized_type == "all" or activity.activity_type == normalized_type

        query_blob = " ".join(
            item
            for item in [
                activity.message,
                activity.request_id,
                activity.inquiry_id,
                activity.run_id,
                activity.artifact_path,
            ]
            if item
        ).lower()

        query_matches = not normalized_query or normalized_query in query_blob

        if type_matches and query_matches:
            filtered.append(activity)

    return filtered


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None