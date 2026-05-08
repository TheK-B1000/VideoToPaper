from pathlib import Path

from src.frontend.studio_config import StudioConfig
from src.frontend.studio_readme import (
    build_studio_readme,
    write_studio_readme,
)


def test_build_studio_readme_includes_configured_paths():
    config = StudioConfig(
        inquiry_library_dir="custom/inquiries",
        run_requests_dir="custom/run_requests",
        runs_dir="custom/runs",
        operator_activity_log_path="custom/logs/activity.jsonl",
        default_audit_report_path="custom/audit.json",
        default_progress_log_path="custom/progress.json",
        backend_base_url="http://127.0.0.1:8000",
        backend_timeout_seconds=10.0,
    )

    readme = build_studio_readme(config)

    assert readme.title == "Inquiry Studio README"
    assert "custom/inquiries" in readme.content
    assert "custom/run_requests" in readme.content
    assert "custom/runs" in readme.content
    assert "custom/logs/activity.jsonl" in readme.content
    assert "custom/audit.json" in readme.content
    assert "custom/progress.json" in readme.content


def test_build_studio_readme_describes_operator_workflow():
    config = StudioConfig(
        inquiry_library_dir="data/inquiries",
        run_requests_dir="data/run_requests",
        runs_dir="logs/runs",
        operator_activity_log_path="logs/operator_activity.jsonl",
    )

    readme = build_studio_readme(config)

    assert "Operator workflow" in readme.content
    assert "Submit a YouTube URL" in readme.content
    assert "Run Requests" in readme.content
    assert "Audit Inspector" in readme.content
    assert "Health Check" in readme.content


def test_build_studio_readme_handles_missing_optional_paths():
    config = StudioConfig(
        inquiry_library_dir="data/inquiries",
        run_requests_dir="data/run_requests",
        runs_dir="logs/runs",
        operator_activity_log_path="logs/operator_activity.jsonl",
        default_audit_report_path=None,
        default_progress_log_path=None,
    )

    readme = build_studio_readme(config)

    assert "not configured" in readme.content


def test_write_studio_readme_creates_file(tmp_path: Path):
    config = StudioConfig(
        inquiry_library_dir="data/inquiries",
        run_requests_dir="data/run_requests",
        runs_dir="logs/runs",
        operator_activity_log_path="logs/operator_activity.jsonl",
    )

    output_path = tmp_path / "docs" / "inquiry_studio.md"

    written_path = write_studio_readme(
        config,
        output_path=output_path,
    )

    assert written_path == output_path
    assert written_path.exists()

    content = written_path.read_text(encoding="utf-8")

    assert "# Inquiry Studio" in content
    assert "streamlit run src/frontend/inquiry_studio.py" in content
    assert "Completion standard" in content