"""
Section builders for interactive Inquiry Engine papers.

These helpers convert structured view models into PaperSection objects.
The assembler should not need to know how claim cards, evidence panels,
or reading lists are rendered internally.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from src.html.component_renderers import (
    ClaimCardViewModel,
    EvidencePanelViewModel,
    ReadingListViewModel,
    render_claim_card,
    render_evidence_panel,
    render_reading_list,
)
from src.html.paper_assembler import PaperSection


@dataclass(frozen=True)
class InteractivePaperSections:
    """
    Interactive sections for the generated paper.
    """

    claims: PaperSection
    evidence: PaperSection
    reading: PaperSection


@dataclass(frozen=True)
class InteractiveSectionInput:
    """
    Structured data required to build interactive paper sections.
    """

    claim_cards: Sequence[ClaimCardViewModel] = field(default_factory=list)
    evidence_panels: Sequence[EvidencePanelViewModel] = field(default_factory=list)
    reading_list: ReadingListViewModel | None = None


def build_claims_section(
    claim_cards: Sequence[ClaimCardViewModel],
    *,
    section_id: str = "claims",
    title: str = "Claims Under Examination",
) -> PaperSection:
    """
    Build the Claims Under Examination section from ClaimCard view models.
    """

    if not claim_cards:
        body_html = """
<p class="empty-state">
  No verifiable claims were identified for this inquiry.
</p>
""".strip()
    else:
        body_html = "\n".join(render_claim_card(card) for card in claim_cards)

    return PaperSection(
        section_id=section_id,
        title=title,
        body_html=body_html,
    )


def build_evidence_section(
    evidence_panels: Sequence[EvidencePanelViewModel],
    *,
    section_id: str = "evidence",
    title: str = "Evidence Review",
) -> PaperSection:
    """
    Build the Evidence Review section from EvidencePanel view models.
    """

    if not evidence_panels:
        body_html = """
<p class="empty-state">
  No external evidence has been retrieved for this inquiry yet.
</p>
""".strip()
    else:
        body_html = "\n".join(
            render_evidence_panel(panel) for panel in evidence_panels
        )

    return PaperSection(
        section_id=section_id,
        title=title,
        body_html=body_html,
    )


def build_reading_section(
    reading_list: ReadingListViewModel | None,
    *,
    section_id: str = "reading",
    title: str = "Further Reading",
) -> PaperSection:
    """
    Build the Further Reading section from a ReadingList view model.
    """

    if reading_list is None:
        body_html = """
<p class="empty-state">
  No further-reading sources are available yet.
</p>
""".strip()
    else:
        body_html = render_reading_list(reading_list)

    return PaperSection(
        section_id=section_id,
        title=title,
        body_html=body_html,
    )


def build_interactive_sections(
    section_input: InteractiveSectionInput,
) -> InteractivePaperSections:
    """
    Build all interactive sections from structured data.
    """

    return InteractivePaperSections(
        claims=build_claims_section(section_input.claim_cards),
        evidence=build_evidence_section(section_input.evidence_panels),
        reading=build_reading_section(section_input.reading_list),
    )


def build_interactive_section_sequence(
    section_input: InteractiveSectionInput,
) -> list[PaperSection]:
    """
    Return sections in the expected paper order.

    This is useful when assembling the final PaperDocument.
    """

    sections = build_interactive_sections(section_input)

    return [
        sections.claims,
        sections.evidence,
        sections.reading,
    ]