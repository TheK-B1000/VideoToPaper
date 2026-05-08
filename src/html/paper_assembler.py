"""
HTML paper assembler for the Inquiry Engine.

This module assembles a self-contained interactive HTML paper.
Week 9 adds interactive assets:
- JSON island
- inline component CSS
- inline vanilla JavaScript
- noscript fallback
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.html.interactive_components import (
    render_interactive_assets,
    render_no_script_notice,
)


@dataclass(frozen=True)
class PaperSection:
    """
    A semantic section of the generated Inquiry Engine paper.
    """

    section_id: str
    title: str
    body_html: str


@dataclass(frozen=True)
class PaperDocument:
    """
    Fully assembled paper metadata and sections.
    """

    title: str
    abstract: str
    source_title: str
    source_url: str
    speaker_name: str
    sections: Sequence[PaperSection] = field(default_factory=list)
    interactive_payload: Mapping[str, Any] = field(default_factory=dict)


def assemble_html_paper(document: PaperDocument) -> str:
    """
    Assemble a complete, self-contained HTML paper.

    The generated file intentionally avoids external CSS or JS references.
    YouTube embeds may still require internet access because they point back
    to the original source video.
    """

    title = html.escape(document.title)
    abstract = html.escape(document.abstract)
    source_title = html.escape(document.source_title)
    source_url = html.escape(document.source_url, quote=True)
    speaker_name = html.escape(document.speaker_name)

    assets = render_interactive_assets(document.interactive_payload)
    sections_html = "\n".join(render_section(section) for section in document.sections)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  {render_base_css()}
  {assets.css}
</head>
<body>
  {assets.json_island}

  <article class="inquiry-paper">
    <header class="paper-header">
      <p class="eyebrow">The Inquiry Engine</p>
      <h1>{title}</h1>
      <p class="paper-abstract">{abstract}</p>

      <section class="source-attribution" aria-label="Source attribution">
        <h2>Source</h2>
        <p>
          Speaker: <strong>{speaker_name}</strong><br>
          Video:
          <a href="{source_url}" target="_blank" rel="noopener noreferrer">
            {source_title}
          </a>
        </p>
      </section>

      <p class="inquiry-js-status" data-inquiry-js-status>
        Interactive controls unavailable until JavaScript loads.
      </p>

      {render_no_script_notice()}
    </header>

    {sections_html}
  </article>

  {assets.js}
</body>
</html>
"""


def render_section(section: PaperSection) -> str:
    """
    Render one semantic paper section.

    body_html is assumed to come from trusted internal renderers.
    """

    section_id = html.escape(section.section_id, quote=True)
    title = html.escape(section.title)

    return f"""
<section id="{section_id}" class="paper-section">
  <h2>{title}</h2>
  {section.body_html}
</section>
""".strip()


def write_html_paper(document: PaperDocument, output_path: str | Path) -> Path:
    """
    Assemble and write the HTML paper to disk.
    """

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(assemble_html_paper(document), encoding="utf-8")
    return path


def render_base_css() -> str:
    """
    Base paper CSS.

    Week 9 component CSS is injected separately by render_interactive_assets().
    """

    return """
<style>
  :root {
    color-scheme: light;
    font-family:
      Inter,
      ui-sans-serif,
      system-ui,
      -apple-system,
      BlinkMacSystemFont,
      "Segoe UI",
      sans-serif;
    line-height: 1.6;
    color: #111111;
    background: #f4f4f1;
  }

  body {
    margin: 0;
    padding: 0;
  }

  a {
    color: #111111;
  }

  .inquiry-paper {
    max-width: 980px;
    margin: 0 auto;
    padding: 2rem;
  }

  .paper-header,
  .paper-section {
    background: #ffffff;
    border: 1px solid rgba(20, 20, 20, 0.12);
    border-radius: 1rem;
    padding: 1.5rem;
    margin: 1.25rem 0;
  }

  .eyebrow {
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.8rem;
    color: #444444;
    margin: 0 0 0.5rem;
  }

  h1,
  h2,
  h3 {
    line-height: 1.2;
  }

  h1 {
    margin: 0;
    font-size: clamp(2rem, 5vw, 3.5rem);
  }

  h2 {
    margin-top: 0;
  }

  .paper-abstract {
    font-size: 1.08rem;
    max-width: 760px;
  }

  .source-attribution {
    border-top: 1px solid rgba(20, 20, 20, 0.12);
    margin-top: 1.5rem;
    padding-top: 1rem;
  }

  iframe {
    width: 100%;
    aspect-ratio: 16 / 9;
    border: 0;
    border-radius: 0.75rem;
    background: #111111;
  }
</style>
""".strip()
