import json
from pathlib import Path

import pytest

from src.ops.run_tracker import (
    create_run_log,
    finish_run_log,
    record_error,
    record_metric,
    save_run_log,
)


def test_create_run_log_success():
    run_log = create_run_log(
        config_path="configs/default_config.json",
        input_path="data/raw/raw_transcript.json",
        output_path="data/outputs/processed_transcript.json",
        pipeline_name="transcript_processing",
    )

    assert "run_id" in run_log
    assert run_log["pipeline_name"] == "transcript_processing"
    assert run_log["status"] == "running"
    assert run_log["config_path"] == "configs/default_config.json"
    assert run_log["input_path"] == "data/raw/raw_transcript.json"
    assert run_log["output_path"] == "data/outputs/processed_transcript.json"
    assert run_log["finished_at"] is None
    assert run_log["metrics"] == {}
    assert run_log["errors"] == []


def test_create_run_log_accepts_multiple_output_paths():
    output_paths = {
        "chunks": "data/outputs/chunks.json",
        "argument_map": "data/outputs/argument_map.json",
        "anchor_moments": "data/outputs/anchor_moments.json",
    }

    run_log = create_run_log(
        config_path="configs/argument_config.json",
        input_path="data/outputs/processed_transcript.json",
        output_path=output_paths,
        pipeline_name="argument_structure",
    )

    assert run_log["output_path"] == output_paths
    assert run_log["pipeline_name"] == "argument_structure"
    assert run_log["status"] == "running"


def test_create_run_log_rejects_empty_output_path_dict():
    with pytest.raises(ValueError, match="output_path cannot be an empty dictionary"):
        create_run_log(
            config_path="configs/argument_config.json",
            input_path="data/outputs/processed_transcript.json",
            output_path={},
            pipeline_name="argument_structure",
        )


def test_create_run_log_rejects_empty_output_path_string():
    with pytest.raises(ValueError, match="output_path cannot be empty"):
        create_run_log(
            config_path="configs/default_config.json",
            input_path="data/raw/raw_transcript.json",
            output_path="   ",
            pipeline_name="transcript_processing",
        )


def test_create_run_log_rejects_invalid_output_path_type():
    with pytest.raises(TypeError, match="output_path must be a string or dictionary"):
        create_run_log(
            config_path="configs/default_config.json",
            input_path="data/raw/raw_transcript.json",
            output_path=["data/outputs/processed_transcript.json"],
            pipeline_name="transcript_processing",
        )


def test_create_run_log_rejects_empty_config_path():
    with pytest.raises(ValueError, match="config_path cannot be empty"):
        create_run_log(
            config_path="   ",
            input_path="data/raw/raw_transcript.json",
            output_path="data/outputs/processed_transcript.json",
        )


def test_create_run_log_rejects_empty_input_path():
    with pytest.raises(ValueError, match="input_path cannot be empty"):
        create_run_log(
            config_path="configs/default_config.json",
            input_path="   ",
            output_path="data/outputs/processed_transcript.json",
        )


def test_create_run_log_rejects_empty_pipeline_name():
    with pytest.raises(ValueError, match="pipeline_name cannot be empty"):
        create_run_log(
            config_path="configs/default_config.json",
            input_path="data/raw/raw_transcript.json",
            output_path="data/outputs/processed_transcript.json",
            pipeline_name="   ",
        )


def test_record_metric_adds_metric():
    run_log = create_run_log(
        config_path="configs/default_config.json",
        input_path="data/raw/raw_transcript.json",
        output_path="data/outputs/processed_transcript.json",
    )

    updated = record_metric(run_log, "processed_segment_count", 3)

    assert updated["metrics"]["processed_segment_count"] == 3


def test_record_metric_rejects_empty_metric_name():
    run_log = create_run_log(
        config_path="configs/default_config.json",
        input_path="data/raw/raw_transcript.json",
        output_path="data/outputs/processed_transcript.json",
    )

    with pytest.raises(ValueError, match="metric_name cannot be empty"):
        record_metric(run_log, "   ", 3)


def test_record_error_adds_error():
    run_log = create_run_log(
        config_path="configs/default_config.json",
        input_path="data/raw/raw_transcript.json",
        output_path="data/outputs/processed_transcript.json",
    )

    updated = record_error(run_log, "Something went wrong")

    assert len(updated["errors"]) == 1
    assert updated["errors"][0]["message"] == "Something went wrong"
    assert "recorded_at" in updated["errors"][0]


def test_record_error_rejects_empty_error_message():
    run_log = create_run_log(
        config_path="configs/default_config.json",
        input_path="data/raw/raw_transcript.json",
        output_path="data/outputs/processed_transcript.json",
    )

    with pytest.raises(ValueError, match="error_message cannot be empty"):
        record_error(run_log, "   ")


def test_finish_run_log_sets_status_and_finished_at():
    run_log = create_run_log(
        config_path="configs/default_config.json",
        input_path="data/raw/raw_transcript.json",
        output_path="data/outputs/processed_transcript.json",
    )

    finished = finish_run_log(run_log, status="success")

    assert finished["status"] == "success"
    assert finished["finished_at"] is not None


def test_save_run_log_writes_file(tmp_path):
    run_log = create_run_log(
        config_path="configs/default_config.json",
        input_path="data/raw/raw_transcript.json",
        output_path="data/outputs/processed_transcript.json",
    )

    saved_path = save_run_log(run_log, logs_dir=str(tmp_path))

    assert Path(saved_path).exists()

    with open(saved_path, "r", encoding="utf-8") as file:
        saved_data = json.load(file)

    assert saved_data["run_id"] == run_log["run_id"]
    assert saved_data["pipeline_name"] == run_log["pipeline_name"]


def test_save_run_log_uses_run_id_as_filename(tmp_path):
    run_log = create_run_log(
        config_path="configs/default_config.json",
        input_path="data/raw/raw_transcript.json",
        output_path="data/outputs/processed_transcript.json",
    )

    saved_path = save_run_log(run_log, logs_dir=str(tmp_path))

    assert Path(saved_path).name == f"{run_log['run_id']}.json"


def test_save_run_log_rejects_missing_run_id(tmp_path):
    run_log = {
        "pipeline_name": "transcript_processing",
        "status": "running",
    }

    with pytest.raises(ValueError, match="run_log must contain run_id"):
        save_run_log(run_log, logs_dir=str(tmp_path))