from pathlib import Path

from src.html.html_integrity import check_html_integrity_from_text
from src.html.paper_assembler import assemble_html_paper
from tools.generate_sample_paper import build_sample_document, main


def test_build_sample_document_assembles_valid_html() -> None:
    html = assemble_html_paper(build_sample_document())
    report = check_html_integrity_from_text(html)

    assert report.passed is True
    assert 'data-component="claim-card"' in html
    assert 'data-component="evidence-panel"' in html
    assert 'data-component="reading-list"' in html


def test_generate_sample_paper_writes_default_output() -> None:
    output_path = Path("data/outputs/sample_interactive_paper.html")
    if output_path.exists():
        output_path.unlink()

    result = main()

    assert result == 0
    assert output_path.exists()

    report = check_html_integrity_from_text(output_path.read_text(encoding="utf-8"))

    assert report.passed is True
