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
    ClaimCreate,
    ClaimRead,
    EvidenceRecordCreate,
    EvidenceRecordRead,
    InquiryAuditReport,
    PaperCreate,
    PaperRead,
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


@app.post(
    "/videos/{video_id}/claims",
    response_model=ClaimRead,
    status_code=status.HTTP_201_CREATED,
)
def create_claim_for_video(video_id: str, payload: ClaimCreate) -> ClaimRead:
    repo = get_repository()
    video = repo.get_video(video_id)

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found: {video_id}",
        )

    if payload.video_id != video_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Claim payload video_id must match path video_id",
        )

    claim = repo.create_claim(payload)

    repo.create_audit_event(
        AuditEventCreate(
            video_id=video_id,
            event_type="claim_created",
            message="Claim persisted through FastAPI backend.",
            metadata={
                "claim_id": claim.id,
                "claim_type": claim.claim_type,
                "verification_strategy": claim.verification_strategy,
                "anchor_clip_start": claim.anchor_clip.start,
                "anchor_clip_end": claim.anchor_clip.end,
            },
        )
    )

    return claim


@app.post(
    "/claims/{claim_id}/evidence",
    response_model=EvidenceRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create_evidence_for_claim(
    claim_id: str,
    payload: EvidenceRecordCreate,
) -> EvidenceRecordRead:
    repo = get_repository()
    claim = repo.get_claim(claim_id)

    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim not found: {claim_id}",
        )

    if payload.claim_id != claim_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evidence payload claim_id must match path claim_id",
        )

    evidence = repo.create_evidence_record(payload)

    repo.create_audit_event(
        AuditEventCreate(
            video_id=claim.video_id,
            event_type="evidence_created",
            message="Evidence record persisted through FastAPI backend.",
            metadata={
                "claim_id": claim_id,
                "evidence_id": evidence.id,
                "tier": evidence.tier,
                "stance": evidence.stance,
                "source_title": evidence.source_title,
                "identifier": evidence.identifier,
            },
        )
    )

    return evidence


@app.get(
    "/evidence/{evidence_id}",
    response_model=EvidenceRecordRead,
)
def get_evidence_record(evidence_id: str) -> EvidenceRecordRead:
    repo = get_repository()
    evidence = repo.get_evidence_record(evidence_id)

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence record not found: {evidence_id}",
        )

    return evidence


@app.get(
    "/claims/{claim_id}/evidence",
    response_model=list[EvidenceRecordRead],
)
def list_evidence_for_claim(claim_id: str) -> list[EvidenceRecordRead]:
    repo = get_repository()
    claim = repo.get_claim(claim_id)

    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim not found: {claim_id}",
        )

    return repo.list_evidence_records_for_claim(claim_id)


@app.get("/claims/{claim_id}", response_model=ClaimRead)
def get_claim(claim_id: str) -> ClaimRead:
    repo = get_repository()
    claim = repo.get_claim(claim_id)

    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim not found: {claim_id}",
        )

    return claim


@app.get("/videos/{video_id}/claims", response_model=list[ClaimRead])
def list_claims_for_video(video_id: str) -> list[ClaimRead]:
    repo = get_repository()
    video = repo.get_video(video_id)

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found: {video_id}",
        )

    return repo.list_claims_for_video(video_id)


@app.post(
    "/videos/{video_id}/papers",
    response_model=PaperRead,
    status_code=status.HTTP_201_CREATED,
)
def create_paper_for_video(video_id: str, payload: PaperCreate) -> PaperRead:
    repo = get_repository()
    video = repo.get_video(video_id)

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found: {video_id}",
        )

    if payload.video_id != video_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paper payload video_id must match path video_id",
        )

    paper = repo.create_paper(payload)

    repo.create_audit_event(
        AuditEventCreate(
            video_id=video_id,
            event_type="paper_created",
            message="Paper record persisted through FastAPI backend.",
            metadata={
                "paper_id": paper.id,
                "html_render_path": paper.html_render_path,
                "has_speaker_perspective": bool(
                    paper.section_speaker_perspective.strip()
                ),
                "has_evidence_review": bool(
                    paper.section_evidence_review.strip()
                ),
                "has_further_reading": bool(
                    paper.section_further_reading.strip()
                ),
            },
        )
    )

    return paper


@app.get("/papers/{paper_id}", response_model=PaperRead)
def get_paper(paper_id: str) -> PaperRead:
    repo = get_repository()
    paper = repo.get_paper(paper_id)

    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper not found: {paper_id}",
        )

    return paper


@app.get("/videos/{video_id}/papers", response_model=list[PaperRead])
def list_papers_for_video(video_id: str) -> list[PaperRead]:
    repo = get_repository()
    video = repo.get_video(video_id)

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found: {video_id}",
        )

    return repo.list_papers_for_video(video_id)


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

    return repo.build_video_audit_report(video_id)


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
