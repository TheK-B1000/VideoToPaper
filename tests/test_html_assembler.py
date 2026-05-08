from pathlib import Path

import pytest

from src.paper.html_assembler import (
    HtmlAssemblyError,
    PaperAdjudication,
    PaperClaim,
    PaperDocument,
    PaperEvidenceRecord,
    PaperVideo,
    assemble_html_paper,
    build_clip_embed_url,
    write_html_paper,
)


def _sample_document() -> PaperDocument:
    video = PaperVideo(
        video_id="ABC123",
        title="What Most People Get Wrong About Reinforcement Learning",
        url="https://www.youtube.com/watch?v=ABC123",
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
        speaker_name="Dr. Jane Smith",
        speaker_credentials="Professor of Computer Science",
    )

    claim = PaperClaim(
        claim_id="claim_0042",
        verbatim_quote="non-stationarity makes single-agent algorithms fundamentally unsuited",
        claim_type="empirical_technical",
        anchor_clip_start=252.4,
        anchor_clip_end=263.0,
    )

    evidence = PaperEvidenceRecord(
        evidence_id="ev_001",
        claim_id="claim_0042",
        title="Multi-Agent Reinforcement Learning: A Selective Overview",
        source="Journal of Artificial Intelligence Research",
        url="https://example.org/marl-overview",
        tier=1,
        stance="qualifies",
        identifier="doi:10.0000/example",
        key_finding="Multi-agent settings can violate stationarity assumptions, but specialized approaches address this problem.",
    )

    adjudication = PaperAdjudication(
        claim_id="claim_0042",
        verdict="well_supported_with_qualifications",
        confidence="high",
        narrative=(
            "The speaker's claim is directionally supported, but the literature "
            "shows that specialized multi-agent methods complicate the strongest version."
        ),
        qualifies=["ev_001"],
    )

    return PaperDocument(
        title="Inquiry Paper: Reinforcement Learning Misconceptions",
        abstract="A charitable, evidence-balanced review of a technical claim about reinforcement learning.",
        video=video,
        speaker_perspective=(
            "The speaker argues that naive single-agent assumptions become fragile "
            "when moved into adaptive multi-agent settings."
        ),
        claims=[claim],
        evidence_records=[evidence],
        adjudications=[adjudication],
        limitations=[
            "This pass relies on retrieved metadata and does not yet verify full-text source claims."
        ],
        further_reading=[evidence],
    )


def test_build_clip_embed_url_adds_privacy_respecting_timing_params() -> None:
    url = build_clip_embed_url(
        "https://www.youtube-nocookie.com/embed/ABC123",
        start=252.4,
        end=263.0,
    )

    assert url == "https://www.youtube-nocookie.com/embed/ABC123?start=252&end=263&rel=0"


def test_assemble_html_paper_contains_required_sections_and_embed() -> None:
    html = assemble_html_paper(_sample_document())

    assert '<article class="inquiry-paper">' in html
    assert 'id="perspective"' in html
    assert 'id="claims"' in html
    assert 'id="evidence"' in html
    assert 'id="agreement"' in html
    assert 'id="complexity"' in html
    assert 'id="limitations"' in html
    assert 'id="reading"' in html
    assert 'id="references"' in html

    assert "https://www.youtube-nocookie.com/embed/ABC123?start=252&end=263&rel=0" in html
    assert "Source Attribution" in html
    assert "Dr. Jane Smith" in html


def test_assemble_html_paper_escapes_user_controlled_text() -> None:
    document = _sample_document()

    unsafe_claim = PaperClaim(
        claim_id="claim_script",
        verbatim_quote='<script>alert("bad")</script>',
        claim_type="empirical_technical",
        anchor_clip_start=10,
        anchor_clip_end=20,
    )

    document = PaperDocument(
        title=document.title,
        abstract=document.abstract,
        video=document.video,
        speaker_perspective=document.speaker_perspective,
        claims=[unsafe_claim],
        evidence_records=[],
        adjudications=[],
        limitations=[],
        further_reading=[],
    )

    html = assemble_html_paper(document)

    assert "<script>" not in html
    assert "&lt;script&gt;alert(&quot;bad&quot;)&lt;/script&gt;" in html


def test_assemble_html_paper_always_renders_limitations_section() -> None:
    document = _sample_document()

    document = PaperDocument(
        title=document.title,
        abstract=document.abstract,
        video=document.video,
        speaker_perspective=document.speaker_perspective,
        claims=document.claims,
        evidence_records=document.evidence_records,
        adjudications=document.adjudications,
        limitations=[],
        further_reading=[],
    )

    html = assemble_html_paper(document)

    assert 'id="limitations"' in html
    assert "No additional limitations were detected by the assembler" in html


def test_assemble_html_paper_rejects_evidence_for_unknown_claim() -> None:
    document = _sample_document()

    bad_evidence = PaperEvidenceRecord(
        evidence_id="ev_bad",
        claim_id="missing_claim",
        title="Bad Record",
        source="Example",
        url="https://example.org/bad",
        tier=1,
        stance="supports",
    )

    document = PaperDocument(
        title=document.title,
        abstract=document.abstract,
        video=document.video,
        speaker_perspective=document.speaker_perspective,
        claims=document.claims,
        evidence_records=[bad_evidence],
        adjudications=document.adjudications,
        limitations=document.limitations,
        further_reading=[],
    )

    with pytest.raises(HtmlAssemblyError, match="references unknown claim"):
        assemble_html_paper(document)


def test_assemble_html_paper_rejects_invalid_evidence_url() -> None:
    document = _sample_document()

    bad_evidence = PaperEvidenceRecord(
        evidence_id="ev_bad_url",
        claim_id="claim_0042",
        title="Bad URL",
        source="Example",
        url="not-a-real-url",
        tier=1,
        stance="supports",
    )

    document = PaperDocument(
        title=document.title,
        abstract=document.abstract,
        video=document.video,
        speaker_perspective=document.speaker_perspective,
        claims=document.claims,
        evidence_records=[bad_evidence],
        adjudications=document.adjudications,
        limitations=document.limitations,
        further_reading=[],
    )

    with pytest.raises(HtmlAssemblyError, match="resolvable URL"):
        assemble_html_paper(document)


def test_write_html_paper_creates_output_file(tmp_path: Path) -> None:
    output_path = tmp_path / "paper.html"

    written_path = write_html_paper(_sample_document(), output_path)

    assert written_path == output_path
    assert output_path.exists()

    html = output_path.read_text(encoding="utf-8")
    assert "Inquiry Paper: Reinforcement Learning Misconceptions" in html
    assert '<article class="inquiry-paper">' in html
