import json
import re

import pytest

from src.html.interactive_components import (
    InteractiveAssets,
    render_interactive_assets,
    render_interactive_css,
    render_interactive_js,
    render_json_island,
    render_no_script_notice,
)


def test_render_json_island_embeds_valid_json_payload():
    payload = {
        "claims": [
            {
                "claim_id": "claim_001",
                "quote": "Multi-agent systems become non-stationary.",
            }
        ]
    }

    html = render_json_island(payload)

    assert 'id="inquiry-interactive-data"' in html
    assert 'type="application/json"' in html

    match = re.search(
        r'<script id="inquiry-interactive-data" type="application/json">(.*?)</script>',
        html,
    )

    assert match is not None

    parsed = json.loads(match.group(1))
    assert parsed == payload


def test_render_json_island_escapes_closing_script_tag():
    payload = {"dangerous": "</script><script>alert('bad')</script>"}

    html = render_json_island(payload)

    assert "</script><script>" not in html
    assert "<\\/script>" in html


def test_render_json_island_rejects_non_mapping_payload():
    with pytest.raises(TypeError):
        render_json_island(["not", "a", "mapping"])


def test_render_json_island_rejects_empty_element_id():
    with pytest.raises(ValueError):
        render_json_island({}, element_id="   ")


def test_interactive_css_contains_component_classes():
    css = render_interactive_css()

    assert ".claim-card" in css
    assert ".evidence-panel" in css
    assert ".reading-item" in css
    assert ":focus-visible" in css
    assert "<style>" in css
    assert "</style>" in css


def test_interactive_js_contains_expected_component_hydrators():
    js = render_interactive_js()

    assert "hydrateClaimCards" in js
    assert "hydrateEvidencePanels" in js
    assert "hydrateReadingLists" in js
    assert "aria-expanded" in js
    assert "aria-pressed" in js
    assert "DOMContentLoaded" in js


def test_interactive_js_has_no_external_script_reference():
    js = render_interactive_js()

    assert 'src="' not in js
    assert "import " not in js
    assert "fetch(" not in js


def test_render_interactive_assets_returns_all_inline_assets():
    payload = {"claims": [], "evidence": [], "reading": []}

    assets = render_interactive_assets(payload)

    assert isinstance(assets, InteractiveAssets)
    assert assets.json_island.startswith("<script")
    assert assets.css.startswith("<style")
    assert assets.js.startswith("<script")
    assert "inquiry-interactive-data" in assets.json_island


def test_no_script_notice_supports_progressive_enhancement():
    notice = render_no_script_notice()

    assert notice.startswith("<noscript>")
    assert "paper remains readable" in notice
    assert notice.endswith("</noscript>")
