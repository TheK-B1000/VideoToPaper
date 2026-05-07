from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.backend.db import connect_sqlite
from src.backend.mlops_schemas import (
    AuditEventCreate,
    AuditEventRead,
    RunRecordCreate,
    RunRecordRead,
)
from src.backend.schemas import (
    ClaimAuditSummary,
    ClaimCreate,
    ClaimRead,
    EvidenceRecordCreate,
    EvidenceRecordRead,
    InquiryAuditReport,
    VideoCreate,
    VideoRead,
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: Dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True)


def _json_loads(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}

    return json.loads(value)


class BackendRepository:
    """
    SQLite repository for Week 6 backend persistence.

    This keeps FastAPI thin and makes persistence testable before the API
    is fully wired to Neon/Postgres.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def create_video(self, payload: VideoCreate) -> VideoRead:
        video = VideoRead(
            id=_new_id("video"),
            url=payload.url,
            title=payload.title,
            embed_base_url=payload.embed_base_url,
            duration_seconds=payload.duration_seconds,
            speaker_id=None,
        )

        with connect_sqlite(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO videos (
                    id,
                    url,
                    title,
                    embed_base_url,
                    duration_seconds,
                    speaker_id
                )
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    video.id,
                    str(video.url),
                    video.title,
                    str(video.embed_base_url),
                    video.duration_seconds,
                    video.speaker_id,
                ),
            )

        return video

    def get_video(self, video_id: str) -> Optional[VideoRead]:
        with connect_sqlite(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    url,
                    title,
                    embed_base_url,
                    duration_seconds,
                    speaker_id
                FROM videos
                WHERE id = ?;
                """,
                (video_id,),
            ).fetchone()

        if row is None:
            return None

        return VideoRead(
            id=row["id"],
            url=row["url"],
            title=row["title"],
            embed_base_url=row["embed_base_url"],
            duration_seconds=row["duration_seconds"],
            speaker_id=row["speaker_id"],
        )

    def create_run_record(self, payload: RunRecordCreate) -> RunRecordRead:
        started_at = _now_iso()
        finished_at = _now_iso()

        run = RunRecordRead(
            id=_new_id("run"),
            video_id=payload.video_id,
            pipeline_name=payload.pipeline_name,
            status="completed",
            pipeline_config=payload.pipeline_config,
            input_artifacts=payload.input_artifacts,
            output_artifacts={},
            started_at=datetime.fromisoformat(started_at),
            finished_at=datetime.fromisoformat(finished_at),
            error_message=None,
        )

        with connect_sqlite(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO runs (
                    id,
                    video_id,
                    pipeline_name,
                    status,
                    pipeline_config_json,
                    input_artifacts_json,
                    output_artifacts_json,
                    started_at,
                    finished_at,
                    error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    run.id,
                    run.video_id,
                    run.pipeline_name,
                    run.status,
                    _json_dumps(run.pipeline_config),
                    _json_dumps(run.input_artifacts),
                    _json_dumps(run.output_artifacts),
                    run.started_at.isoformat(),
                    run.finished_at.isoformat() if run.finished_at else None,
                    run.error_message,
                ),
            )

        return run

    def get_run(self, run_id: str) -> Optional[RunRecordRead]:
        with connect_sqlite(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    video_id,
                    pipeline_name,
                    status,
                    pipeline_config_json,
                    input_artifacts_json,
                    output_artifacts_json,
                    started_at,
                    finished_at,
                    error_message
                FROM runs
                WHERE id = ?;
                """,
                (run_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_run(row)

    def list_runs(self) -> List[RunRecordRead]:
        with connect_sqlite(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    video_id,
                    pipeline_name,
                    status,
                    pipeline_config_json,
                    input_artifacts_json,
                    output_artifacts_json,
                    started_at,
                    finished_at,
                    error_message
                FROM runs
                ORDER BY started_at DESC;
                """
            ).fetchall()

        return [self._row_to_run(row) for row in rows]

    def create_audit_event(self, payload: AuditEventCreate) -> AuditEventRead:
        created_at = _now_iso()

        event = AuditEventRead(
            id=_new_id("audit"),
            run_id=payload.run_id,
            video_id=payload.video_id,
            event_type=payload.event_type,
            message=payload.message,
            metadata=payload.metadata,
            created_at=datetime.fromisoformat(created_at),
        )

        with connect_sqlite(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_events (
                    id,
                    run_id,
                    video_id,
                    event_type,
                    message,
                    metadata_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event.id,
                    event.run_id,
                    event.video_id,
                    event.event_type,
                    event.message,
                    _json_dumps(event.metadata),
                    event.created_at.isoformat(),
                ),
            )

        return event

    def list_audit_events(self) -> List[AuditEventRead]:
        with connect_sqlite(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    run_id,
                    video_id,
                    event_type,
                    message,
                    metadata_json,
                    created_at
                FROM audit_events
                ORDER BY created_at DESC;
                """
            ).fetchall()

        return [self._row_to_audit_event(row) for row in rows]

    def list_audit_events_for_video(self, video_id: str) -> List[AuditEventRead]:
        with connect_sqlite(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    run_id,
                    video_id,
                    event_type,
                    message,
                    metadata_json,
                    created_at
                FROM audit_events
                WHERE video_id = ?
                ORDER BY created_at DESC;
                """,
                (video_id,),
            ).fetchall()

        return [self._row_to_audit_event(row) for row in rows]

    def create_claim(self, payload: ClaimCreate) -> ClaimRead:
        claim = ClaimRead(
            id=_new_id("claim"),
            video_id=payload.video_id,
            verbatim_quote=payload.verbatim_quote,
            claim_type=payload.claim_type,
            verification_strategy=payload.verification_strategy,
            char_offset_start=payload.char_offset_start,
            char_offset_end=payload.char_offset_end,
            anchor_clip=payload.anchor_clip,
            embed_url=payload.embed_url,
        )

        with connect_sqlite(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO claims (
                    id,
                    video_id,
                    verbatim_quote,
                    claim_type,
                    verification_strategy,
                    char_offset_start,
                    char_offset_end,
                    anchor_clip_start,
                    anchor_clip_end,
                    embed_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    claim.id,
                    claim.video_id,
                    claim.verbatim_quote,
                    claim.claim_type,
                    claim.verification_strategy,
                    claim.char_offset_start,
                    claim.char_offset_end,
                    claim.anchor_clip.start,
                    claim.anchor_clip.end,
                    str(claim.embed_url),
                ),
            )

        return claim

    def get_claim(self, claim_id: str) -> Optional[ClaimRead]:
        with connect_sqlite(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    video_id,
                    verbatim_quote,
                    claim_type,
                    verification_strategy,
                    char_offset_start,
                    char_offset_end,
                    anchor_clip_start,
                    anchor_clip_end,
                    embed_url
                FROM claims
                WHERE id = ?;
                """,
                (claim_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_claim(row)

    def list_claims_for_video(self, video_id: str) -> List[ClaimRead]:
        with connect_sqlite(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    video_id,
                    verbatim_quote,
                    claim_type,
                    verification_strategy,
                    char_offset_start,
                    char_offset_end,
                    anchor_clip_start,
                    anchor_clip_end,
                    embed_url
                FROM claims
                WHERE video_id = ?
                ORDER BY char_offset_start ASC;
                """,
                (video_id,),
            ).fetchall()

        return [self._row_to_claim(row) for row in rows]

    def build_video_audit_report(self, video_id: str) -> InquiryAuditReport:
        claims = self.list_claims_for_video(video_id)

        claim_summaries: List[ClaimAuditSummary] = []

        with connect_sqlite(self.db_path) as conn:
            for claim in claims:
                evidence_rows = conn.execute(
                    """
                    SELECT stance
                    FROM evidence_records
                    WHERE claim_id = ?;
                    """,
                    (claim.id,),
                ).fetchall()

                stances_present = sorted({row["stance"] for row in evidence_rows})

                claim_summaries.append(
                    ClaimAuditSummary(
                        claim_id=claim.id,
                        has_verbatim_quote=bool(claim.verbatim_quote.strip()),
                        has_anchor_clip=(
                            claim.anchor_clip.start >= 0
                            and claim.anchor_clip.end > claim.anchor_clip.start
                        ),
                        has_embed_url=bool(str(claim.embed_url).strip()),
                        evidence_count=len(evidence_rows),
                        stances_present=stances_present,
                    )
                )

        total_evidence_count = sum(
            summary.evidence_count for summary in claim_summaries
        )

        return InquiryAuditReport(
            video_id=video_id,
            claim_count=len(claims),
            evidence_count=total_evidence_count,
            claims=claim_summaries,
        )

    def create_evidence_record(
        self,
        payload: EvidenceRecordCreate,
    ) -> EvidenceRecordRead:
        evidence = EvidenceRecordRead(
            id=_new_id("evidence"),
            claim_id=payload.claim_id,
            tier=payload.tier,
            stance=payload.stance,
            source_title=payload.source_title,
            source_url=payload.source_url,
            identifier=payload.identifier,
            abstract_or_summary=payload.abstract_or_summary,
            key_finding=payload.key_finding,
        )

        with connect_sqlite(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO evidence_records (
                    id,
                    claim_id,
                    tier,
                    stance,
                    source_title,
                    source_url,
                    identifier,
                    abstract_or_summary,
                    key_finding
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    evidence.id,
                    evidence.claim_id,
                    evidence.tier,
                    evidence.stance,
                    evidence.source_title,
                    str(evidence.source_url) if evidence.source_url else None,
                    evidence.identifier,
                    evidence.abstract_or_summary,
                    evidence.key_finding,
                ),
            )

        return evidence

    def get_evidence_record(
        self,
        evidence_id: str,
    ) -> Optional[EvidenceRecordRead]:
        with connect_sqlite(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    claim_id,
                    tier,
                    stance,
                    source_title,
                    source_url,
                    identifier,
                    abstract_or_summary,
                    key_finding
                FROM evidence_records
                WHERE id = ?;
                """,
                (evidence_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_evidence_record(row)

    def list_evidence_records_for_claim(
        self,
        claim_id: str,
    ) -> List[EvidenceRecordRead]:
        with connect_sqlite(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    claim_id,
                    tier,
                    stance,
                    source_title,
                    source_url,
                    identifier,
                    abstract_or_summary,
                    key_finding
                FROM evidence_records
                WHERE claim_id = ?
                ORDER BY tier ASC, source_title ASC;
                """,
                (claim_id,),
            ).fetchall()

        return [self._row_to_evidence_record(row) for row in rows]

    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> RunRecordRead:
        return RunRecordRead(
            id=row["id"],
            video_id=row["video_id"],
            pipeline_name=row["pipeline_name"],
            status=row["status"],
            pipeline_config=_json_loads(row["pipeline_config_json"]),
            input_artifacts=_json_loads(row["input_artifacts_json"]),
            output_artifacts=_json_loads(row["output_artifacts_json"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=(
                datetime.fromisoformat(row["finished_at"])
                if row["finished_at"]
                else None
            ),
            error_message=row["error_message"],
        )

    @staticmethod
    def _row_to_claim(row: sqlite3.Row) -> ClaimRead:
        return ClaimRead(
            id=row["id"],
            video_id=row["video_id"],
            verbatim_quote=row["verbatim_quote"],
            claim_type=row["claim_type"],
            verification_strategy=row["verification_strategy"],
            char_offset_start=row["char_offset_start"],
            char_offset_end=row["char_offset_end"],
            anchor_clip={
                "start": row["anchor_clip_start"],
                "end": row["anchor_clip_end"],
            },
            embed_url=row["embed_url"],
        )

    @staticmethod
    def _row_to_evidence_record(row: sqlite3.Row) -> EvidenceRecordRead:
        return EvidenceRecordRead(
            id=row["id"],
            claim_id=row["claim_id"],
            tier=row["tier"],
            stance=row["stance"],
            source_title=row["source_title"],
            source_url=row["source_url"],
            identifier=row["identifier"],
            abstract_or_summary=row["abstract_or_summary"],
            key_finding=row["key_finding"],
        )

    @staticmethod
    def _row_to_audit_event(row: sqlite3.Row) -> AuditEventRead:
        return AuditEventRead(
            id=row["id"],
            run_id=row["run_id"],
            video_id=row["video_id"],
            event_type=row["event_type"],
            message=row["message"],
            metadata=_json_loads(row["metadata_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
