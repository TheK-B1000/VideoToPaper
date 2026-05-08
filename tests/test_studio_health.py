from pathlib import Path

from src.frontend.studio_config import StudioConfig
from src.frontend.studio_health import (
    check_directory_exists,
    check_directory_writable,
    check_optional_file_reference,
    check_parent_directory_writable,
    run_studio_health_checks,
)


def test_check_directory_exists_passes_for_existing_directory(tmp_path: Path):
    result = check_directory_exists("Test directory", tmp_path)

    assert result.status == "pass"
    assert result.is_passing is True
    assert result.path == tmp_path.as_posix()


def test_check_directory_exists_fails_for_missing_directory(tmp_path: Path):
    missing = tmp_path / "missing"

    result = check_directory_exists("Missing directory", missing)

    assert result.status == "fail"
    assert result.is_failing is True
    assert result.message == "Directory does not exist."


def test_check_directory_exists_fails_when_path_is_file(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("not a directory", encoding="utf-8")

    result = check_directory_exists("File path", file_path)

    assert result.status == "fail"
    assert result.message == "Path exists but is not a directory."


def test_check_directory_writable_passes_for_temp_directory(tmp_path: Path):
    result = check_directory_writable("Writable directory", tmp_path)

    assert result.status == "pass"
    assert result.message == "Directory is writable."
    assert not (tmp_path / ".studio_write_probe").exists()


def test_check_directory_writable_fails_for_missing_directory(tmp_path: Path):
    missing = tmp_path / "missing"

    result = check_directory_writable("Missing writable directory", missing)

    assert result.status == "fail"
    assert "writability could not be verified" in result.message


def test_check_parent_directory_writable_passes_when_parent_exists(tmp_path: Path):
    log_path = tmp_path / "logs" / "operator_activity.jsonl"
    log_path.parent.mkdir(parents=True)

    result = check_parent_directory_writable(
        "Activity log directory",
        log_path,
    )

    assert result.status == "pass"
    assert result.path == log_path.parent.as_posix()


def test_check_parent_directory_writable_fails_when_parent_missing(tmp_path: Path):
    log_path = tmp_path / "missing" / "operator_activity.jsonl"

    result = check_parent_directory_writable(
        "Activity log directory",
        log_path,
    )

    assert result.status == "fail"
    assert result.message == "Parent directory does not exist."


def test_check_optional_file_reference_passes_for_existing_file(tmp_path: Path):
    file_path = tmp_path / "audit.json"
    file_path.write_text("{}", encoding="utf-8")

    result = check_optional_file_reference("Audit file", file_path)

    assert result.status == "pass"
    assert result.message == "Configured file exists."


def test_check_optional_file_reference_warns_for_missing_file(tmp_path: Path):
    file_path = tmp_path / "missing.json"

    result = check_optional_file_reference("Missing optional file", file_path)

    assert result.status == "warning"
    assert result.is_warning is True
    assert result.message == "Configured file does not exist yet."


def test_run_studio_health_checks_reports_ready_for_valid_config(tmp_path: Path):
    inquiry_dir = tmp_path / "data" / "inquiries"
    requests_dir = tmp_path / "data" / "run_requests"
    runs_dir = tmp_path / "logs" / "runs"
    activity_log = tmp_path / "logs" / "operator_activity.jsonl"

    inquiry_dir.mkdir(parents=True)
    requests_dir.mkdir(parents=True)
    runs_dir.mkdir(parents=True)
    activity_log.parent.mkdir(parents=True, exist_ok=True)

    config = StudioConfig(
        inquiry_library_dir=inquiry_dir.as_posix(),
        run_requests_dir=requests_dir.as_posix(),
        runs_dir=runs_dir.as_posix(),
        operator_activity_log_path=activity_log.as_posix(),
        default_progress_log_path=None,
        default_audit_report_path=None,
    )

    report = run_studio_health_checks(config)

    assert report.is_ready is True
    assert report.failing_count == 0
    assert report.passing_count == 6


def test_run_studio_health_checks_fails_for_missing_required_dirs(tmp_path: Path):
    config = StudioConfig(
        inquiry_library_dir=(tmp_path / "missing_inquiries").as_posix(),
        run_requests_dir=(tmp_path / "missing_requests").as_posix(),
        runs_dir=(tmp_path / "missing_runs").as_posix(),
        operator_activity_log_path=(
            tmp_path / "missing_logs" / "operator_activity.jsonl"
        ).as_posix(),
    )

    report = run_studio_health_checks(config)

    assert report.is_ready is False
    assert report.failing_count >= 4
