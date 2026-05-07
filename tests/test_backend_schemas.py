import pytest
from pydantic import ValidationError

from src.backend.schemas import (
    AnchorClip,
    ClaimAuditSummary,
    ClaimCreate,
    EvidenceRecordCreate,
    InquiryAuditReport,
    VideoCreate,
)


def test_video_create_requires_privacy_respecting_embed_url():
    video = VideoCreate(
        url="https://www.youtube.com/watch?v=ABC123",
        title="Example Video",
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
        duration_seconds=120.0,
    )

    assert str(video.embed_base_url).startswith(
        "https://www.youtube-nocookie.com/embed/ABC123"
    )


def test_video_create_rejects_non_embed_url():
    with pytest.raises(ValidationError):
        VideoCreate(
            url="https://www.youtube.com/watch?v=ABC123",
            title="Example Video",
            embed_base_url="https://www.youtube.com/watch?v=ABC123",
            duration_seconds=120.0,
        )


def test_anchor_clip_requires_end_after_start():
    clip = AnchorClip(start=10.0, end=15.0)

    assert clip.start == 10.0
    assert clip.end == 15.0

    with pytest.raises(ValidationError):
        AnchorClip(start=15.0, end=10.0)


def test_claim_create_validates_offsets_and_clip_contract():
    claim = ClaimCreate(
        video_id="video_001",
        verbatim_quote="Multi-agent systems are non-stationary.",
        claim_type="empirical_technical",
        verification_strategy="literature_review",
        char_offset_start=100,
        char_offset_end=141,
        anchor_clip={"start": 25.0, "end": 32.0},
        embed_url="https://www.youtube-nocookie.com/embed/ABC123?start=25&end=32",
    )

    assert claim.video_id == "video_001"
    assert claim.anchor_clip.start == 25.0

    with pytest.raises(ValidationError):
        ClaimCreate(
            video_id="video_001",
            verbatim_quote="Bad offsets",
            claim_type="empirical_technical",
            verification_strategy="literature_review",
            char_offset_start=200,
            char_offset_end=100,
            anchor_clip={"start": 25.0, "end": 32.0},
            embed_url="https://www.youtube-nocookie.com/embed/ABC123?start=25&end=32",
        )


def test_evidence_record_requires_valid_tier_and_stance():
    evidence = EvidenceRecordCreate(
        claim_id="claim_001",
        tier=1,
        stance="supports",
        source_title="A Survey of Multi-Agent Reinforcement Learning",
        source_url="https://example.com/paper",
        identifier="doi:10.0000/example",
        key_finding="The paper discusses non-stationarity in MARL.",
    )

    assert evidence.tier == 1
    assert evidence.stance == "supports"

    with pytest.raises(ValidationError):
        EvidenceRecordCreate(
            claim_id="claim_001",
            tier=4,
            stance="supports",
            source_title="Invalid tier example",
        )


def test_audit_report_tracks_claim_and_evidence_counts():
    report = InquiryAuditReport(
        video_id="video_001",
        claim_count=1,
        evidence_count=2,
        claims=[
            ClaimAuditSummary(
                claim_id="claim_001",
                has_verbatim_quote=True,
                has_anchor_clip=True,
                has_embed_url=True,
                evidence_count=2,
                stances_present=["supports", "qualifies"],
            )
        ],
    )

    assert report.claim_count == 1
    assert report.evidence_count == 2
    assert report.claims[0].stances_present == ["supports", "qualifies"]
