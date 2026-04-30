from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from src.data.json_store import save_json


def _utc_now_iso() -> str:
    """
    Return the current UTC time as an ISO-formatted string.
    """
    return datetime.now(timezone.utc).isoformat()


def create_run_log(
    config_path: str,
    input_path: str,
    output_path: str,
    pipeline_name: str = "transcript_processing"
) -> dict:
    """
    Create a new run log dictionary.

    Args:
        config_path: Path to the config file used for this run.
        input_path: Path to the raw input file.
        output_path: Path where the output will be saved.
        pipeline_name: Name of the pipeline being executed.

    Returns:
        A run log dictionary.
    """
    if not isinstance(config_path, str):
        raise TypeError("config_path must be a string")

    if not isinstance(input_path, str):
        raise TypeError("input_path must be a string")

    if not isinstance(output_path, (str, dict)):
        raise TypeError("output_path must be a string")

    if not isinstance(pipeline_name, str):
        raise TypeError("pipeline_name must be a string")

    if not config_path.strip():
        raise ValueError("config_path cannot be empty")

    if not input_path.strip():
        raise ValueError("input_path cannot be empty")

    if not output_path.strip():
        raise ValueError("output_path cannot be empty")

    if not pipeline_name.strip():
        raise ValueError("pipeline_name cannot be empty")

    started_at = _utc_now_iso()

    return {
        "run_id": str(uuid4()),
        "pipeline_name": pipeline_name.strip(),
        "status": "running",
        "config_path": config_path.strip(),
        "input_path": input_path.strip(),
        "output_path": output_path.strip(),
        "started_at": started_at,
        "finished_at": None,
        "metrics": {},
        "errors": []
    }


def record_metric(run_log: dict, metric_name: str, metric_value) -> dict:
    """
    Record a metric in the run log.

    Args:
        run_log: Existing run log dictionary.
        metric_name: Name of the metric.
        metric_value: Value of the metric.

    Returns:
        The updated run log.
    """
    if not isinstance(run_log, dict):
        raise TypeError("run_log must be a dictionary")

    if not isinstance(metric_name, str):
        raise TypeError("metric_name must be a string")

    if not metric_name.strip():
        raise ValueError("metric_name cannot be empty")

    if "metrics" not in run_log:
        run_log["metrics"] = {}

    run_log["metrics"][metric_name.strip()] = metric_value

    return run_log


def record_error(run_log: dict, error_message: str) -> dict:
    """
    Record an error message in the run log.

    Args:
        run_log: Existing run log dictionary.
        error_message: Error message to record.

    Returns:
        The updated run log.
    """
    if not isinstance(run_log, dict):
        raise TypeError("run_log must be a dictionary")

    if not isinstance(error_message, str):
        raise TypeError("error_message must be a string")

    if not error_message.strip():
        raise ValueError("error_message cannot be empty")

    if "errors" not in run_log:
        run_log["errors"] = []

    run_log["errors"].append({
        "message": error_message.strip(),
        "recorded_at": _utc_now_iso()
    })

    return run_log


def finish_run_log(run_log: dict, status: str = "success") -> dict:
    """
    Finish a run log by setting final status and finish time.

    Args:
        run_log: Existing run log dictionary.
        status: Final status such as success or failed.

    Returns:
        The updated run log.
    """
    if not isinstance(run_log, dict):
        raise TypeError("run_log must be a dictionary")

    if not isinstance(status, str):
        raise TypeError("status must be a string")

    if not status.strip():
        raise ValueError("status cannot be empty")

    run_log["status"] = status.strip()

    finished_dt = datetime.now(timezone.utc)
    started_raw = run_log.get("started_at")
    if isinstance(started_raw, str):
        try:
            started_iso = started_raw.replace("Z", "+00:00")
            started_dt = datetime.fromisoformat(started_iso)
            if finished_dt <= started_dt:
                finished_dt = started_dt + timedelta(microseconds=1)
        except ValueError:
            pass

    run_log["finished_at"] = finished_dt.isoformat()

    return run_log


def save_run_log(run_log: dict, logs_dir: str = "logs/runs") -> str:
    """
    Save a run log to disk.

    Args:
        run_log: Run log dictionary.
        logs_dir: Directory where run logs should be saved.

    Returns:
        The path to the saved run log file.
    """
    if not isinstance(run_log, dict):
        raise TypeError("run_log must be a dictionary")

    if not isinstance(logs_dir, str):
        raise TypeError("logs_dir must be a string")

    if "run_id" not in run_log:
        raise ValueError("run_log must contain run_id")

    run_id = run_log["run_id"]
    file_path = Path(logs_dir) / f"{run_id}.json"

    save_json(run_log, str(file_path))

    return str(file_path)