"""
HTML renderers for Week 9 interactive Inquiry Engine components.

These render semantic, progressively-enhanced HTML that is hydrated by the
vanilla JavaScript bundle in src/html/interactive_components.py.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class ClaimCardViewModel:
    claim_id: str
    claim_label: str
    speaker_quote: str
    adjudication: str
    retrieval_trail: Sequence[str] = field(default_factory=list)
    embed_url: str | None = None


@dataclass(frozen=True)
class EvidenceRecordViewModel:
    evidence_id: str
    title: str
    stance: str
    tier: int
    source_url: str
    key_finding: str
    citation_label: str


@dataclass(frozen=True)
class EvidencePanelViewModel:
    claim_id: str
    title: str
    records: Sequence[EvidenceRecordViewModel] = field(default_factory=list)


@dataclass(frozen=True)
class ReadingItemViewModel:
    title: str
    topic: str
    tier: int
    source_url: str
    citation_label: str
    open_access: bool = False


@dataclass(frozen=True)
class ReadingListViewModel:
    topics: Sequence[str]
    items: Sequence[ReadingItemViewModel] = field(default_factory=list)


def render_claim_card(view_model: ClaimCardViewModel) -> str:
    """
    Render one expandable claim card.

    The card remains readable without JavaScript because all essential text
    is present in the HTML document. JavaScript only improves disclosure.
    """

    claim_id = _safe_attr(view_model.claim_id)
    label = _safe_text(view_model.claim_label)
    quote = _safe_text(view_model.speaker_quote)
    adjudication = _safe_text(view_model.adjudication)

    details_id = f"claim-details-{claim_id}"
    quote_id = f"claim-quote-{claim_id}"
    adjudication_id = f"claim-adjudication-{claim_id}"

    retrieval_items = "\n".join(
        f"<li>{_safe_text(item)}</li>" for item in view_model.retrieval_trail
    )

    retrieval_html = (
        f"<ul>{retrieval_items}</ul>"
        if retrieval_items
        else "<p>No retrieval trail is available for this claim yet.</p>"
    )

    embed_html = ""
    if view_model.embed_url:
        embed_url = _safe_attr(view_model.embed_url)
        embed_html = f"""
<div class="claim-card__clip">
  <iframe
    src="{embed_url}"
    title="Anchor clip for {label}"
    loading="lazy"
    allowfullscreen>
  </iframe>
</div>
""".strip()

    return f"""
<article class="claim-card" data-component="claim-card" data-claim-id="{claim_id}">
  <div class="claim-card__header">
    <div>
      <p class="eyebrow">Claim</p>
      <h3>{label}</h3>
    </div>

    <button
      type="button"
      class="claim-card__toggle"
      data-action="toggle-claim"
      aria-controls="{details_id}">
      Expand trail
    </button>
  </div>

  <div id="{quote_id}" data-claim-quote>
    <h4>Speaker quote</h4>
    <blockquote>{quote}</blockquote>
  </div>

  <div id="{adjudication_id}" data-claim-adjudication>
    <h4>Adjudication</h4>
    <p>{adjudication}</p>
  </div>

  <button
    type="button"
    class="claim-card__mode"
    data-action="toggle-claim-mode"
    aria-controls="{quote_id} {adjudication_id}">
    Show adjudication
  </button>

  <div id="{details_id}" data-claim-details>
    <h4>Retrieval trail</h4>
    {retrieval_html}
    {embed_html}
  </div>
</article>
""".strip()


def render_evidence_panel(view_model: EvidencePanelViewModel) -> str:
    """
    Render a filterable evidence panel for one claim.
    """

    claim_id = _safe_attr(view_model.claim_id)
    title = _safe_text(view_model.title)

    records_html = "\n".join(
        render_evidence_record(record) for record in view_model.records
    )

    if not records_html:
        records_html = """
<p class="empty-state">
  No evidence records are available for this claim yet.
</p>
""".strip()

    return f"""
<section
  class="evidence-panel"
  data-component="evidence-panel"
  data-claim-id="{claim_id}">
  <div class="evidence-panel__header">
    <div>
      <p class="eyebrow">Evidence Review</p>
      <h3>{title}</h3>
    </div>
  </div>

  <div class="inquiry-controls" aria-label="Evidence filters">
    <label class="inquiry-control">
      Stance
      <select class="evidence-filter" data-filter="evidence-stance">
        <option value="all">All</option>
        <option value="supports">Supporting</option>
        <option value="contradicts">Contrary</option>
        <option value="qualifies">Qualifying</option>
        <option value="complicates">Complicating</option>
      </select>
    </label>

    <label class="inquiry-control">
      Tier
      <select class="evidence-filter" data-filter="evidence-tier">
        <option value="all">All tiers</option>
        <option value="1">Tier 1</option>
        <option value="2">Tier 2</option>
        <option value="3">Tier 3</option>
      </select>
    </label>
  </div>

  <div class="evidence-panel__records">
    {records_html}
  </div>
