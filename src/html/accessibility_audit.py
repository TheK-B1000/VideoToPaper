"""
Accessibility audit helpers for interactive HTML papers.

Purpose:
- Catch missing ARIA hooks.
- Catch buttons without readable labels.
- Catch filters without labels.
- Catch broken progressive-enhancement assumptions.

This is intentionally lightweight and static. Browser-level tests still verify
actual behavior.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AccessibilityIssue:
    code: str
    message: str


@dataclass(frozen=True)
class AccessibilityAuditReport:
    checked_path: str | None
    passed: bool
    issues: list[AccessibilityIssue] = field(default_factory=list)

    @property
    def issue_count(self) -> int:
        return len(self.issues)


REQUIRED_ARIA_MARKERS = [
    "aria-controls",
    "aria-expanded",
    "aria-pressed",
]

REQUIRED_KEYBOARD_SAFE_ELEMENTS = [
    'data-action="toggle-claim"',
    'data-action="toggle-claim-mode"',
    'data-action="toggle-source-detail"',
]

REQUIRED_LABELLED_FILTERS = [
    'data-filter="evidence-stance"',
    'data-filter="evidence-tier"',
    'data-filter="reading-topic"',
    'data-filter="reading-tier"',
    'data-sort="reading-accessibility"',
]


def audit_accessibility_from_text(
    html_text: str,
    *,
    checked_path: str | None = None,
) -> AccessibilityAuditReport:
    """
    Run a lightweight static accessibility audit against generated HTML text.
    """

    issues: list[AccessibilityIssue] = []

    if not html_text.strip():
        issues.append(
            AccessibilityIssue(
                code="empty_html",
                message="Generated HTML is empty.",
            )
        )

    for marker in REQUIRED_ARIA_MARKERS:
        if marker not in html_text:
            issues.append(
                AccessibilityIssue(
                    code="missing_aria_marker",
                    message=f"Missing required ARIA marker: {marker}",
                )
            )

    for marker in REQUIRED_KEYBOARD_SAFE_ELEMENTS:
        if marker not in html_text:
            issues.append(
                AccessibilityIssue(
                    code="missing_keyboard_safe_control",
                    message=f"Missing keyboard-safe button control: {marker}",
                )
            )

    for marker in REQUIRED_LABELLED_FILTERS:
        if marker not in html_text:
            issues.append(
                AccessibilityIssue(
                    code="missing_filter_control",
                    message=f"Missing required filter control: {marker}",
                )
            )

    _check_buttons_have_text(html_text, issues)
    _check_selects_are_wrapped_by_labels(html_text, issues)
    _check_iframes_have_titles(html_text, issues)
    _check_noscript_exists(html_text, issues)

    return AccessibilityAuditReport(
        checked_path=checked_path,
        passed=len(issues) == 0,
        issues=issues,
    )


def audit_accessibility_file(html_path: str | Path) -> AccessibilityAuditReport:
    """
    Run the accessibility audit against a generated HTML file.
    """

    path = Path(html_path)

    if not path.exists():
        return AccessibilityAuditReport(
            checked_path=str(path),
            passed=False,
            issues=[
                AccessibilityIssue(
                    code="file_not_found",
                    message=f"HTML file does not exist: {path}",
                )
            ],
        )

    return audit_accessibility_from_text(
        path.read_text(encoding="utf-8"),
        checked_path=str(path),
    )


def format_accessibility_report(report: AccessibilityAuditReport) -> str:
    """
    Format an accessibility audit report for CLI output.
    """

    target = report.checked_path or "<html text>"

    if report.passed:
        return f"Accessibility audit passed: {target}"

    lines = [
        f"Accessibility audit failed: {target}",
        f"Issues found: {report.issue_count}",
    ]

    for issue in report.issues:
        lines.append(f"- {issue.code}: {issue.message}")

    return "\n".join(lines)


def _check_buttons_have_text(
    html_text: str,
    issues: list[AccessibilityIssue],
) -> None:
    """
    Static check that buttons are not empty.

    This catches the common mistake where icon-only buttons are rendered without
    aria-label or readable text.
    """

    button_pattern = re.compile(
        r"<button\b(?P<attrs>[^>]*)>(?P<body>.*?)</button>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    for match in button_pattern.finditer(html_text):
        attrs = match.group("attrs")
        body = _strip_tags(match.group("body")).strip()

        has_aria_label = "aria-label=" in attrs
        has_text = bool(body)

        if not has_text and not has_aria_label:
            issues.append(
                AccessibilityIssue(
                    code="button_missing_accessible_name",
                    message="A button is missing visible text or aria-label.",
                )
            )


def _check_selects_are_wrapped_by_labels(
    html_text: str,
    issues: list[AccessibilityIssue],
) -> None:
    """
    Static check that select controls appear inside label elements.

    This intentionally matches the renderer pattern we use for Week 9.
    """

    select_pattern = re.compile(
        r"<select\b(?P<select_attrs>[^>]*)>",
        flags=re.IGNORECASE,
    )

    for match in select_pattern.finditer(html_text):
        start = max(0, match.start() - 160)
        context = html_text[start : match.start()]

        if "<label" not in context:
            issues.append(
                AccessibilityIssue(
                    code="select_missing_label",
                    message="A select control appears to be missing a nearby label.",
                )
            )


def _check_iframes_have_titles(
    html_text: str,
    issues: list[AccessibilityIssue],
) -> None:
    """
    Static check that every iframe has a title attribute.
    """

    iframe_pattern = re.compile(
        r"<iframe\b(?P<attrs>[^>]*)>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    for match in iframe_pattern.finditer(html_text):
        attrs = match.group("attrs")

        if "title=" not in attrs:
            issues.append(
                AccessibilityIssue(
                    code="iframe_missing_title",
                    message="An iframe is missing a title attribute.",
                )
            )


def _check_noscript_exists(
    html_text: str,
    issues: list[AccessibilityIssue],
) -> None:
    """
    Static check for progressive enhancement notice.
    """

    if "<noscript>" not in html_text:
        issues.append(
            AccessibilityIssue(
                code="missing_noscript_notice",
                message="Generated HTML is missing a noscript fallback notice.",
            )
        )


def _strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value)