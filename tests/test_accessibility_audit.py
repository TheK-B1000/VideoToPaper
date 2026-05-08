from pathlib import Path

from src.html.accessibility_audit import (
    audit_accessibility_file,
    audit_accessibility_from_text,
    format_accessibility_report,
)
from src.html.paper_assembler import assemble_html_paper
from tools.generate_sample_paper import build_sample_document


def _valid_sample_html() -> str:
    return assemble_html_paper(build_sample_document())


def test_valid_sample_passes_accessibility_audit():
    report = audit_accessibility_from_text(_valid_sample_html())

    assert report.passed is True
    assert report.issue_count == 0


def test_accessibility_audit_fails_empty_html():
    report = audit_accessibility_from_text("")

    assert report.passed is False
    assert any(issue.code == "empty_html" for issue in report.issues)


def test_accessibility_audit_fails_missing_aria_markers():
    html = _valid_sample_html().replace("aria-controls", "data-missing-controls")
    html = html.replace("aria-expanded", "data-missing-expanded")

    report = audit_accessibility_from_text(html)

    assert report.passed is False
    assert any(issue.code == "missing_aria_marker" for issue in report.issues)


def test_accessibility_audit_fails_empty_button_without_aria_label():
    html = _valid_sample_html().replace(
        "Expand trail",
        "",
        1,
    )

    report = audit_accessibility_from_text(html)

    assert report.passed is False
    assert any(
        issue.code == "button_missing_accessible_name"
        for issue in report.issues
    )


def test_accessibility_audit_allows_empty_button_with_aria_label():
    html = _valid_sample_html().replace(
        """<button
      type="button"
      class="claim-card__toggle"
      data-action="toggle-claim"
      aria-controls="claim-details-claim_001">
      Expand trail
    </button>""",
        """<button
      type="button"
      class="claim-card__toggle"
      data-action="toggle-claim"
      aria-controls="claim-details-claim_001"
      aria-label="Expand retrieval trail">
    </button>""",
    )

    report = audit_accessibility_from_text(html)

    assert not any(
        issue.code == "button_missing_accessible_name"
        for issue in report.issues
    )


def test_accessibility_audit_fails_iframe_without_title():
    html = _valid_sample_html().replace(
        'title="Anchor clip for Non-stationarity in multi-agent reinforcement learning"',
        "",
        1,
    )

    report = audit_accessibility_from_text(html)

    assert report.passed is False
    assert any(issue.code == "iframe_missing_title" for issue in report.issues)


def test_accessibility_audit_fails_missing_noscript():
    html = _valid_sample_html().replace("<noscript>", "<div>")
    html = html.replace("</noscript>", "</div>")

    report = audit_accessibility_from_text(html)

    assert report.passed is False
    assert any(issue.code == "missing_noscript_notice" for issue in report.issues)


def test_accessibility_audit_file_reports_missing_file(tmp_path: Path):
    missing_path = tmp_path / "missing.html"

    report = audit_accessibility_file(missing_path)

    assert report.passed is False
    assert report.checked_path == str(missing_path)
    assert report.issues[0].code == "file_not_found"


def test_accessibility_audit_file_reads_existing_file(tmp_path: Path):
    html_path = tmp_path / "paper.html"
    html_path.write_text(_valid_sample_html(), encoding="utf-8")

    report = audit_accessibility_file(html_path)

    assert report.passed is True
    assert report.checked_path == str(html_path)


def test_format_accessibility_report_passed():
    report = audit_accessibility_from_text(_valid_sample_html())

    output = format_accessibility_report(report)

    assert "Accessibility audit passed" in output


def test_format_accessibility_report_failed():
    report = audit_accessibility_from_text("")

    output = format_accessibility_report(report)

    assert "Accessibility audit failed" in output
    assert "Issues found:" in output
    assert "empty_html" in output