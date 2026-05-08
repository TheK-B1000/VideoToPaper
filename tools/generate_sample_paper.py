"""
Generate a sample interactive Inquiry Engine paper.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.html.component_renderers import (  # noqa: E402
    ClaimCardViewModel,
    EvidencePanelViewModel,
    EvidenceRecordViewModel,
    ReadingItemViewModel,
    ReadingListViewModel,
)
from src.html.paper_assembler import PaperDocument, write_html_paper  # noqa: E402
from src.html.section_builders import (  # noqa: E402
    InteractiveSectionInput,
    build_interactive_section_sequence,
)


DEFAULT_OUTPUT_PATH = Path("data/outputs/sample_interactive_paper.html")


def build_sample_document() -> PaperDocument:
    claim = ClaimCardViewModel(
        claim_id="claim_0042",
        claim_label="Non-stationarity in multi-agent reinforcement learning",
        speaker_quote=(
            "non-stationarity makes single-agent algorithms fundamentally unsuited"
        ),
        adjudication=(
            "The claim is directionally supported, but specialized MARL methods "
            "complicate the strongest version."
        ),
        retrieval_trail=[
            "Generated query about non-stationarity in multi-agent RL.",
            "Retrieved selective MARL overview.",
            "Matched source against claim timing and stance.",
        ],
        embed_url="https://www.youtube-nocookie.com/embed/ABC123?start=252&end=263&rel=0",
    )

    evidence_record = EvidenceRecordViewModel(
        evidence_id="ev_001",
        title="Multi-Agent Reinforcement Learning: A Selective Overview",
        stance="qualifies",
        tier=1,
        source_url="https://example.org/marl-overview",
        key_finding=(
            "Multi-agent settings can violate stationarity assumptions, but "
            "specialized approaches address this problem."
        ),
        citation_label="Selective MARL Overview",
    )

    reading_item = ReadingItemViewModel(
        title="Multi-Agent Reinforcement Learning: A Selective Overview",
        topic="Multi-Agent Systems",
        tier=1,
        source_url="https://example.org/marl-overview",
        citation_label="Selective MARL Overview",
        open_access=True,
    )

    sections = build_interactive_section_sequence(
        InteractiveSectionInput(
            claim_cards=[claim],
            evidence_panels=[
                EvidencePanelViewModel(
                    claim_id="claim_0042",
                    title="Evidence for claim_0042",
                    records=[evidence_record],
                )
            ],
            reading_list=ReadingListViewModel(
                topics=["Multi-Agent Systems", "Reinforcement Learning"],
                items=[reading_item],
            ),
        )
    )

    return PaperDocument(
        title="Sample Interactive Inquiry Paper",
        abstract=(
            "A local-file friendly sample paper with interactive claim, evidence, "
            "and reading-list components."
        ),
        source_title="What Most People Get Wrong About Reinforcement Learning",
        source_url="https://www.youtube.com/watch?v=ABC123",
        speaker_name="Dr. Jane Smith",
        sections=sections,
        interactive_payload={
            "claims": [
                {
                    "claim_id": "claim_0042",
                    "quote": claim.speaker_quote,
                    "verdict": "well_supported_with_qualifications",
                }
            ],
            "evidence": [
                {
                    "evidence_id": evidence_record.evidence_id,
                    "stance": evidence_record.stance,
                    "tier": evidence_record.tier,
                }
            ],
            "reading": [
                {
                    "title": reading_item.title,
                    "topic": reading_item.topic,
                    "tier": reading_item.tier,
                    "open_access": reading_item.open_access,
                }
            ],
        },
    )


def main() -> int:
    output_path = write_html_paper(build_sample_document(), DEFAULT_OUTPUT_PATH)
    print(f"Sample interactive paper written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
