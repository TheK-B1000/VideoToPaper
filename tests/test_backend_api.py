from fastapi.testclient import TestClient

from src.backend.api import app


client = TestClient(app)


def test_health_check_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_video_returns_created_video():
    response = client.post(
        "/videos",
        json={
            "url": "https://www.youtube.com/watch?v=ABC123",
            "title": "Example Inquiry Video",
            "embed_base_url": "https://www.youtube-nocookie.com/embed/ABC123",
            "duration_seconds": 180.0,
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["id"].startswith("video_")
    assert data["title"] == "Example Inquiry Video"
    assert data["duration_seconds"] == 180.0
    assert "youtube-nocookie.com/embed/ABC123" in data["embed_base_url"]


def test_registered_video_can_be_retrieved():
    create_response = client.post(
        "/videos",
        json={
            "url": "https://www.youtube.com/watch?v=XYZ789",
            "title": "Retrievable Video",
            "embed_base_url": "https://www.youtube-nocookie.com/embed/XYZ789",
            "duration_seconds": 240.0,
        },
    )

    video_id = create_response.json()["id"]

    get_response = client.get(f"/videos/{video_id}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == video_id
    assert get_response.json()["title"] == "Retrievable Video"


def test_get_video_returns_404_for_unknown_video():
    response = client.get("/videos/video_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Video not found: video_missing"


def test_video_audit_placeholder_returns_empty_report():
    create_response = client.post(
        "/videos",
        json={
            "url": "https://www.youtube.com/watch?v=AUDIT123",
            "title": "Audit Placeholder Video",
            "embed_base_url": "https://www.youtube-nocookie.com/embed/AUDIT123",
            "duration_seconds": 300.0,
        },
    )

    video_id = create_response.json()["id"]

    audit_response = client.get(f"/videos/{video_id}/audit")

    assert audit_response.status_code == 200

    data = audit_response.json()
    assert data["video_id"] == video_id
    assert data["claim_count"] == 0
    assert data["evidence_count"] == 0
    assert data["claims"] == []


def test_video_audit_returns_404_for_unknown_video():
    response = client.get("/videos/video_missing/audit")

    assert response.status_code == 404
    assert response.json()["detail"] == "Video not found: video_missing"


def test_register_video_rejects_non_privacy_embed_url():
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
