from src.html.component_renderers import (
    ClaimCardViewModel,
    EvidencePanelViewModel,
    EvidenceRecordViewModel,
    ReadingItemViewModel,
    ReadingListViewModel,
    render_claim_card,
    render_evidence_panel,
    render_reading_list,
)


def test_render_claim_card_contains_accessible_expandable_markup():
    html = render_claim_card(
        ClaimCardViewModel(
            claim_id="claim_001",
            claim_label="Non-stationarity claim",
            speaker_quote="Multi-agent environments are not stationary.",
            adjudication="The evidence supports this with qualifications.",
            retrieval_trail=[
                "Generated supportive query.",
                "Retrieved peer-reviewed source.",
            ],
            embed_url="https://www.youtube-nocookie.com/embed/ABC123?start=10&end=20",
        )
    )

    assert 'data-component="claim-card"' in html
    assert 'data-action="toggle-claim"' in html
    assert 'data-action="toggle-claim-mode"' in html
    assert "data-claim-details" in html
    assert 'aria-controls="claim-details-claim_001"' in html
    assert "Multi-agent environments are not stationary." in html
    assert "https://www.youtube-nocookie.com/embed/ABC123?start=10&amp;end=20" in html


def test_render_claim_card_escapes_user_content():
    html = render_claim_card(
        ClaimCardViewModel(
            claim_id="claim_002",
            claim_label="<script>alert('bad')</script>",
            speaker_quote="<b>not trusted</b>",
            adjudication="Safe text.",
        )
    )

    assert "<script>alert" not in html
    assert "&lt;script&gt;alert" in html
    assert "&lt;b&gt;not trusted&lt;/b&gt;" in html


def test_render_claim_card_has_empty_retrieval_state():
    html = render_claim_card(
        ClaimCardViewModel(
            claim_id="claim_003",
            claim_label="Empty trail claim",
            speaker_quote="A claim.",
            adjudication="An adjudication.",
        )
    )

    assert "No retrieval trail is available" in html


def test_render_evidence_panel_contains_filters_and_records():
    html = render_evidence_panel(
        EvidencePanelViewModel(
            claim_id="claim_001",
            title="Evidence for Claim 001",
            records=[
                EvidenceRecordViewModel(
                    evidence_id="ev_001",
                    title="A peer-reviewed paper",
                    stance="supports",
                    tier=1,
                    source_url="https://example.com/paper",
                    key_finding="The paper supports the claim.",
                    citation_label="Smith 2024",
                )
            ],
        )
    )

    assert 'data-component="evidence-panel"' in html
    assert 'data-filter="evidence-stance"' in html
    assert 'data-filter="evidence-tier"' in html
    assert "data-evidence-record" in html
    assert 'data-stance="supports"' in html
    assert 'data-tier="1"' in html
    assert 'data-action="toggle-source-detail"' in html
    assert "Smith 2024" in html


def test_render_evidence_panel_has_empty_state():
    html = render_evidence_panel(
        EvidencePanelViewModel(
            claim_id="claim_001",
            title="Evidence for Claim 001",
            records=[],
        )
    )

    assert "No evidence records are available" in html


def test_render_reading_list_contains_filters_sort_and_items():
    html = render_reading_list(
        ReadingListViewModel(
            topics=["Reinforcement Learning", "Multi-Agent Systems"],
            items=[
                ReadingItemViewModel(
                    title="Open access survey",
                    topic="Reinforcement Learning",
                    tier=1,
                    source_url="https://example.com/survey",
                    citation_label="Survey 2023",
                    open_access=True,
                )
            ],
        )
    )

    assert 'data-component="reading-list"' in html
    assert 'data-filter="reading-topic"' in html
    assert 'data-filter="reading-tier"' in html
    assert 'data-sort="reading-accessibility"' in html
    assert "data-reading-item" in html
    assert 'data-topic="reinforcement_learning"' in html
    assert 'data-open-access="true"' in html
    assert "Open access survey" in html


def test_render_reading_list_has_empty_state():
    html = render_reading_list(
        ReadingListViewModel(
            topics=[],
            items=[],
        )
    )

    assert "No further-reading items are available" in html


def test_render_reading_list_escapes_link_text_and_title():
    html = render_reading_list(
        ReadingListViewModel(
            topics=["AI <Safety>"],
            items=[
                ReadingItemViewModel(
                    title="<Unsafe Title>",
                    topic="AI <Safety>",
                    tier=2,
                    source_url="https://example.com/source",
                    citation_label="<Unsafe Citation>",
                    open_access=False,
                )
            ],
        )
    )

    assert "<Unsafe Title>" not in html
    assert "&lt;Unsafe Title&gt;" in html
    assert "&lt;Unsafe Citation&gt;" in html
