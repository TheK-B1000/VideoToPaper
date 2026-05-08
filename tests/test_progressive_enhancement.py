import re

from src.html.paper_assembler import assemble_html_paper
from tools.generate_sample_paper import build_sample_document


def _sample_html() -> str:
    return assemble_html_paper(build_sample_document())


def _article_markup(html: str) -> str:
    start = html.index('<article class="inquiry-paper">')
    end = html.rindex("</article>") + len("</article>")

    return html[start:end]


def _without_script_blocks(html: str) -> str:
    return re.sub(
        r"<script\b[^>]*>.*?</script>",
        "",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )


def test_generated_paper_keeps_core_text_readable_without_javascript() -> None:
    no_script_html = _without_script_blocks(_sample_html())

    assert "Sample Interactive Inquiry Paper" in no_script_html
    assert "The Inquiry Engine" in no_script_html
    assert "Non-stationarity in multi-agent reinforcement learning" in no_script_html
    assert "non-stationarity makes single-agent algorithms fundamentally unsuited" in no_script_html
    assert "The claim is directionally supported" in no_script_html
    assert "Generated query about non-stationarity in multi-agent RL." in no_script_html
    assert "Multi-Agent Reinforcement Learning: A Selective Overview" in no_script_html
    assert "Multi-agent settings can violate stationarity assumptions" in no_script_html


def test_generated_article_does_not_hide_essential_content_before_hydration() -> None:
    article = _article_markup(_sample_html())

    assert " hidden" not in article
    assert "hidden=" not in article
    assert "<template" not in article
    assert "display: none" not in article


def test_claim_card_is_readable_before_javascript_adds_disclosure_state() -> None:
    article = _article_markup(_sample_html())

    assert 'data-component="claim-card"' in article
    assert "Speaker quote" in article
    assert "Adjudication" in article
    assert "Retrieval trail" in article
    assert "Expand trail" in article
    assert "Show adjudication" in article
    assert "No retrieval trail is available" not in article


def test_evidence_and_reading_components_render_visible_fallback_content() -> None:
    article = _article_markup(_sample_html())

    assert 'data-component="evidence-panel"' in article
    assert 'data-component="reading-list"' in article
    assert "Evidence for claim_0042" in article
    assert "Show key finding" in article
    assert "Selective MARL Overview" in article
    assert "Open access" in article


def test_noscript_notice_explicitly_preserves_readability_contract() -> None:
    html = _sample_html()

    assert "<noscript>" in html
    assert "The paper remains readable" in html
    assert "claim expansion" in html
    assert "evidence filters" in html
    assert "reading-list sorting" in html


def test_progressive_enhancement_keeps_local_file_safe_when_scripts_are_removed() -> None:
    no_script_html = _without_script_blocks(_sample_html())

    assert '<link rel="stylesheet"' not in no_script_html
    assert '<script src="' not in no_script_html
    assert "fetch(" not in no_script_html
    assert 'href="https://example.org/marl-overview"' in no_script_html
    assert 'src="https://www.youtube-nocookie.com/embed/ABC123?start=252&amp;end=263&amp;rel=0"' in no_script_html
