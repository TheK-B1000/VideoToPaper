from src.html.component_renderers import (
    ClaimCardViewModel,
    EvidencePanelViewModel,
    EvidenceRecordViewModel,
    ReadingItemViewModel,
    ReadingListViewModel,
)
from src.html.section_builders import (
    InteractiveSectionInput,
    build_claims_section,
    build_evidence_section,
    build_interactive_section_sequence,
    build_interactive_sections,
    build_reading_section,
)


def test_build_claims_section_from_claim_cards():
    section = build_claims_section(
        [
            ClaimCardViewModel(
                claim_id="claim_001",
                claim_label="Stationarity claim",
                speaker_quote="The environment is not stationary.",
                adjudication="The literature supports this with qualifications.",
                retrieval_trail=["Query generated", "Evidence retrieved"],
            )
        ]
    )

    assert section.section_id == "claims"
    assert section.title == "Claims Under Examination"
    assert 'data-component="claim-card"' in section.body_html
    assert "The environment is not stationary." in section.body_html


def test_build_claims_section_empty_state():
    section = build_claims_section([])

    assert section.section_id == "claims"
    assert "No verifiable claims were identified" in section.body_html


def test_build_evidence_section_from_panels():
    section = build_evidence_section(
        [
            EvidencePanelViewModel(
                claim_id="claim_001",
                title="Evidence for Stationarity Claim",
                records=[
                    EvidenceRecordViewModel(
                        evidence_id="ev_001",
                        title="A peer-reviewed study",
                        stance="supports",
                        tier=1,
                        source_url="https://example.com/study",
                        key_finding="The study supports the claim.",
                        citation_label="Smith 2024",
                    )
                ],
            )
        ]
    )

    assert section.section_id == "evidence"
    assert section.title == "Evidence Review"
    assert 'data-component="evidence-panel"' in section.body_html
    assert 'data-evidence-record' in section.body_html
    assert "Smith 2024" in section.body_html


def test_build_evidence_section_empty_state():
    section = build_evidence_section([])

    assert section.section_id == "evidence"
    assert "No external evidence has been retrieved" in section.body_html


def test_build_reading_section_from_reading_list():
    section = build_reading_section(
        ReadingListViewModel(
            topics=["Multi-Agent Systems"],
            items=[
                ReadingItemViewModel(
                    title="A useful survey",
                    topic="Multi-Agent Systems",
                    tier=1,
                    source_url="https://example.com/survey",
                    citation_label="Survey 2024",
                    open_access=True,
                )
            ],
        )
    )

    assert section.section_id == "reading"
    assert section.title == "Further Reading"
    assert 'data-component="reading-list"' in section.body_html
    assert 'data-reading-item' in section.body_html
    assert "A useful survey" in section.body_html


def test_build_reading_section_empty_state():
    section = build_reading_section(None)

    assert section.section_id == "reading"
    assert "No further-reading sources are available" in section.body_html


def test_build_interactive_sections_returns_named_sections():
    sections = build_interactive_sections(
        InteractiveSectionInput(
            claim_cards=[
                ClaimCardViewModel(
                    claim_id="claim_001",
                    claim_label="Claim One",
                    speaker_quote="A quote.",
                    adjudication="An adjudication.",
                )
            ],
            evidence_panels=[],
            reading_list=None,
        )
    )

    assert sections.claims.section_id == "claims"
    assert sections.evidence.section_id == "evidence"
    assert sections.reading.section_id == "reading"


def test_build_interactive_section_sequence_returns_expected_order():
    sequence = build_interactive_section_sequence(
        InteractiveSectionInput(
            claim_cards=[],
            evidence_panels=[],
            reading_list=None,
        )
    )

    assert [section.section_id for section in sequence] == [
        "claims",
        "evidence",
        "reading",
    ]