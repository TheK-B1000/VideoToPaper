from pathlib import Path

from src.frontend.operator_activity import read_activity_log
from src.frontend.run_progress import load_run_progress
from src.frontend.run_queue import load_queued_run_request
from src.frontend.studio_config import StudioConfig
from src.frontend.studio_smoke import run_studio_smoke_test


def test_run_studio_smoke_test_passes_with_temp_config(tmp_path: Path):
    config = StudioConfig(
        inquiry_library_dir=(tmp_path / "data" / "inquiries").as_posix(),
        run_requests_dir=(tmp_path / "data" / "run_requests").as_posix(),
        runs_dir=(tmp_path / "logs" / "runs").as_posix(),
        operator_activity_log_path=(
            tmp_path / "logs" / "operator_activity.jsonl"
        ).as_posix(),
        default_audit_report_path=None,
        default_progress_log_path=None,
    )

    result = run_studio_smoke_test(config=config)

    assert result.passed is True
    assert result.errors == []
    assert result.request_path is not None
    assert result.progress_path is not None
    assert result.readme_path is not None
    assert result.activity_log_path == config.operator_activity_log_path

    assert "studio_directories_ready" in result.checks
    assert "studio_health_checked" in result.checks
    assert "run_request_created" in result.checks
    assert "local_run_launched" in result.checks
    assert "queue_status_updated" in result.checks
    assert "readme_generated" in result.checks


def test_smoke_test_creates_queued_request_file(tmp_path: Path):
    config = StudioConfig(
        inquiry_library_dir=(tmp_path / "data" / "inquiries").as_posix(),
        run_requests_dir=(tmp_path / "data" / "run_requests").as_posix(),
        runs_dir=(tmp_path / "logs" / "runs").as_posix(),
        operator_activity_log_path=(
            tmp_path / "logs" / "operator_activity.jsonl"
        ).as_posix(),
    )

    result = run_studio_smoke_test(config=config)

    queued = load_queued_run_request(result.request_path)

    assert queued.status == "queued"
    assert queued.progress_path == result.progress_path
    assert queued.request.video_id == "ABC123xyz_9"
    assert queued.request.metadata["created_from"] == "studio_smoke_test"


def test_smoke_test_creates_loadable_progress_file(tmp_path: Path):
    config = StudioConfig(
        inquiry_library_dir=(tmp_path / "data" / "inquiries").as_posix(),
        run_requests_dir=(tmp_path / "data" / "run_requests").as_posix(),
        runs_dir=(tmp_path / "logs" / "runs").as_posix(),
        operator_activity_log_path=(
            tmp_path / "logs" / "operator_activity.jsonl"
        ).as_posix(),
    )

    result = run_studio_smoke_test(config=config)

    progress = load_run_progress(result.progress_path)

    assert progress is not None
    assert progress.status == "queued"
    assert progress.current_step == "source_ingestion"
    assert [step.name for step in progress.steps] == [
        "source_ingestion",
        "claim_inventory",
        "evaluation",
    ]


def test_smoke_test_records_operator_activity(tmp_path: Path):
    config = StudioConfig(
        inquiry_library_dir=(tmp_path / "data" / "inquiries").as_posix(),
        run_requests_dir=(tmp_path / "data" / "run_requests").as_posix(),
        runs_dir=(tmp_path / "logs" / "runs").as_posix(),
        operator_activity_log_path=(
            tmp_path / "logs" / "operator_activity.jsonl"
        ).as_posix(),
    )

    result = run_studio_smoke_test(config=config)

    activities = read_activity_log(config.operator_activity_log_path)

    assert result.passed is True
    assert len(activities) == 1
    assert activities[0].activity_type == "run_launched"
    assert activities[0].artifact_path == result.progress_path
    assert activities[0].metadata["source"] == "studio_smoke_test"


def test_smoke_test_generates_readme(tmp_path: Path):
    config = StudioConfig(
        inquiry_library_dir=(tmp_path / "data" / "inquiries").as_posix(),
        run_requests_dir=(tmp_path / "data" / "run_requests").as_posix(),
        runs_dir=(tmp_path / "logs" / "runs").as_posix(),
        operator_activity_log_path=(
            tmp_path / "logs" / "operator_activity.jsonl"
        ).as_posix(),
    )

    result = run_studio_smoke_test(config=config)

    readme_path = Path(result.readme_path)

    assert readme_path.exists()

    content = readme_path.read_text(encoding="utf-8")

    assert "# Inquiry Studio" in content
    assert "Operator workflow" in content