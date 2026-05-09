from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


@dataclass(frozen=True)
class PaperVideo:
    video_id: str
    title: str
    url: str
    embed_base_url: str
    speaker_name: str | None = None
    speaker_credentials: str | None = None


@dataclass(frozen=True)
class PaperClaim:
    claim_id: str
    verbatim_quote: str
    claim_type: str
    anchor_clip_start: float
    anchor_clip_end: float
    embed_url: str | None = None


@dataclass(frozen=True)
class PaperEvidenceRecord:
    evidence_id: str
    claim_id: str
    title: str
    source: str
    url: str
    tier: int
    stance: str
    identifier: str | None = None
    key_finding: str | None = None


@dataclass(frozen=True)
class PaperAdjudication:
    claim_id: str
    verdict: str
    confidence: str
    narrative: str
    supports: list[str] = field(default_factory=list)
    complicates: list[str] = field(default_factory=list)
    contradicts: list[str] = field(default_factory=list)
    qualifies: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PaperDocument:
    title: str
    abstract: str
    video: PaperVideo
    speaker_perspective: str
    claims: list[PaperClaim]
    evidence_records: list[PaperEvidenceRecord]
    adjudications: list[PaperAdjudication]
    limitations: list[str] = field(default_factory=list)
    further_reading: list[PaperEvidenceRecord] = field(default_factory=list)


class HtmlAssemblyError(ValueError):
    """Raised when the paper cannot be assembled safely."""


def build_clip_embed_url(embed_base_url: str, start: float, end: float) -> str:
    """
    Build a privacy-respecting YouTube embed URL with start/end timing.

    The assembler rounds timestamps to whole seconds because YouTube embed
    parameters use integer seconds.
    """
    if start < 0:
        raise HtmlAssemblyError("Clip start cannot be negative.")

    if end <= start:
        raise HtmlAssemblyError("Clip end must be greater than clip start.")

    parsed = urlparse(embed_base_url)
    query = dict(parse_qsl(parsed.query))

    query["start"] = str(int(round(start)))
    query["end"] = str(int(round(end)))
    query["rel"] = "0"

    return urlunparse(
        parsed._replace(
            query=urlencode(query),
        )
    )


def assemble_html_paper(document: PaperDocument) -> str:
    """
    Assemble a self-contained Inquiry Engine HTML paper.

    Hard rules enforced here:
    1. Every claim must have a valid inline clip embed.
    2. Every adjudication must reference an existing claim.
    3. Every evidence record must resolve to a real-looking URL.
    4. The Limitations section is always present.
    """
    _validate_document(document)

    evidence_by_claim = _group_evidence_by_claim(document.evidence_records)
    adjudication_by_claim = {
        adjudication.claim_id: adjudication for adjudication in document.adjudications
    }

    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(document.title)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="referrer" content="strict-origin-when-cross-origin">
  <style>
    {_base_css()}
  </style>
</head>
<body>
  <article class="inquiry-paper">
    {_render_header(document)}
    {_render_speaker_perspective(document)}
    {_render_claims(document.video, document.claims)}
    {_render_evidence_review(document.claims, evidence_by_claim, adjudication_by_claim)}
    {_render_agreement(document.claims, adjudication_by_claim)}
    {_render_complexity(document.claims, adjudication_by_claim)}
    {_render_limitations(document.limitations)}
    {_render_further_reading(document.further_reading or document.evidence_records)}
    {_render_references(document.evidence_records)}
  </article>
