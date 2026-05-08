from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuditAxisSummary:
    axis: str
    status: str
    score: str | None
    issues: list[str]

    @property
    def is_passing(self) -> bool:
        return self.status == "pass"

    @property
    def is_warning(self) -> bool:
        return self.status == "warning"

    @property
    def is_failing(self) -> bool:
        return self.status == "fail"


@dataclass(frozen=True)
class AuditSummary:
    publishable: bool
    axes: list[AuditAxisSummary]
    blocking_issues: list[str]
    warning_issues: list[str]

    @property
    def status_label(self) -> str:
        if self.publishable:
            return "publishable"

        return "not_publishable"


__all__ = ["AuditAxisSummary", "AuditSummary"]
