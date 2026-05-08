from pathlib import Path

from src.html.html_integrity import (
    check_html_integrity_file,
    check_html_integrity_from_text,
    format_integrity_report,
)
from src.html.paper_assembler import assemble_html_paper
from tools.generate_sample_paper import build_sample_document


def _valid_sample_html() -> str:
    return assemble_html_paper(build_sample_document())


def test_valid_sample_html_passes_integrity_check():
    report = check_html_integrity_from_text(_valid_sample_html())

    assert report.passed is True
    assert report.issue_count == 0


def test_integrity_check_fails_empty_html():
    report = check_html_integrity_from_text("")

    assert report.passed is False
    assert any(issue.code == "empty_html" for issue in report.issues)


def test_integrity_check_fails_missing_required_markers():
    report = check_html_integrity_from_text(
        """
<!doctype html>
<html>
<body>
  <article class="inquiry-paper"></article>
</body>
</html>
"""
    )

    assert report.passed is False
    assert any(issue.code == "missing_required_marker" for issue in report.issues)


def test_integrity_check_fails_external_script_reference():
    html = _valid_sample_html().replace(
        "</body>",
        '<script src="https://example.com/app.js"></script></body>',
    )

    report = check_html_integrity_from_text(html)

    assert report.passed is False
    assert any(
        issue.code == "external_dependency_detected"
        for issue in report.issues
    )


def test_integrity_check_fails_external_stylesheet_reference():
    html = _valid_sample_html().replace(
        "</head>",
        '<link rel="stylesheet" href="https://example.com/app.css"></head>',
    )

    report = check_html_integrity_from_text(html)

    assert report.passed is False
    assert any(
        issue.code == "external_dependency_detected"
        for issue in report.issues
    )


def test_integrity_check_can_allow_missing_components():
    html = """
<!doctype html>
<html>
<body>
  <script id="inquiry-interactive-data" type="application/json">{}</script>
  <article class="inquiry-paper">
    <p data-inquiry-js-status>Interactive controls loading.</p>
    <iframe src="https://www.youtube-nocookie.com/embed/ABC123?start=1&end=2"></iframe>
    <noscript>Readable without JavaScript.</noscript>
  </article>
  <script>
    function hydrateClaimCards() {}
    function hydrateEvidencePanels() {}
    function hydrateReadingLists() {}
  </script>
</body>
</html>
"""

    report = check_html_integrity_from_text(
        html,
        require_components=False,
    )

    assert report.passed is True


def test_integrity_check_file_reports_missing_file(tmp_path: Path):
    missing_path = tmp_path / "missing.html"

    report = check_html_integrity_file(missing_path)

    assert report.passed is False
    assert report.checked_path == str(missing_path)
    assert report.issues[0].code == "file_not_found"


def test_integrity_check_file_reads_existing_file(tmp_path: Path):
    html_path = tmp_path / "paper.html"
    html_path.write_text(_valid_sample_html(), encoding="utf-8")

    report = check_html_integrity_file(html_path)

    assert report.passed is True
    assert report.checked_path == str(html_path)


def test_format_integrity_report_passed():
    report = check_html_integrity_from_text(_valid_sample_html())

    output = format_integrity_report(report)

    assert "HTML integrity check passed" in output


def test_format_integrity_report_failed():
    report = check_html_integrity_from_text("")

    output = format_integrity_report(report)

    assert "HTML integrity check failed" in output
    assert "Issues found:" in output
    assert "empty_html" in output
