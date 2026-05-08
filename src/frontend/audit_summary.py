from __future__ import annotations

from dataclasses import dataclass
from typing import Any


AUDIT_AXES = [
    "steelman_accuracy",
    "evidence_balance",
    "citation_integrity",
    "clip_anchor_accuracy",
]


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


def summarize_audit_report(report: dict[str, Any]) -> AuditSummary:
    publishable = bool(report.get("publishable", False))

    axes = [
        summarize_audit_axis(axis_name, report.get(axis_name, {}))
        for axis_name in AUDIT_AXES
    ]

    blocking_issues: list[str] = []
    warning_issues: list[str] = []

    for axis in axes:
        if axis.is_failing:
            blocking_issues.extend(
                f"{axis.axis}: {issue}" for issue in axis.issues
            )

        if axis.is_warning:
            warning_issues.extend(
                f"{axis.axis}: {issue}" for issue in axis.issues
            )

    return AuditSummary(
        publishable=publishable,
        axes=axes,
        blocking_issues=blocking_issues,
        warning_issues=warning_issues,
    )


def summarize_audit_axis(
    axis_name: str,
    axis_report: Any,
) -> AuditAxisSummary:
    if not isinstance(axis_report, dict):
        return AuditAxisSummary(
            axis=axis_name,
            status="fail",
            score=None,
            issues=["Axis report is missing or malformed."],
        )

    issues = collect_axis_issues(axis_name, axis_report)
    score = infer_axis_score(axis_name, axis_report)
    status = infer_axis_status(axis_name, axis_report, issues)

    return AuditAxisSummary(
        axis=axis_name,
        status=status,
        score=score,
        issues=issues,
    )


def collect_axis_issues(
    axis_name: str,
    axis_report: dict[str, Any],
) -> list[str]:
    if axis_name == "steelman_accuracy":
        return _steelman_issues(axis_report)

    if axis_name == "evidence_balance":
        return _evidence_balance_issues(axis_report)

    if axis_name == "citation_integrity":
        return _citation_integrity_issues(axis_report)

    if axis_name == "clip_anchor_accuracy":
        return _clip_anchor_issues(axis_report)

    return []


def infer_axis_score(
    axis_name: str,
    axis_report: dict[str, Any],
) -> str | None:
    if axis_name == "steelman_accuracy":
        return _first_present_string(
            axis_report,
            [
                "verbatim_anchored_assertions",
                "qualifications_preserved",
            ],
        )

    if axis_name == "evidence_balance":
        return _first_present_string(
            axis_report,
            [
                "claims_with_balanced_retrieval",
                "cherry_picking_score",
            ],
        )

    if axis_name == "citation_integrity":
        return _first_present_string(
            axis_report,
            [
                "references_resolved",
                "fabricated_references",
            ],
        )

    if axis_name == "clip_anchor_accuracy":
        return _first_present_string(
            axis_report,
            [
                "clips_within_tolerance",
                "tolerance_seconds",
            ],
        )

    return None


def infer_axis_status(
    axis_name: str,
    axis_report: dict[str, Any],
    issues: list[str],
) -> str:
    if _has_blocking_failure(axis_name, axis_report):
        return "fail"

    if issues:
        return "warning"

    return "pass"


def _steelman_issues(axis_report: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if axis_report.get("hedge_drift_detected") is True:
        issues.append("Hedge drift was detected.")

    if _percent_value(axis_report.get("verbatim_anchored_assertions")) < 1.0:
        issues.append("Not all speaker-perspective assertions are verbatim anchored.")

    if _percent_value(axis_report.get("qualifications_preserved")) < 1.0:
        issues.append("Not all qualifications were preserved.")

    return issues


def _evidence_balance_issues(axis_report: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    cherry_picking_score = str(axis_report.get("cherry_picking_score", "")).lower()

    if cherry_picking_score in {"high", "severe"}:
        issues.append("Cherry-picking risk is high.")

    false_consensus_count = int(axis_report.get("false_consensus_count", 0))

    if false_consensus_count > 0:
        issues.append(f"{false_consensus_count} false consensus issue(s) detected.")

    if _percent_value(axis_report.get("claims_with_balanced_retrieval")) < 0.8:
        issues.append("Balanced retrieval coverage is below 80%.")

    return issues


def _citation_integrity_issues(axis_report: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    fabricated_references = int(axis_report.get("fabricated_references", 0))

    if fabricated_references > 0:
        issues.append(f"{fabricated_references} fabricated reference(s) detected.")

    if _percent_value(axis_report.get("references_resolved")) < 1.0:
        issues.append("Not all references resolved successfully.")

    return issues


def _clip_anchor_issues(axis_report: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    drift_detected = axis_report.get("drift_detected", [])

    if isinstance(drift_detected, list) and drift_detected:
        issues.append(f"{len(drift_detected)} clip drift issue(s) detected.")

    if _percent_value(axis_report.get("clips_within_tolerance")) < 1.0:
        issues.append("Not all clips are within timestamp tolerance.")

    return issues


def _has_blocking_failure(
    axis_name: str,
    axis_report: dict[str, Any],
) -> bool:
    if axis_name == "citation_integrity":
        return int(axis_report.get("fabricated_references", 0)) > 0

    if axis_name == "clip_anchor_accuracy":
        drift_detected = axis_report.get("drift_detected", [])
        return isinstance(drift_detected, list) and len(drift_detected) > 0

    if axis_name == "steelman_accuracy":
        return axis_report.get("hedge_drift_detected") is True

    if axis_name == "evidence_balance":
        return str(axis_report.get("cherry_picking_score", "")).lower() in {
            "high",
            "severe",
        }

    return False


def _first_present_string(
    data: dict[str, Any],
    keys: list[str],
) -> str | None:
    for key in keys:
        if key in data:
            return str(data[key])

    return None


def _percent_value(value: Any) -> float:
    if value is None:
        return 1.0

    if isinstance(value, int | float):
        numeric = float(value)
        return numeric / 100.0 if numeric > 1 else numeric

    text = str(value).strip()

    if text.endswith("%"):
        try:
            return float(text[:-1]) / 100.0
        except ValueError:
            return 1.0

    try:
        numeric = float(text)
        return numeric / 100.0 if numeric > 1 else numeric
    except ValueError:
        return 1.0