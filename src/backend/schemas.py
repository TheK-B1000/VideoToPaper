from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


ClaimType = Literal[
    "empirical_technical",
    "empirical_scientific",
    "empirical_historical",
    "interpretive",
    "normative",
    "anecdotal",
    "predictive",
]

VerificationStrategy = Literal[
    "literature_review",
    "source_context_review",
    "future_tracking",
    "not_externally_verified",
]

EvidenceTier = Literal[1, 2, 3]

EvidenceStance = Literal[
    "supports",
    "contradicts",
    "complicates",
    "qualifies",
    "neutral",
]

RunStatus = Literal[
    "queued",
    "running",
    "completed",
    "failed",
]


class SpeakerCreate(BaseModel):
    name: str = Field(..., min_length=1)
    credentials: Optional[str] = None
    stated_motivations: Optional[str] = None


class SpeakerRead(SpeakerCreate):
    id: str


class VideoCreate(BaseModel):
    url: HttpUrl
    title: str = Field(..., min_length=1)
    embed_base_url: HttpUrl
    duration_seconds: Optional[float] = Field(default=None, ge=0)
    speaker: Optional[SpeakerCreate] = None

    @field_validator("embed_base_url")
    @classmethod
    def embed_url_should_use_privacy_domain(cls, value: HttpUrl) -> HttpUrl:
        url = str(value)
        if "youtube-nocookie.com/embed/" not in url:
            raise ValueError(
                "embed_base_url must use YouTube's privacy-respecting embed domain"
            )
        return value


class VideoRead(BaseModel):
    id: str
    url: HttpUrl
    title: str
    embed_base_url: HttpUrl
    duration_seconds: Optional[float] = None
    speaker_id: Optional[str] = None


class AnchorClip(BaseModel):
    start: float = Field(..., ge=0)
    end: float = Field(..., ge=0)

    @field_validator("end")
    @classmethod
    def end_must_be_after_start(cls, value: float, info: Any) -> float:
        start = info.data.get("start")
        if start is not None and value <= start:
            raise ValueError("anchor clip end must be greater than start")
        return value


class ClaimCreate(BaseModel):
    video_id: str = Field(..., min_length=1)
    verbatim_quote: str = Field(..., min_length=1)
    claim_type: ClaimType
    verification_strategy: VerificationStrategy
    char_offset_start: int = Field(..., ge=0)
    char_offset_end: int = Field(..., ge=0)
    anchor_clip: AnchorClip
    embed_url: HttpUrl

    @field_validator("char_offset_end")
    @classmethod
    def char_end_must_be_after_start(cls, value: int, info: Any) -> int:
        start = info.data.get("char_offset_start")
        if start is not None and value <= start:
            raise ValueError("char_offset_end must be greater than char_offset_start")
        return value


class ClaimRead(ClaimCreate):
    id: str


class EvidenceRecordCreate(BaseModel):
    claim_id: str = Field(..., min_length=1)
    tier: EvidenceTier
    stance: EvidenceStance
    source_title: str = Field(..., min_length=1)
    source_url: Optional[HttpUrl] = None
    identifier: Optional[str] = None
    abstract_or_summary: Optional[str] = None
    key_finding: Optional[str] = None

    @field_validator("identifier")
    @classmethod
    def identifier_cannot_be_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("identifier cannot be blank")
        return value


class EvidenceRecordRead(EvidenceRecordCreate):
    id: str


class PaperCreate(BaseModel):
    video_id: str = Field(..., min_length=1)
    section_speaker_perspective: str = ""
    section_evidence_review: str = ""
    section_further_reading: str = ""
    html_render_path: Optional[str] = None


class PaperRead(PaperCreate):
    id: str


class RunCreate(BaseModel):
    video_id: str = Field(..., min_length=1)
    pipeline_config: Dict[str, Any] = Field(default_factory=dict)


class RunRead(BaseModel):
    id: str
    video_id: str
    status: RunStatus
    pipeline_config: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ClaimAuditSummary(BaseModel):
    claim_id: str
    has_verbatim_quote: bool
    has_anchor_clip: bool
    has_embed_url: bool
    evidence_count: int = Field(..., ge=0)
    stances_present: List[EvidenceStance] = Field(default_factory=list)


class InquiryAuditReport(BaseModel):
    video_id: str
    claim_count: int = Field(..., ge=0)
    evidence_count: int = Field(..., ge=0)
    claims: List[ClaimAuditSummary] = Field(default_factory=list)
