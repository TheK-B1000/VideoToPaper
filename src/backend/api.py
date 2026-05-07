from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, status

from src.backend.db import initialize_sqlite_database
from src.backend.mlops_schemas import (
    AuditEventCreate,
    RunRecordCreate,
    RunRecordRead,
)
from src.backend.repository import BackendRepository
from src.backend.schemas import (
    InquiryAuditReport,
    VideoCreate,
    VideoRead,
)

DEFAULT_API_DB_PATH = Path("data/inquiry_engine.db")

app = FastAPI(
    title="Inquiry Engine API",
    description="Backend service for registering videos and exposing inquiry audit data.",
    version="0.1.0",
)


def get_repository() -> BackendRepository:
    """
    Return the backend repository.

    For Week 6, this uses SQLite persistence.
    Later, this can switch based on DATABASE_URL to support Neon/Postgres.
    """
    initialize_sqlite_database(db_path=DEFAULT_API_DB_PATH)
    return BackendRepository(db_path=DEFAULT_API_DB_PATH)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/videos",
    response_model=VideoRead,
    status_code=status.HTTP_201_CREATED,
)
def register_video(payload: VideoCreate) -> VideoRead:
    repo = get_repository()

    video = repo.create_video(payload)

    run = repo.create_run_record(
        RunRecordCreate(
            video_id=video.id,
            pipeline_name="week6_video_registration",
            pipeline_config={"source": "fastapi"},
            input_artifacts={"video_url": str(payload.url)},
        )
    )

    repo.create_audit_event(
        AuditEventCreate(
            run_id=run.id,
            video_id=video.id,
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
    repo = get_repository()
    video = repo.get_video(video_id)

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found: {video_id}",
        )

    return video


@app.get("/videos/{video_id}/audit", response_model=InquiryAuditReport)
def get_video_audit(video_id: str) -> InquiryAuditReport:
    repo = get_repository()
    video = repo.get_video(video_id)

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found: {video_id}",
        )

    repo.create_audit_event(
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
    repo = get_repository()
    return repo.list_runs()


@app.get("/runs/{run_id}", response_model=RunRecordRead)
def get_run(run_id: str) -> RunRecordRead:
    repo = get_repository()
    run = repo.get_run(run_id)

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )

    return run


@app.get("/audit-events")
def list_audit_events():
    repo = get_repository()
    return repo.list_audit_events()
