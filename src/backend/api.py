from __future__ import annotations

from typing import Dict
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status

from src.backend.schemas import (
    ClaimAuditSummary,
    InquiryAuditReport,
    VideoCreate,
    VideoRead,
)

app = FastAPI(
    title="Inquiry Engine API",
    description="Backend service for registering videos and exposing inquiry audit data.",
    version="0.1.0",
)

# Temporary in-memory store.
# Week 6 will later replace this with the relational database layer.
_VIDEO_STORE: Dict[str, VideoRead] = {}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/videos",
    response_model=VideoRead,
    status_code=status.HTTP_201_CREATED,
)
def register_video(payload: VideoCreate) -> VideoRead:
    video_id = f"video_{uuid4().hex[:12]}"

    video = VideoRead(
        id=video_id,
        url=payload.url,
        title=payload.title,
        embed_base_url=payload.embed_base_url,
        duration_seconds=payload.duration_seconds,
        speaker_id=None,
    )

    _VIDEO_STORE[video_id] = video
    return video


@app.get("/videos/{video_id}", response_model=VideoRead)
def get_video(video_id: str) -> VideoRead:
    video = _VIDEO_STORE.get(video_id)

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found: {video_id}",
        )

    return video


@app.get("/videos/{video_id}/audit", response_model=InquiryAuditReport)
def get_video_audit(video_id: str) -> InquiryAuditReport:
    if video_id not in _VIDEO_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found: {video_id}",
        )

    return InquiryAuditReport(
        video_id=video_id,
        claim_count=0,
        evidence_count=0,
        claims=[],
    )
