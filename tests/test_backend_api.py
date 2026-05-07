from pathlib import Path

from fastapi.testclient import TestClient

from src.backend import api
from src.backend.api import app
from src.backend.db import initialize_sqlite_database
from src.backend.repository import BackendRepository


def _make_test_client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "api_test.db"

    initialize_sqlite_database(
        db_path=db_path,
        schema_path=Path("src/backend/schema.sql"),
    )

    def _test_repository() -> BackendRepository:
        return BackendRepository(db_path=db_path)

    monkeypatch.setattr(api, "get_repository", _test_repository)

    return TestClient(app)


def _create_video(client: TestClient, title: str = "Example Inquiry Video") -> dict:
    response = client.post(
        "/videos",
        json={
            "url": "https://www.youtube.com/watch?v=ABC123",
            "title": title,
            "embed_base_url": "https://www.youtube-nocookie.com/embed/ABC123",
            "duration_seconds": 180.0,
        },
    )

    assert response.status_code == 201
    return response.json()


def test_health_check_returns_ok(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_video_returns_created_video(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    data = _create_video(client)

    assert data["id"].startswith("video_")
    assert data["title"] == "Example Inquiry Video"
    assert data["duration_seconds"] == 180.0
    assert "youtube-nocookie.com/embed/ABC123" in data["embed_base_url"]


def test_registered_video_can_be_retrieved(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Retrievable Video")

    get_response = client.get(f"/videos/{video['id']}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == video["id"]
    assert get_response.json()["title"] == "Retrievable Video"


def test_get_video_returns_404_for_unknown_video(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    response = client.get("/videos/video_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Video not found: video_missing"


def test_video_audit_placeholder_returns_empty_report(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Audit Placeholder Video")

    audit_response = client.get(f"/videos/{video['id']}/audit")

    assert audit_response.status_code == 200

    data = audit_response.json()
    assert data["video_id"] == video["id"]
    assert data["claim_count"] == 0
    assert data["evidence_count"] == 0
    assert data["claims"] == []


def test_video_audit_returns_404_for_unknown_video(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    response = client.get("/videos/video_missing/audit")

    assert response.status_code == 404
    assert response.json()["detail"] == "Video not found: video_missing"


def test_register_video_rejects_non_privacy_embed_url(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    response = client.post(
        "/videos",
        json={
            "url": "https://www.youtube.com/watch?v=BAD123",
            "title": "Bad Embed Video",
            "embed_base_url": "https://www.youtube.com/watch?v=BAD123",
            "duration_seconds": 100.0,
        },
    )

    assert response.status_code == 422


def test_register_video_creates_persistent_mlops_run_record(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="MLOps Run Video")

    response = client.get("/runs")

    assert response.status_code == 200

    runs = response.json()
    matching_runs = [
        run
        for run in runs
        if run["video_id"] == video["id"]
        and run["pipeline_name"] == "week6_video_registration"
    ]

    assert len(matching_runs) == 1
    assert matching_runs[0]["status"] == "completed"
    assert matching_runs[0]["pipeline_config"] == {"source": "fastapi"}
    assert matching_runs[0]["input_artifacts"]["video_url"].startswith(
        "https://www.youtube.com/watch"
    )


def test_get_run_returns_single_persistent_mlops_run_record(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Single Run Lookup Video")

    runs_response = client.get("/runs")
    runs = runs_response.json()

    run = next(
        item
        for item in runs
        if item["video_id"] == video["id"]
        and item["pipeline_name"] == "week6_video_registration"
    )

    get_response = client.get(f"/runs/{run['id']}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == run["id"]
    assert get_response.json()["video_id"] == video["id"]


def test_get_run_returns_404_for_unknown_run(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    response = client.get("/runs/run_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Run not found: run_missing"


def test_register_video_creates_persistent_audit_event(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Audit Event Video")

    response = client.get("/audit-events")

    assert response.status_code == 200

    events = response.json()
    matching_events = [
        event
        for event in events
        if event["video_id"] == video["id"]
        and event["event_type"] == "video_registered"
    ]

    assert len(matching_events) == 1
    assert matching_events[0]["message"] == "Video registered through FastAPI backend."
    assert matching_events[0]["metadata"]["title"] == "Audit Event Video"


def test_audit_endpoint_records_persistent_audit_requested_event(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Audit Requested Video")

    audit_response = client.get(f"/videos/{video['id']}/audit")
    assert audit_response.status_code == 200

    events_response = client.get("/audit-events")
    events = events_response.json()

    matching_events = [
        event
        for event in events
        if event["video_id"] == video["id"]
        and event["event_type"] == "audit_requested"
    ]

    assert len(matching_events) == 1
    assert matching_events[0]["metadata"]["endpoint"] == f"/videos/{video['id']}/audit"
