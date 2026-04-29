import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.ops.run_tracker import (
    create_run_log,
    record_metric,
    record_error,
    finish_run_log,
    save_run_log,
)


def test_create_run_log_creates_running_log():
    run_log = create_run_log(
        config_path="configs/default_config.json",
        input_path="data/raw/raw_transcript.json",
        output_path="data/processed/clean_transcript.json"
    )

    assert "run_id" in run_log
    assert run_log["pipeline_name"] == "transcript_processing"
    assert run_log["status"] == "running"
    assert run_log["config_path"] == "configs/default_config.json"
    assert run_log["input_path"] == "data/raw/raw_transcript.json"
    assert run_log["output_path"] == "data/processed/clean_transcript.json"
    assert run_log["finished_at"] is None
    assert run_log["metrics"] == {}
    assert run_log["errors"] == []


def test_create_run_log_rejects_empty_input_path():
    try:
        create_run_log(
            config_path="configs/default_config.json",
            input_path="   ",
            output_path="data/processed/clean_transcript.json"
        )
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


def test_record_metric_adds_metric():
    run_log = create_run_log(
        config_path="configs/default_config.json",
        input_path="data/raw/raw_transcript.json",
        output_path="data/processed/clean_transcript.json"
    )

    record_metric(run_log, "segment_count", 3)

    assert run_log["metrics"]["segment_count"] == 3


def test_record_metric_rejects_empty_metric_name():
    run_log = create_run_log(
        config_path="configs/default_config.json",
        input_path="data/raw/raw_transcript.json",
        output_path="data/processed/clean_transcript.json"
    )

    try:
        record_metric(run_log, "   ", 3)
        assert False, "Expected ValueError, but no error was raised"
    except ValueError:
        pass


def test_record_error_adds_error():
    run_log = create_run_log(
        config_path="configs/default_config.json",
        input_path="data/raw/raw_transcript.json",
        output_path="data/processed/clean_transcript.json"
    )

    record_error(run_log, "something failed")

    assert len(run_log["errors"]) == 1
    assert run_log["errors"][0]["message"] == "something failed"
    assert "recorded_at" in run_log["errors"][0]


def test_finish_run_log_sets_status_and_finished_at():
    run_log = create_run_log(
        config_path="configs/default_config.json",
        input_path="data/raw/raw_transcript.json",
        output_path="data/processed/clean_transcript.json"
    )

    finish_run_log(run_log, "success")

    assert run_log["status"] == "success"
    assert run_log["finished_at"] is not None


def test_save_run_log_writes_file():
    run_log = create_run_log(
        config_path="configs/default_config.json",
        input_path="data/raw/raw_transcript.json",
        output_path="data/processed/clean_transcript.json"
    )

    finish_run_log(run_log, "success")

    saved_path = save_run_log(run_log, "logs/test_runs")

    assert Path(saved_path).exists()


test_create_run_log_creates_running_log()
test_create_run_log_rejects_empty_input_path()
test_record_metric_adds_metric()
test_record_metric_rejects_empty_metric_name()
test_record_error_adds_error()
test_finish_run_log_sets_status_and_finished_at()
test_save_run_log_writes_file()

print("All run_tracker tests passed.")