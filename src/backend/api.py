from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status

from src.backend.mlops_schemas import (
    AuditEventCreate,
    AuditEventRead,
    RunRecordCreate,
    RunRecordRead,
    new_audit_event_id,
    new_run_id,
)
from src.backend.schemas import (
    InquiryAuditReport,
    VideoCreate,
    VideoRead,
)

app = FastAPI(
    title="Inquiry Engine API",
    description="Backend service for registering videos and exposing inquiry audit data.",
    version="0.1.0",
)

# Temporary in-memory stores.
# Week 6 will later replace these with the relational database layer.
_VIDEO_STORE: Dict[str, VideoRead] = {}
_RUN_STORE: Dict[str, RunRecordRead] = {}
_AUDIT_EVENT_STORE: List[AuditEventRead] = []


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _create_run_record(payload: RunRecordCreate) -> RunRecordRead:
    run = RunRecordRead(
        id=new_run_id(),
        video_id=payload.video_id,
        pipeline_name=payload.pipeline_name,
        status="completed",
        pipeline_config=payload.pipeline_config,
        input_artifacts=payload.input_artifacts,
        output_artifacts={},
        started_at=_now_utc(),
        finished_at=_now_utc(),
        error_message=None,
    )

    _RUN_STORE[run.id] = run
    return run


def _record_audit_event(payload: AuditEventCreate) -> AuditEventRead:
    event = AuditEventRead(
        id=new_audit_event_id(),
        run_id=payload.run_id,
        video_id=payload.video_id,
        event_type=payload.event_type,
        message=payload.message,
        metadata=payload.metadata,
        created_at=_now_utc(),
    )

    _AUDIT_EVENT_STORE.append(event)
    return event


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

    run = _create_run_record(
        RunRecordCreate(
            video_id=video_id,
            pipeline_name="week6_video_registration",
            pipeline_config={"source": "fastapi"},
            input_artifacts={"video_url": str(payload.url)},
        )
    )

    _record_audit_event(
        AuditEventCreate(
            run_id=run.id,
            video_id=video_id,
            event_type="video_registered",
            message="Video registered through FastAPI backend.",
            metadata={
                "title": payload.title,
                "embed_base_url": str(payload.embed_base_url),
                "duration_seconds": payload.duration_seconds,
            },
        )
    )

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

    _record_audit_event(
        AuditEventCreate(
            video_id=video_id,
            event_type="audit_requested",
            message="Inquiry audit report requested.",
            metadata={"endpoint": f"/videos/{video_id}/audit"},
        )
    )

    return InquiryAuditReport(
        video_id=video_id,
        claim_count=0,
        evidence_count=0,
        claims=[],
    )


@app.get("/runs", response_model=list[RunRecordRead])
def list_runs() -> list[RunRecordRead]:
    return list(_RUN_STORE.values())


@app.get("/runs/{run_id}", response_model=RunRecordRead)
def get_run(run_id: str) -> RunRecordRead:
    run = _RUN_STORE.get(run_id)

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )

    return run


@app.get("/audit-events", response_model=list[AuditEventRead])
def list_audit_events() -> list[AuditEventRead]:
    return _AUDIT_EVENT_STORE
