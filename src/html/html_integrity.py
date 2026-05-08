"""
HTML integrity checks for generated Inquiry Engine papers.

Interactive paper purpose:
- Verify the generated paper is self-contained.
- Verify required interactive component hooks exist.
- Catch broken HTML assembly before manual browser testing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class HtmlIntegrityIssue:
    code: str
    message: str


@dataclass(frozen=True)
class HtmlIntegrityReport:
    checked_path: str | None
    passed: bool
    issues: list[HtmlIntegrityIssue] = field(default_factory=list)

    @property
    def issue_count(self) -> int:
        return len(self.issues)


REQUIRED_INTERACTIVE_MARKERS = [
    'id="inquiry-interactive-data"',
    "hydrateClaimCards",
    "hydrateEvidencePanels",
    "hydrateReadingLists",
    "<noscript>",
    "data-inquiry-js-status",
]

REQUIRED_COMPONENT_MARKERS = [
    'data-component="claim-card"',
    'data-component="evidence-panel"',
    'data-component="reading-list"',
]

FORBIDDEN_EXTERNAL_MARKERS = [
    '<script src="',
    "<script src='",
    '<link rel="stylesheet"',
    "<link rel='stylesheet'",
]


def check_html_integrity_from_text(
    html_text: str,
    *,
    checked_path: str | None = None,
    require_components: bool = True,
) -> HtmlIntegrityReport:
    """
    Check generated HTML text for interactive-paper integrity.

    This does not parse the DOM. It intentionally performs simple static checks
    that are fast, deterministic, and enough to catch common assembly mistakes.
    """

    issues: list[HtmlIntegrityIssue] = []

    if not html_text.strip():
        issues.append(
            HtmlIntegrityIssue(
                code="empty_html",
                message="Generated HTML is empty.",
            )
        )

    if "<!doctype html>" not in html_text.lower():
        issues.append(
            HtmlIntegrityIssue(
                code="missing_doctype",
                message="Generated HTML is missing <!doctype html>.",
            )
        )

    if "<article" not in html_text or "inquiry-paper" not in html_text:
        issues.append(
            HtmlIntegrityIssue(
                code="missing_inquiry_article",
                message="Generated HTML is missing the inquiry-paper article shell.",
            )
        )

    for marker in REQUIRED_INTERACTIVE_MARKERS:
        if marker not in html_text:
            issues.append(
                HtmlIntegrityIssue(
                    code="missing_required_marker",
                    message=f"Missing required interactive marker: {marker}",
                )
            )

    if require_components:
        for marker in REQUIRED_COMPONENT_MARKERS:
            if marker not in html_text:
                issues.append(
                    HtmlIntegrityIssue(
                        code="missing_component_marker",
                        message=f"Missing required component marker: {marker}",
                    )
                )

    for marker in FORBIDDEN_EXTERNAL_MARKERS:
        if marker in html_text:
            issues.append(
                HtmlIntegrityIssue(
                    code="external_dependency_detected",
                    message=(
                        "Generated HTML contains forbidden external dependency "
                        f"marker: {marker}"
                    ),
                )
            )

    if "https://www.youtube-nocookie.com/embed/" not in html_text:
        issues.append(
            HtmlIntegrityIssue(
                code="missing_privacy_embed",
                message=(
                    "Generated HTML does not contain a privacy-respecting "
                    "YouTube nocookie embed URL."
                ),
            )
        )

    return HtmlIntegrityReport(
        checked_path=checked_path,
        passed=len(issues) == 0,
        issues=issues,
    )


def check_html_integrity_file(
    html_path: str | Path,
    *,
    require_components: bool = True,
) -> HtmlIntegrityReport:
    """
    Check a generated HTML file on disk.
    """

    path = Path(html_path)

    if not path.exists():
        return HtmlIntegrityReport(
            checked_path=str(path),
            passed=False,
            issues=[
                HtmlIntegrityIssue(
                    code="file_not_found",
                    message=f"HTML file does not exist: {path}",
                )
            ],
        )

    html_text = path.read_text(encoding="utf-8")

    return check_html_integrity_from_text(
        html_text,
        checked_path=str(path),
        require_components=require_components,
    )


def format_integrity_report(report: HtmlIntegrityReport) -> str:
    """
    Format an integrity report for CLI output.
    """

    target = report.checked_path or "<html text>"

    if report.passed:
        return f"HTML integrity check passed: {target}"

    lines = [
        f"HTML integrity check failed: {target}",
        f"Issues found: {report.issue_count}",
    ]

    for issue in report.issues:
        lines.append(f"- {issue.code}: {issue.message}")

    return "\n".join(lines)
