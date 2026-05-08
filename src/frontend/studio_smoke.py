from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.frontend.local_runner import launch_local_run
from src.frontend.operator_activity import record_activity
from src.frontend.queue_status import mark_request_queued
from src.frontend.run_progress import load_run_progress
from src.frontend.run_queue import load_queued_run_request
from src.frontend.run_request import create_inquiry_run_request, save_run_request
from src.frontend.studio_config import StudioConfig, ensure_studio_directories
from src.frontend.studio_health import run_studio_health_checks
from src.frontend.studio_readme import write_studio_readme


@dataclass(frozen=True)
class StudioSmokeResult:
    passed: bool
    request_path: str | None
    progress_path: str | None
    readme_path: str | None
    activity_log_path: str | None
    checks: list[str]
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "request_path": self.request_path,
            "progress_path": self.progress_path,
            "readme_path": self.readme_path,
            "activity_log_path": self.activity_log_path,
            "checks": self.checks,
            "errors": self.errors,
        }


def run_studio_smoke_test(
    *,
    config: StudioConfig,
    youtube_url: str = "https://www.youtube.com/watch?v=ABC123xyz_9",
) -> StudioSmokeResult:
    from src.frontend.inquiry_studio import build_run_parameters

    checks: list[str] = []
    errors: list[str] = []

    request_path: Path | None = None
    progress_path: str | None = None
    readme_path: Path | None = None

    try:
        ensure_studio_directories(config)
        checks.append("studio_directories_ready")
    except Exception as error:
        errors.append(f"Failed to ensure studio directories: {error}")

    try:
        health = run_studio_health_checks(config)

        if not health.is_ready:
            errors.append("Studio health check failed.")

        checks.append("studio_health_checked")
    except Exception as error:
        errors.append(f"Failed to run health checks: {error}")

    try:
        params = build_run_parameters(
            youtube_url=youtube_url,
            claim_type_filter=["empirical_technical"],
            retrieval_depth=2,
            source_tiers=[1],
        )

        checks.append(f"run_parameters_validated:{params.video_id}")
    except Exception as error:
        errors.append(f"Failed to validate run parameters: {error}")

    try:
        run_request = create_inquiry_run_request(
            youtube_url=youtube_url,
            claim_type_filter=["empirical_technical"],
            retrieval_depth=2,
            source_tiers=[1],
            stages=["source_ingestion", "claim_inventory", "evaluation"],
            metadata={"created_from": "studio_smoke_test"},
        )

        request_path = save_run_request(
            run_request,
            config.run_requests_dir,
        )

        checks.append("run_request_created")
    except Exception as error:
        errors.append(f"Failed to create run request: {error}")
        run_request = None

    try:
        if request_path is None:
            raise ValueError("No request path exists.")

        queued = load_queued_run_request(request_path)
        launch = launch_local_run(queued, runs_dir=config.runs_dir)
        progress_path = launch.progress_path

        mark_request_queued(
            request_path,
            progress_path=launch.progress_path,
        )

        checks.append("local_run_launched")
        checks.append("queue_status_updated")
    except Exception as error:
        errors.append(f"Failed to launch local run: {error}")

    try:
        if progress_path is None:
            raise ValueError("No progress path exists.")

        progress = load_run_progress(progress_path)

        if progress is None:
            raise ValueError("Progress file did not load.")

        checks.append(f"progress_loaded:{progress.run_id}")
    except Exception as error:
        errors.append(f"Failed to load progress: {error}")

    try:
        activity = record_activity(
            activity_type="run_launched",
            message="Studio smoke test launched a local run.",
            request_id=run_request.request_id if run_request else None,
            artifact_path=progress_path,
            log_path=config.operator_activity_log_path,
            metadata={"source": "studio_smoke_test"},
        )

        checks.append(f"activity_recorded:{activity.activity_id}")
    except Exception as error:
        errors.append(f"Failed to record activity: {error}")

    try:
        readme_path = write_studio_readme(
            config,
            output_path=Path(config.runs_dir).parent / "inquiry_studio_smoke_readme.md",
        )

        checks.append("readme_generated")
    except Exception as error:
        errors.append(f"Failed to generate README: {error}")

    return StudioSmokeResult(
        passed=not errors,
        request_path=request_path.as_posix() if request_path else None,
        progress_path=progress_path,
        readme_path=readme_path.as_posix() if readme_path else None,
        activity_log_path=config.operator_activity_log_path,
        checks=checks,
        errors=errors,
    )