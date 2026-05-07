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


def _create_claim(client: TestClient, video_id: str) -> dict:
    response = client.post(
        f"/videos/{video_id}/claims",
        json={
            "video_id": video_id,
            "verbatim_quote": "Multi-agent systems are non-stationary.",
            "claim_type": "empirical_technical",
            "verification_strategy": "literature_review",
            "char_offset_start": 10,
            "char_offset_end": 48,
            "anchor_clip": {"start": 25.0, "end": 32.0},
            "embed_url": "https://www.youtube-nocookie.com/embed/ABC123?start=25&end=32",
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


def test_video_audit_returns_empty_report_when_video_has_no_claims(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Audit Placeholder Video")

    audit_response = client.get(f"/videos/{video['id']}/audit")

    assert audit_response.status_code == 200

    data = audit_response.json()
    assert data["video_id"] == video["id"]
    assert data["claim_count"] == 0
    assert data["evidence_count"] == 0
    assert data["claims"] == []


def test_video_audit_reports_persisted_claims(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Claim Audit Report Video")
    claim = _create_claim(client, video["id"])

    audit_response = client.get(f"/videos/{video['id']}/audit")

    assert audit_response.status_code == 200

    data = audit_response.json()
    assert data["video_id"] == video["id"]
    assert data["claim_count"] == 1
    assert data["evidence_count"] == 0
    assert len(data["claims"]) == 1

    claim_summary = data["claims"][0]
    assert claim_summary["claim_id"] == claim["id"]
    assert claim_summary["has_verbatim_quote"] is True
    assert claim_summary["has_anchor_clip"] is True
    assert claim_summary["has_embed_url"] is True
    assert claim_summary["evidence_count"] == 0
    assert claim_summary["stances_present"] == []


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


def test_create_claim_for_video_persists_claim(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Claim Video")

    claim = _create_claim(client, video["id"])

    assert claim["id"].startswith("claim_")
    assert claim["video_id"] == video["id"]
    assert claim["claim_type"] == "empirical_technical"
    assert claim["anchor_clip"]["start"] == 25.0


def test_get_claim_returns_persisted_claim(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Get Claim Video")
    claim = _create_claim(client, video["id"])

    response = client.get(f"/claims/{claim['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == claim["id"]
    assert response.json()["video_id"] == video["id"]


def test_list_claims_for_video_returns_claims(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="List Claims Video")
    claim = _create_claim(client, video["id"])

    response = client.get(f"/videos/{video['id']}/claims")

    assert response.status_code == 200
    assert response.json()[0]["id"] == claim["id"]


def test_create_claim_rejects_mismatched_video_id(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Mismatch Claim Video")

    response = client.post(
        f"/videos/{video['id']}/claims",
        json={
            "video_id": "video_other",
            "verbatim_quote": "Multi-agent systems are non-stationary.",
            "claim_type": "empirical_technical",
            "verification_strategy": "literature_review",
            "char_offset_start": 10,
            "char_offset_end": 48,
            "anchor_clip": {"start": 25.0, "end": 32.0},
            "embed_url": "https://www.youtube-nocookie.com/embed/ABC123?start=25&end=32",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Claim payload video_id must match path video_id"


def test_create_claim_returns_404_for_unknown_video(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    response = client.post(
        "/videos/video_missing/claims",
        json={
            "video_id": "video_missing",
            "verbatim_quote": "Multi-agent systems are non-stationary.",
            "claim_type": "empirical_technical",
            "verification_strategy": "literature_review",
            "char_offset_start": 10,
            "char_offset_end": 48,
            "anchor_clip": {"start": 25.0, "end": 32.0},
            "embed_url": "https://www.youtube-nocookie.com/embed/ABC123?start=25&end=32",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Video not found: video_missing"


def test_get_claim_returns_404_for_unknown_claim(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    response = client.get("/claims/claim_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found: claim_missing"


def test_create_claim_records_audit_event(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Claim Audit Video")
    claim = _create_claim(client, video["id"])

    events_response = client.get("/audit-events")
    events = events_response.json()

    matching_events = [
        event
        for event in events
        if event["video_id"] == video["id"]
        and event["event_type"] == "claim_created"
        and event["metadata"]["claim_id"] == claim["id"]
    ]

    assert len(matching_events) == 1
