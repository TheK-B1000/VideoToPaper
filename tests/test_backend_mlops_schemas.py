from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.backend.mlops_schemas import (
    AuditEventCreate,
    AuditEventRead,
    RunRecordCreate,
    RunRecordRead,
    new_audit_event_id,
    new_run_id,
)


def test_new_run_id_has_expected_prefix():
    run_id = new_run_id()

    assert run_id.startswith("run_")
    assert len(run_id) > len("run_")


def test_new_audit_event_id_has_expected_prefix():
    audit_id = new_audit_event_id()

    assert audit_id.startswith("audit_")
    assert len(audit_id) > len("audit_")


def test_run_record_create_defaults_to_week6_backend_pipeline():
    run = RunRecordCreate(video_id="video_001")

    assert run.video_id == "video_001"
    assert run.pipeline_name == "week6_backend"
    assert run.pipeline_config == {}
    assert run.input_artifacts == {}


def test_run_record_read_tracks_status_and_artifacts():
    started_at = datetime.now(timezone.utc)

    run = RunRecordRead(
        id="run_001",
        video_id="video_001",
        pipeline_name="week6_backend",
        status="running",
        pipeline_config={"source": "api"},
        input_artifacts={"video": "video_001"},
        output_artifacts={},
        started_at=started_at,
    )

    assert run.status == "running"
    assert run.pipeline_config["source"] == "api"
    assert run.input_artifacts["video"] == "video_001"
    assert run.finished_at is None


def test_run_record_rejects_invalid_status():
    with pytest.raises(ValidationError):
        RunRecordRead(
            id="run_001",
            video_id="video_001",
            pipeline_name="week6_backend",
            status="paused",
            started_at=datetime.now(timezone.utc),
        )


def test_audit_event_create_requires_message():
    event = AuditEventCreate(
        run_id="run_001",
        video_id="video_001",
        event_type="video_registered",
        message="Registered video for inquiry backend.",
        metadata={"title": "Example Video"},
    )

    assert event.event_type == "video_registered"
    assert event.metadata["title"] == "Example Video"


def test_audit_event_create_rejects_blank_message():
    with pytest.raises(ValidationError):
        AuditEventCreate(
            run_id="run_001",
            video_id="video_001",
            event_type="video_registered",
            message="",
        )


def test_audit_event_read_tracks_created_at():
    created_at = datetime.now(timezone.utc)

    event = AuditEventRead(
        id="audit_001",
        run_id="run_001",
        video_id="video_001",
        event_type="audit_requested",
        message="Audit report requested.",
        metadata={"endpoint": "/videos/video_001/audit"},
        created_at=created_at,
    )

    assert event.created_at == created_at
    assert event.metadata["endpoint"] == "/videos/video_001/audit"
