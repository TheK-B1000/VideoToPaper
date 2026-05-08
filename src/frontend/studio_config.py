from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_STUDIO_CONFIG_PATH = "configs/studio_config.json"


@dataclass(frozen=True)
class StudioConfig:
    inquiry_library_dir: str
    run_requests_dir: str
    runs_dir: str
    operator_activity_log_path: str
    default_audit_report_path: str | None = None
    default_progress_log_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "inquiry_library_dir": self.inquiry_library_dir,
            "run_requests_dir": self.run_requests_dir,
            "runs_dir": self.runs_dir,
            "operator_activity_log_path": self.operator_activity_log_path,
            "default_audit_report_path": self.default_audit_report_path,
            "default_progress_log_path": self.default_progress_log_path,
        }


def default_studio_config() -> StudioConfig:
    return StudioConfig(
        inquiry_library_dir="data/inquiries",
        run_requests_dir="data/run_requests",
        runs_dir="logs/runs",
        operator_activity_log_path="logs/operator_activity.jsonl",
        default_audit_report_path=None,
        default_progress_log_path="logs/runs/latest_progress.json",
    )


def load_studio_config(
    config_path: str | Path = DEFAULT_STUDIO_CONFIG_PATH,
) -> StudioConfig:
    path = Path(config_path)

    if not path.exists():
        return default_studio_config()

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Studio config must contain a JSON object.")

    return studio_config_from_dict(data)


def studio_config_from_dict(data: dict[str, Any]) -> StudioConfig:
    defaults = default_studio_config().to_dict()
    merged = {**defaults, **data}

    return StudioConfig(
        inquiry_library_dir=_required_string(
            merged,
            "inquiry_library_dir",
        ),
        run_requests_dir=_required_string(
            merged,
            "run_requests_dir",
        ),
        runs_dir=_required_string(
            merged,
            "runs_dir",
        ),
        operator_activity_log_path=_required_string(
            merged,
            "operator_activity_log_path",
        ),
        default_audit_report_path=_optional_string(
            merged.get("default_audit_report_path"),
        ),
        default_progress_log_path=_optional_string(
            merged.get("default_progress_log_path"),
        ),
    )


def ensure_studio_directories(config: StudioConfig) -> None:
    Path(config.inquiry_library_dir).mkdir(parents=True, exist_ok=True)
    Path(config.run_requests_dir).mkdir(parents=True, exist_ok=True)
    Path(config.runs_dir).mkdir(parents=True, exist_ok=True)
    Path(config.operator_activity_log_path).parent.mkdir(parents=True, exist_ok=True)


def save_studio_config(
    config: StudioConfig,
    config_path: str | Path = DEFAULT_STUDIO_CONFIG_PATH,
) -> Path:
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(config.to_dict(), indent=2),
        encoding="utf-8",
    )

    return path


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)

    if value is None:
        raise ValueError(f"Studio config is missing required key: {key}")

    text = str(value).strip()

    if not text:
        raise ValueError(f"Studio config key cannot be empty: {key}")

    return text


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None