</section>
""".strip()


def render_evidence_record(record: EvidenceRecordViewModel) -> str:
    """
    Render one source inside an evidence panel.
    """

    evidence_id = _safe_attr(record.evidence_id)
    detail_id = f"source-detail-{evidence_id}"

    title = _safe_text(record.title)
    stance = _safe_attr(record.stance)
    tier = _safe_attr(str(record.tier))
    source_url = _safe_attr(record.source_url)
    key_finding = _safe_text(record.key_finding)
    citation_label = _safe_text(record.citation_label)

    return f"""
<article
  class="evidence-record"
  data-evidence-record
  data-stance="{stance}"
  data-tier="{tier}">
  <h4>{title}</h4>

  <p>
    <strong>Stance:</strong> {_safe_text(record.stance)}
    ·
    <strong>Tier:</strong> {record.tier}
  </p>

  <p>
    <a href="{source_url}" target="_blank" rel="noopener noreferrer">
      {citation_label}
    </a>
  </p>

  <button
    type="button"
    class="source-detail-toggle"
    data-action="toggle-source-detail"
    aria-controls="{detail_id}">
    Show key finding
  </button>

  <p id="{detail_id}" class="source-detail">
    {key_finding}
  </p>
</article>
""".strip()


def render_reading_list(view_model: ReadingListViewModel) -> str:
    """
    Render the filterable further-reading list.
    """

    topic_options = "\n".join(
        f'<option value="{_safe_attr(_slugify(topic))}">{_safe_text(topic)}</option>'
        for topic in view_model.topics
    )

    items_html = "\n".join(render_reading_item(item) for item in view_model.items)

    if not items_html:
        items_html = """
<p class="empty-state">
  No further-reading items are available yet.
</p>
""".strip()

    return f"""
<section data-component="reading-list" class="reading-list">
  <div class="inquiry-controls" aria-label="Further reading filters">
    <label class="inquiry-control">
      Topic
      <select class="reading-filter" data-filter="reading-topic">
        <option value="all">All topics</option>
        {topic_options}
      </select>
    </label>

    <label class="inquiry-control">
      Tier
      <select class="reading-filter" data-filter="reading-tier">
        <option value="all">All tiers</option>
        <option value="1">Tier 1</option>
        <option value="2">Tier 2</option>
        <option value="3">Tier 3</option>
      </select>
    </label>

    <label class="inquiry-control">
      Sort
      <select class="reading-filter" data-sort="reading-accessibility">
        <option value="default">Default</option>
        <option value="open-access-first">Open access first</option>
      </select>
    </label>
  </div>

  <div data-reading-items>
    {items_html}
  </div>
</section>
""".strip()


def render_reading_item(item: ReadingItemViewModel) -> str:
    """
    Render one further-reading item.
    """

    topic = _safe_attr(_slugify(item.topic))
    tier = _safe_attr(str(item.tier))
    open_access = "true" if item.open_access else "false"

    title = _safe_text(item.title)
    source_url = _safe_attr(item.source_url)
    citation_label = _safe_text(item.citation_label)

    access_label = "Open access" if item.open_access else "Access may be restricted"

    return f"""
<article
  class="reading-item"
  data-reading-item
  data-topic="{topic}"
  data-tier="{tier}"
  data-open-access="{open_access}">
  <h3>{title}</h3>
  <p>
    <strong>Topic:</strong> {_safe_text(item.topic)}
    ·
    <strong>Tier:</strong> {item.tier}
    ·
    <strong>{access_label}</strong>
  </p>
  <p>
    <a href="{source_url}" target="_blank" rel="noopener noreferrer">
      {citation_label}
    </a>
  </p>
</article>
""".strip()


def _safe_text(value: object) -> str:
    return html.escape(str(value), quote=False)


def _safe_attr(value: object) -> str:
    return html.escape(str(value), quote=True)


def _slugify(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("&", "and")
        .replace("/", "-")
        .replace(" ", "_")
    )
