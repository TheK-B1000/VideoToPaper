from pathlib import Path

from src.backend.db import initialize_sqlite_database
from src.backend.mlops_schemas import AuditEventCreate, RunRecordCreate
from src.backend.repository import BackendRepository
from src.backend.schemas import VideoCreate


def _repo(tmp_path) -> BackendRepository:
    db_path = tmp_path / "repository.db"
    initialize_sqlite_database(
        db_path=db_path,
        schema_path=Path("src/backend/schema.sql"),
    )
    return BackendRepository(db_path=db_path)


def _video_payload(title: str = "Repository Video") -> VideoCreate:
    return VideoCreate(
        url="https://www.youtube.com/watch?v=ABC123",
        title=title,
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
        duration_seconds=180.0,
    )


def test_repository_creates_and_reads_video(tmp_path):
    repo = _repo(tmp_path)

    video = repo.create_video(_video_payload())

    saved = repo.get_video(video.id)

    assert saved is not None
    assert saved.id == video.id
    assert saved.title == "Repository Video"
    assert str(saved.embed_base_url).startswith(
        "https://www.youtube-nocookie.com/embed/ABC123"
    )


def test_repository_returns_none_for_missing_video(tmp_path):
    repo = _repo(tmp_path)

    assert repo.get_video("video_missing") is None


def test_repository_creates_and_reads_run_record(tmp_path):
    repo = _repo(tmp_path)
    video = repo.create_video(_video_payload())

    run = repo.create_run_record(
        RunRecordCreate(
            video_id=video.id,
            pipeline_name="week6_video_registration",
            pipeline_config={"source": "repository-test"},
            input_artifacts={"video_url": "https://www.youtube.com/watch?v=ABC123"},
        )
    )

    saved = repo.get_run(run.id)

    assert saved is not None
    assert saved.id == run.id
    assert saved.video_id == video.id
    assert saved.status == "completed"
    assert saved.pipeline_config == {"source": "repository-test"}
    assert saved.input_artifacts["video_url"].startswith("https://www.youtube.com")


def test_repository_lists_runs(tmp_path):
    repo = _repo(tmp_path)
    video = repo.create_video(_video_payload())

    repo.create_run_record(
        RunRecordCreate(
            video_id=video.id,
            pipeline_name="week6_video_registration",
        )
    )

    runs = repo.list_runs()

    assert len(runs) == 1
    assert runs[0].video_id == video.id
    assert runs[0].pipeline_name == "week6_video_registration"


def test_repository_returns_none_for_missing_run(tmp_path):
    repo = _repo(tmp_path)

    assert repo.get_run("run_missing") is None


def test_repository_creates_and_lists_audit_events(tmp_path):
    repo = _repo(tmp_path)
    video = repo.create_video(_video_payload())
    run = repo.create_run_record(
        RunRecordCreate(
            video_id=video.id,
            pipeline_name="week6_video_registration",
        )
    )

    event = repo.create_audit_event(
        AuditEventCreate(
            run_id=run.id,
            video_id=video.id,
            event_type="video_registered",
            message="Video registered through repository.",
            metadata={"title": video.title},
        )
    )

    events = repo.list_audit_events()

    assert len(events) == 1
    assert events[0].id == event.id
    assert events[0].event_type == "video_registered"
    assert events[0].metadata == {"title": video.title}


def test_repository_lists_audit_events_for_video(tmp_path):
    repo = _repo(tmp_path)
    video = repo.create_video(_video_payload(title="Audit Video"))

    repo.create_audit_event(
        AuditEventCreate(
            video_id=video.id,
            event_type="audit_requested",
            message="Audit report requested.",
            metadata={"endpoint": f"/videos/{video.id}/audit"},
        )
    )

    events = repo.list_audit_events_for_video(video.id)

    assert len(events) == 1
    assert events[0].video_id == video.id
    assert events[0].event_type == "audit_requested"
    assert events[0].metadata["endpoint"] == f"/videos/{video.id}/audit"


def test_repository_returns_empty_audit_events_for_unknown_video(tmp_path):
    repo = _repo(tmp_path)

    assert repo.list_audit_events_for_video("video_missing") == []
