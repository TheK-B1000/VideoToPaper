import json
import re
from pathlib import Path

from src.html.paper_assembler import (
    PaperDocument,
    PaperSection,
    assemble_html_paper,
    render_base_css,
    render_section,
    write_html_paper,
)


def _document() -> PaperDocument:
    return PaperDocument(
        title="Interactive Inquiry Paper",
        abstract="A self-contained paper with local interactive controls.",
        source_title="What Most People Get Wrong About Reinforcement Learning",
        source_url="https://www.youtube.com/watch?v=ABC123&feature=share",
        speaker_name="Dr. Jane Smith",
        sections=[
            PaperSection(
                section_id="claims",
                title="Claims Under Examination",
                body_html="""
                <article class="claim-card" data-component="claim-card">
                  <div data-claim-quote>Quote text.</div>
                </article>
                """,
            ),
            PaperSection(
                section_id="evidence",
                title="Evidence Review",
                body_html="""
                <div class="evidence-panel" data-component="evidence-panel">
                  Evidence text.
                </div>
                """,
            ),
        ],
        interactive_payload={
            "claims": [{"claim_id": "claim_0042", "quote": "Stationarity claim"}],
            "evidence": [{"evidence_id": "ev_001", "stance": "qualifies"}],
            "reading": [],
        },
    )


def test_assemble_html_paper_injects_week9_interactive_assets() -> None:
    html = assemble_html_paper(_document())

    assert '<script id="inquiry-interactive-data" type="application/json">' in html
    assert ".claim-card" in html
    assert ".evidence-panel" in html
    assert "hydrateClaimCards" in html
    assert "hydrateEvidencePanels" in html
    assert "hydrateReadingLists" in html
    assert "<noscript>" in html
    assert "Interactive controls unavailable until JavaScript loads." in html


def test_assemble_html_paper_embeds_valid_json_island_payload() -> None:
    html = assemble_html_paper(_document())

    match = re.search(
        r'<script id="inquiry-interactive-data" type="application/json">(.*?)</script>',
        html,
    )

    assert match is not None

    payload = json.loads(match.group(1))

    assert payload["claims"][0]["claim_id"] == "claim_0042"
    assert payload["evidence"][0]["evidence_id"] == "ev_001"


def test_assemble_html_paper_escapes_metadata_but_preserves_section_body_html() -> None:
    document = PaperDocument(
        title="<Unsafe Title>",
        abstract='Abstract with "quotes"',
        source_title="<Unsafe Source>",
        source_url='https://example.org/watch?v=1&x="bad"',
        speaker_name="<Speaker>",
        sections=[
            PaperSection(
                section_id='claims" onclick="bad',
                title="<Claims>",
                body_html="<p><strong>Trusted renderer HTML</strong></p>",
            )
        ],
        interactive_payload={},
    )

    output = assemble_html_paper(document)

    assert "&lt;Unsafe Title&gt;" in output
    assert "Abstract with &quot;quotes&quot;" in output
    assert "&lt;Unsafe Source&gt;" in output
    assert "https://example.org/watch?v=1&amp;x=&quot;bad&quot;" in output
    assert "&lt;Speaker&gt;" in output
    assert 'id="claims&quot; onclick=&quot;bad"' in output
    assert "<h2>&lt;Claims&gt;</h2>" in output
    assert "<p><strong>Trusted renderer HTML</strong></p>" in output


def test_assemble_html_paper_has_no_external_css_or_script_references() -> None:
    output = assemble_html_paper(_document())

    assert "<link" not in output
    assert 'script src="' not in output
    assert "fetch(" not in output
    assert "import " not in output


def test_render_section_escapes_section_id_and_title() -> None:
    section_html = render_section(
        PaperSection(
            section_id='claim" onmouseover="bad',
            title="<Claim Title>",
            body_html="<p>Body</p>",
        )
    )

    assert 'id="claim&quot; onmouseover=&quot;bad"' in section_html
    assert "<h2>&lt;Claim Title&gt;</h2>" in section_html
    assert "<p>Body</p>" in section_html


def test_render_base_css_returns_inline_style_block() -> None:
    css = render_base_css()

    assert css.startswith("<style>")
    assert css.endswith("</style>")
    assert ".inquiry-paper" in css
    assert ".paper-section" in css


def test_write_html_paper_writes_self_contained_file(tmp_path: Path) -> None:
    output_path = tmp_path / "paper.html"

    result = write_html_paper(_document(), output_path)

    assert result == output_path
    assert output_path.exists()

    html = output_path.read_text(encoding="utf-8")

    assert "<!doctype html>" in html
    assert "Interactive Inquiry Paper" in html
    assert "inquiry-interactive-data" in html
