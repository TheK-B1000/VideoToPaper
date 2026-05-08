"""
Generate a self-contained interactive sample HTML paper fixture.

Use this file for manual browser testing of interactive components without a
server or framework.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.html.component_renderers import (
    ClaimCardViewModel,
    EvidencePanelViewModel,
    EvidenceRecordViewModel,
    ReadingItemViewModel,
    ReadingListViewModel,
)
from src.html.paper_assembler import PaperDocument, write_html_paper
from src.html.section_builders import InteractiveSectionInput, build_interactive_section_sequence


DEFAULT_OUTPUT_PATH = Path("data/outputs/sample_interactive_paper_fixture.html")


def build_sample_document() -> PaperDocument:
    claim_cards = [
        ClaimCardViewModel(
            claim_id="claim_001",
            claim_label="Claim 001: Non-stationarity challenge",
            speaker_quote=(
                "In multi-agent systems, the environment keeps changing as other agents learn."
            ),
            adjudication=(
                "Evidence supports this framing, with qualifications about mitigations from "
                "self-play and scale."
            ),
            retrieval_trail=[
                "Generated broad retrieval query from claim quote.",
                "Matched Tier 1 survey on MARL non-stationarity.",
                "Matched qualification evidence on practical mitigation.",
            ],
            embed_url="https://www.youtube-nocookie.com/embed/ABC123?start=252&end=263&rel=0",
        ),
        ClaimCardViewModel(
            claim_id="claim_002",
            claim_label="Claim 002: Coordination remains fragile",
            speaker_quote=(
                "Coordination often breaks when incentives are only partially aligned."
            ),
            adjudication=(
                "Evidence is mixed: several sources support the claim while others show "
                "robust coordination under constrained settings."
            ),
            retrieval_trail=[
                "Generated focused query on incentive alignment.",
                "Retrieved mixed evidence from benchmark and real-world settings.",
            ],
            embed_url="https://www.youtube-nocookie.com/embed/ABC123?start=410&end=430&rel=0",
        ),
    ]

    evidence_panels = [
        EvidencePanelViewModel(
            claim_id="claim_001",
            title="Evidence for Claim 001",
            records=[
                EvidenceRecordViewModel(
                    evidence_id="ev_001",
                    title="A Selective Overview of MARL",
                    stance="supports",
                    tier=1,
                    source_url="https://example.org/marl-overview",
                    key_finding="Non-stationarity is a central challenge in MARL settings.",
                    citation_label="Survey 2019",
                ),
                EvidenceRecordViewModel(
                    evidence_id="ev_002",
                    title="Large-Scale Self-Play Results",
                    stance="qualifies",
                    tier=1,
                    source_url="https://example.org/self-play",
                    key_finding=(
                        "Scaling and curriculum design can reduce instability in practice."
                    ),
                    citation_label="Scale 2021",
                ),
                EvidenceRecordViewModel(
                    evidence_id="ev_003",
                    title="Stable Coordination Under Constraints",
                    stance="contradicts",
                    tier=2,
                    source_url="https://example.org/stable-coordination",
                    key_finding="Some constrained environments remain stable across training.",
                    citation_label="Coordination 2020",
                ),
            ],
        ),
        EvidencePanelViewModel(
            claim_id="claim_002",
            title="Evidence for Claim 002",
            records=[
                EvidenceRecordViewModel(
                    evidence_id="ev_004",
                    title="Incentive Misalignment in Teams",
                    stance="supports",
                    tier=2,
                    source_url="https://example.org/incentive-misalignment",
                    key_finding=(
                        "Partial alignment frequently causes brittle coordination outcomes."
                    ),
                    citation_label="Teams 2022",
                ),
                EvidenceRecordViewModel(
                    evidence_id="ev_005",
                    title="Robust Multi-Agent Cooperation",
                    stance="complicates",
                    tier=1,
                    source_url="https://example.org/robust-cooperation",
                    key_finding=(
                        "Robust cooperation is achievable with explicit communication scaffolds."
                    ),
                    citation_label="Coop 2023",
                ),
            ],
        ),
    ]

    reading_list = ReadingListViewModel(
        topics=["Reinforcement Learning", "Multi-Agent Systems", "Safety"],
        items=[
            ReadingItemViewModel(
                title="Open Access MARL Survey",
                topic="Multi-Agent Systems",
                tier=1,
                source_url="https://example.org/open-survey",
                citation_label="Open Survey 2024",
                open_access=True,
            ),
            ReadingItemViewModel(
                title="Reward Design and Alignment",
                topic="Safety",
                tier=2,
                source_url="https://example.org/reward-alignment",
                citation_label="Alignment 2022",
                open_access=False,
            ),
            ReadingItemViewModel(
                title="Sample Efficiency in RL",
                topic="Reinforcement Learning",
                tier=2,
                source_url="https://example.org/sample-efficiency",
                citation_label="Efficiency 2021",
                open_access=True,
            ),
        ],
    )

    sections = build_interactive_section_sequence(
        InteractiveSectionInput(
            claim_cards=claim_cards,
            evidence_panels=evidence_panels,
            reading_list=reading_list,
        )
    )

    return PaperDocument(
        title="Inquiry Engine Interactive Fixture",
        abstract=(
            "Self-contained interactive fixture for testing claim cards, evidence filters, "
            "and reading-list controls in a local browser."
        ),
        source_title="What Most People Get Wrong About Reinforcement Learning",
        source_url="https://www.youtube.com/watch?v=ABC123",
        speaker_name="Dr. Jane Smith",
        sections=sections,
        interactive_payload={
            "claims": [
                {"claim_id": "claim_001"},
                {"claim_id": "claim_002"},
            ],
            "evidence": [
                {"claim_id": "claim_001", "record_count": 3},
                {"claim_id": "claim_002", "record_count": 2},
            ],
            "reading": {
                "topics": ["Reinforcement Learning", "Multi-Agent Systems", "Safety"],
            },
        },
    )


def generate_sample_paper_fixture(
    *,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    document = build_sample_document()
    return write_html_paper(document, output_path)


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser(
        description="Generate a local interactive paper fixture."
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output path for the self-contained sample HTML file.",
    )
    args = parser.parse_args(argv)

    output_path = generate_sample_paper_fixture(output_path=args.output_path)
    print(f"Sample interactive paper fixture written to: {output_path}")
    return output_path


if __name__ == "__main__":
    main()