</body>
</html>
"""

    return body


def write_html_paper(document: PaperDocument, output_path: str | Path) -> Path:
    html = assemble_html_paper(document)

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")

    return target


def _validate_document(document: PaperDocument) -> None:
    if not document.title.strip():
        raise HtmlAssemblyError("Paper title is required.")

    if not document.abstract.strip():
        raise HtmlAssemblyError("Paper abstract is required.")

    if not document.video.embed_base_url.strip():
        raise HtmlAssemblyError("Video embed_base_url is required.")

    claim_ids = {claim.claim_id for claim in document.claims}

    if not claim_ids:
        raise HtmlAssemblyError("At least one claim is required to assemble a paper.")

    for claim in document.claims:
        if not claim.verbatim_quote.strip():
            raise HtmlAssemblyError(f"Claim {claim.claim_id} is missing a verbatim quote.")

        if claim.anchor_clip_end <= claim.anchor_clip_start:
            raise HtmlAssemblyError(
                f"Claim {claim.claim_id} has an invalid anchor clip range."
            )

    for evidence in document.evidence_records:
        if evidence.claim_id not in claim_ids:
            raise HtmlAssemblyError(
                f"Evidence {evidence.evidence_id} references unknown claim {evidence.claim_id}."
            )

        if not evidence.url.startswith(("http://", "https://")):
            raise HtmlAssemblyError(
                f"Evidence {evidence.evidence_id} must have a resolvable URL."
            )

        if evidence.tier < 1:
            raise HtmlAssemblyError(
                f"Evidence {evidence.evidence_id} must have a tier of 1 or higher."
            )

    for adjudication in document.adjudications:
        if adjudication.claim_id not in claim_ids:
            raise HtmlAssemblyError(
                f"Adjudication references unknown claim {adjudication.claim_id}."
            )


def _group_evidence_by_claim(
    evidence_records: list[PaperEvidenceRecord],
) -> dict[str, list[PaperEvidenceRecord]]:
    grouped: dict[str, list[PaperEvidenceRecord]] = {}

    for record in evidence_records:
        grouped.setdefault(record.claim_id, []).append(record)

    return grouped


def _render_header(document: PaperDocument) -> str:
    video = document.video
    speaker_parts = [video.speaker_name, video.speaker_credentials]
    speaker_line = " | ".join(part for part in speaker_parts if part)

    speaker_html = (
        f'<p class="speaker">Speaker: {escape(speaker_line)}</p>'
        if speaker_line
        else ""
    )

    return f"""
    <header class="paper-header">
      <p class="eyebrow">The Inquiry Engine</p>
      <h1>{escape(document.title)}</h1>
      <p class="abstract">{escape(document.abstract)}</p>
      <section class="source-attribution" aria-label="Source attribution">
        <h2>Source Attribution</h2>
        <p>Source video: <a href="{escape(video.url)}">{escape(video.title)}</a></p>
        {speaker_html}
      </section>
    </header>
    """


def _render_speaker_perspective(document: PaperDocument) -> str:
    return f"""
    <section id="perspective" class="paper-section">
      <h2>The Speaker's Perspective</h2>
      <p>{escape(document.speaker_perspective)}</p>
    </section>
    """


def _render_claims(video: PaperVideo, claims: list[PaperClaim]) -> str:
    cards = "\n".join(_render_claim_card(video, claim) for claim in claims)

    return f"""
    <section id="claims" class="paper-section">
      <h2>Claims Under Examination</h2>
      <div class="claim-grid">
        {cards}
      </div>
    </section>
    """


def _render_claim_card(video: PaperVideo, claim: PaperClaim) -> str:
    embed_url = claim.embed_url or build_clip_embed_url(
        video.embed_base_url,
        claim.anchor_clip_start,
        claim.anchor_clip_end,
    )

    return f"""
    <article class="claim-card" id="{escape(claim.claim_id)}">
      <h3>{escape(claim.claim_id)}</h3>
      <p class="claim-type">{escape(claim.claim_type)}</p>
      <blockquote>{escape(claim.verbatim_quote)}</blockquote>
      {_claim_embed_iframe(
          src=embed_url,
          title=f"Clip for {claim.claim_id}",
      )}
    </article>
    """


def _render_evidence_review(
    claims: list[PaperClaim],
    evidence_by_claim: dict[str, list[PaperEvidenceRecord]],
    adjudication_by_claim: dict[str, PaperAdjudication],
) -> str:
    blocks = []

    for claim in claims:
        evidence_records = evidence_by_claim.get(claim.claim_id, [])
        adjudication = adjudication_by_claim.get(claim.claim_id)

        evidence_items = "\n".join(
            _render_evidence_item(record) for record in evidence_records
        )

        narrative = (
            escape(adjudication.narrative)
            if adjudication
            else "No adjudication has been generated for this claim yet."
        )

        verdict = (
            f"""
            <p class="verdict">
              Verdict: <strong>{escape(adjudication.verdict)}</strong>
              &middot; Confidence: <strong>{escape(adjudication.confidence)}</strong>
            </p>
            """
            if adjudication
            else ""
        )

        blocks.append(
            f"""
            <article class="evidence-block">
              <h3>Evidence for {escape(claim.claim_id)}</h3>
              {verdict}
              <p>{narrative}</p>
              <details>
                <summary>Open retrieval trail</summary>
                <ul class="evidence-list">
                  {evidence_items or "<li>No retrieved evidence records.</li>"}
                </ul>
              </details>
            </article>
            """
        )

    return f"""
    <section id="evidence" class="paper-section">
      <h2>Evidence Review</h2>
      {"".join(blocks)}
    </section>
    """


def _render_agreement(
    claims: list[PaperClaim],
    adjudication_by_claim: dict[str, PaperAdjudication],
) -> str:
    supported = [
        claim
        for claim in claims
        if adjudication_by_claim.get(claim.claim_id)
        and "supported" in adjudication_by_claim[claim.claim_id].verdict
    ]

    if not supported:
        content = "<p>No clearly supported claims were identified in this pass.</p>"
    else:
        content = "<ul>" + "".join(
            f'<li><a href="#{escape(claim.claim_id)}">{escape(claim.claim_id)}</a>: '
            f"{escape(claim.verbatim_quote)}</li>"
            for claim in supported
        ) + "</ul>"

    return f"""
    <section id="agreement" class="paper-section">
      <h2>Points of Agreement</h2>
      {content}
    </section>
    """


def _render_complexity(
    claims: list[PaperClaim],
    adjudication_by_claim: dict[str, PaperAdjudication],
) -> str:
    complex_claims = [
        claim
        for claim in claims
        if adjudication_by_claim.get(claim.claim_id)
        and adjudication_by_claim[claim.claim_id].verdict
        in {
            "mixed",
            "contested",
            "partially_supported",
            "well_supported_with_qualifications",
        }
    ]

    if not complex_claims:
        content = "<p>No claims were marked as contested or complex in this pass.</p>"
    else:
        content = "<ul>" + "".join(
            f'<li><a href="#{escape(claim.claim_id)}">{escape(claim.claim_id)}</a>: '
            f"{escape(claim.verbatim_quote)}</li>"
            for claim in complex_claims
        ) + "</ul>"

    return f"""
    <section id="complexity" class="paper-section">
      <h2>Where the Picture Is More Complex</h2>
      {content}
    </section>
    """


def _render_limitations(limitations: list[str]) -> str:
    if limitations:
        content = "<ul>" + "".join(
            f"<li>{escape(item)}</li>" for item in limitations
        ) + "</ul>"
    else:
        content = (
            "<p>No additional limitations were detected by the assembler. "
            "This does not mean the inquiry is complete; it means no explicit "
            "limitations were supplied by the upstream pipeline.</p>"
        )

    return f"""
    <section id="limitations" class="paper-section">
      <h2>Open Questions & Limitations</h2>
      {content}
    </section>
    """


def _render_further_reading(records: list[PaperEvidenceRecord]) -> str:
    items = "\n".join(_render_evidence_item(record) for record in records)

    return f"""
    <section id="reading" class="paper-section">
      <h2>Further Reading</h2>
      <ul class="evidence-list">
        {items or "<li>No further reading records available.</li>"}
      </ul>
    </section>
    """


def _render_references(records: list[PaperEvidenceRecord]) -> str:
    items = "\n".join(
        f"""
        <li id="{escape(record.evidence_id)}">
          <a href="{escape(record.url)}">{escape(record.title)}</a>.
          {escape(record.source)}.
          Tier {record.tier}.
          Stance: {escape(record.stance)}.
          {f"Identifier: {escape(record.identifier)}." if record.identifier else ""}
        </li>
        """
        for record in records
    )

    return f"""
    <section id="references" class="paper-section">
      <h2>References</h2>
      <ol>
        {items or "<li>No references available.</li>"}
      </ol>
    </section>
    """


def _render_evidence_item(record: PaperEvidenceRecord) -> str:
    finding = f" - {escape(record.key_finding)}" if record.key_finding else ""

    return f"""
    <li>
      <a href="{escape(record.url)}">{escape(record.title)}</a>
      <span class="meta">
        [{escape(record.stance)} &middot; tier {record.tier}]
      </span>
      {finding}
    </li>
    """


def _claim_embed_iframe(src: str, title: str) -> str:
    if not src.startswith(("http://", "https://")):
        raise HtmlAssemblyError("Inline clip iframe requires a valid embed URL.")

    # referrerpolicy + document referrer help satisfy YouTube embed client-id checks (Error 153).
    allow = (
        "accelerometer; autoplay; clipboard-write; encrypted-media; "
        "gyroscope; picture-in-picture; web-share"
    )
    return f"""
    <iframe
      src="{_escape_url_attribute(src)}"
      title="{escape(title)}"
      loading="lazy"
      referrerpolicy="strict-origin-when-cross-origin"
      allow="{allow}"
      allowfullscreen>
    </iframe>
    """


def _escape_url_attribute(url: str) -> str:
    return escape(url, quote=True).replace("&amp;", "&")


def _base_css() -> str:
    return """
    :root {
      color-scheme: light;
      --bg: #f8f7f3;
      --paper: #ffffff;
      --ink: #171717;
      --muted: #5f6368;
      --line: #dedbd2;
      --accent: #22324a;
    }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: ui-serif, Georgia, Cambria, "Times New Roman", serif;
      line-height: 1.6;
    }

    a {
      color: var(--accent);
    }

    .inquiry-paper {
      max-width: 980px;
      margin: 0 auto;
      padding: 48px 20px;
    }

    .paper-header,
    .paper-section {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 28px;
      margin-bottom: 24px;
      box-shadow: 0 12px 35px rgba(0, 0, 0, 0.05);
    }

    .eyebrow {
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 0.78rem;
      margin: 0 0 8px;
    }

    h1,
    h2,
    h3 {
      line-height: 1.2;
      margin-top: 0;
    }

    h1 {
      font-size: clamp(2rem, 5vw, 4rem);
      letter-spacing: -0.04em;
    }

    h2 {
      font-size: 1.65rem;
    }

    h3 {
      font-size: 1.15rem;
    }

    .abstract {
      font-size: 1.12rem;
      color: #2b2b2b;
    }

    .source-attribution {
      border-top: 1px solid var(--line);
      margin-top: 24px;
      padding-top: 18px;
    }

    .claim-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 18px;
    }

    .claim-card,
    .evidence-block {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 18px;
      background: #fffdfa;
    }

    .claim-type,
    .meta,
    .speaker,
    .verdict {
      color: var(--muted);
      font-size: 0.95rem;
    }

    blockquote {
      border-left: 4px solid var(--accent);
      margin-left: 0;
      padding-left: 16px;
      color: #262626;
    }

    iframe {
      width: 100%;
      aspect-ratio: 16 / 9;
      border: 0;
      border-radius: 12px;
      background: #111;
      margin-top: 12px;
    }

    details {
      margin-top: 14px;
    }

    summary {
      cursor: pointer;
      font-weight: 700;
    }

    .evidence-list {
      padding-left: 1.2rem;
    }

    .evidence-list li {
      margin-bottom: 0.65rem;
    }
    """
