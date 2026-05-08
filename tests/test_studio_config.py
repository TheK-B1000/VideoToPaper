import json
from pathlib import Path

import pytest

from src.frontend.studio_config import (
    StudioConfig,
    default_studio_config,
    ensure_studio_directories,
    load_studio_config,
    save_studio_config,
    studio_config_from_dict,
)


def test_default_studio_config_contains_expected_paths():
    config = default_studio_config()

    assert config.inquiry_library_dir == "data/inquiries"
    assert config.run_requests_dir == "data/run_requests"
    assert config.runs_dir == "logs/runs"
    assert config.operator_activity_log_path == "logs/operator_activity.jsonl"
    assert config.default_progress_log_path == "logs/runs/latest_progress.json"


def test_studio_config_from_dict_merges_defaults():
    config = studio_config_from_dict(
        {
            "run_requests_dir": "custom/run_requests",
        }
    )

    assert config.inquiry_library_dir == "data/inquiries"
    assert config.run_requests_dir == "custom/run_requests"
    assert config.runs_dir == "logs/runs"


def test_studio_config_from_dict_rejects_empty_required_value():
    with pytest.raises(ValueError, match="cannot be empty"):
        studio_config_from_dict(
            {
                "runs_dir": " ",
            }
        )


def test_load_studio_config_returns_default_when_file_missing(tmp_path: Path):
    config = load_studio_config(tmp_path / "missing.json")

    assert config == default_studio_config()


def test_load_studio_config_reads_json_file(tmp_path: Path):
    config_path = tmp_path / "studio_config.json"

    config_path.write_text(
        json.dumps(
            {
                "inquiry_library_dir": "custom/inquiries",
                "run_requests_dir": "custom/requests",
                "runs_dir": "custom/runs",
                "operator_activity_log_path": "custom/logs/activity.jsonl",
                "default_audit_report_path": "custom/audit.json",
                "default_progress_log_path": "custom/progress.json",
            }
        ),
        encoding="utf-8",
    )

    config = load_studio_config(config_path)

    assert config.inquiry_library_dir == "custom/inquiries"
    assert config.run_requests_dir == "custom/requests"
    assert config.runs_dir == "custom/runs"
    assert config.operator_activity_log_path == "custom/logs/activity.jsonl"
    assert config.default_audit_report_path == "custom/audit.json"
    assert config.default_progress_log_path == "custom/progress.json"


def test_load_studio_config_rejects_non_object_json(tmp_path: Path):
    config_path = tmp_path / "studio_config.json"
    config_path.write_text(json.dumps(["bad"]), encoding="utf-8")

    with pytest.raises(ValueError, match="JSON object"):
        load_studio_config(config_path)


def test_save_studio_config_round_trip(tmp_path: Path):
    config = StudioConfig(
        inquiry_library_dir="a/inquiries",
        run_requests_dir="a/requests",
        runs_dir="a/runs",
        operator_activity_log_path="a/logs/activity.jsonl",
        default_audit_report_path="a/audit.json",
        default_progress_log_path="a/progress.json",
    )

    config_path = save_studio_config(config, tmp_path / "studio_config.json")
    loaded = load_studio_config(config_path)

    assert loaded == config


def test_ensure_studio_directories_creates_required_dirs(tmp_path: Path):
    config = StudioConfig(
        inquiry_library_dir=(tmp_path / "data" / "inquiries").as_posix(),
        run_requests_dir=(tmp_path / "data" / "run_requests").as_posix(),
        runs_dir=(tmp_path / "logs" / "runs").as_posix(),
        operator_activity_log_path=(
            tmp_path / "logs" / "operator_activity.jsonl"
        ).as_posix(),
    )

    ensure_studio_directories(config)

    assert Path(config.inquiry_library_dir).exists()
    assert Path(config.run_requests_dir).exists()
    assert Path(config.runs_dir).exists()
    assert Path(config.operator_activity_log_path).parent.exists()