from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.frontend.studio_config import StudioConfig


@dataclass(frozen=True)
class HealthCheckResult:
    name: str
    status: str
    message: str
    path: str | None = None

    @property
    def is_passing(self) -> bool:
        return self.status == "pass"

    @property
    def is_warning(self) -> bool:
        return self.status == "warning"

    @property
    def is_failing(self) -> bool:
        return self.status == "fail"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "path": self.path,
        }


@dataclass(frozen=True)
class StudioHealthReport:
    checks: list[HealthCheckResult]

    @property
    def is_ready(self) -> bool:
        return not any(check.is_failing for check in self.checks)

    @property
    def passing_count(self) -> int:
        return sum(1 for check in self.checks if check.is_passing)

    @property
    def warning_count(self) -> int:
        return sum(1 for check in self.checks if check.is_warning)

    @property
    def failing_count(self) -> int:
        return sum(1 for check in self.checks if check.is_failing)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_ready": self.is_ready,
            "passing_count": self.passing_count,
            "warning_count": self.warning_count,
            "failing_count": self.failing_count,
            "checks": [check.to_dict() for check in self.checks],
        }


def run_studio_health_checks(config: StudioConfig) -> StudioHealthReport:
    checks = [
        check_directory_exists(
            "Inquiry library directory",
            config.inquiry_library_dir,
        ),
        check_directory_exists(
            "Run requests directory",
            config.run_requests_dir,
        ),
        check_directory_exists(
            "Runs directory",
            config.runs_dir,
        ),
        check_parent_directory_writable(
            "Operator activity log directory",
            config.operator_activity_log_path,
        ),
        check_directory_writable(
            "Run requests writable",
            config.run_requests_dir,
        ),
        check_directory_writable(
            "Runs directory writable",
            config.runs_dir,
        ),
    ]

    if config.default_progress_log_path:
        checks.append(
            check_optional_file_reference(
                "Default progress log",
                config.default_progress_log_path,
            )
        )

    if config.default_audit_report_path:
        checks.append(
            check_optional_file_reference(
                "Default audit report",
                config.default_audit_report_path,
            )
        )

    return StudioHealthReport(checks=checks)


def check_directory_exists(name: str, path: str | Path) -> HealthCheckResult:
    target = Path(path)

    if target.exists() and target.is_dir():
        return HealthCheckResult(
            name=name,
            status="pass",
            message="Directory exists.",
            path=target.as_posix(),
        )

    if target.exists() and not target.is_dir():
        return HealthCheckResult(
            name=name,
            status="fail",
            message="Path exists but is not a directory.",
            path=target.as_posix(),
        )

    return HealthCheckResult(
        name=name,
        status="fail",
        message="Directory does not exist.",
        path=target.as_posix(),
    )


def check_directory_writable(name: str, path: str | Path) -> HealthCheckResult:
    target = Path(path)

    if not target.exists() or not target.is_dir():
        return HealthCheckResult(
            name=name,
            status="fail",
            message="Directory is missing, so writability could not be verified.",
            path=target.as_posix(),
        )

    probe_path = target / ".studio_write_probe"

    try:
        probe_path.write_text("ok", encoding="utf-8")
        probe_path.unlink(missing_ok=True)

        return HealthCheckResult(
            name=name,
            status="pass",
            message="Directory is writable.",
            path=target.as_posix(),
        )
    except OSError as error:
        return HealthCheckResult(
            name=name,
            status="fail",
            message=f"Directory is not writable: {error}",
            path=target.as_posix(),
        )


def check_parent_directory_writable(
    name: str,
    file_path: str | Path,
) -> HealthCheckResult:
    target = Path(file_path)
    parent = target.parent

    if not parent.exists() or not parent.is_dir():
        return HealthCheckResult(
            name=name,
            status="fail",
            message="Parent directory does not exist.",
            path=parent.as_posix(),
        )

    return check_directory_writable(name, parent)


def check_optional_file_reference(name: str, path: str | Path) -> HealthCheckResult:
    target = Path(path)

    if target.exists() and target.is_file():
        return HealthCheckResult(
            name=name,
            status="pass",
            message="Configured file exists.",
            path=target.as_posix(),
        )

    if target.exists() and not target.is_file():
        return HealthCheckResult(
            name=name,
            status="warning",
            message="Configured path exists but is not a file.",
            path=target.as_posix(),
        )

    return HealthCheckResult(
        name=name,
        status="warning",
        message="Configured file does not exist yet.",
        path=target.as_posix(),
    )
