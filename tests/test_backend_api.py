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


def _create_evidence(client: TestClient, claim_id: str) -> dict:
    response = client.post(
        f"/claims/{claim_id}/evidence",
        json={
            "claim_id": claim_id,
            "tier": 1,
            "stance": "supports",
            "source_title": "A Survey of Multi-Agent Reinforcement Learning",
            "source_url": "https://example.com/paper",
            "identifier": "doi:10.0000/example",
            "abstract_or_summary": "A survey discussing core MARL challenges.",
            "key_finding": "The paper discusses non-stationarity as a MARL challenge.",
        },
    )

    assert response.status_code == 201
    return response.json()


def _create_paper(client: TestClient, video_id: str) -> dict:
    response = client.post(
        f"/videos/{video_id}/papers",
        json={
            "video_id": video_id,
            "section_speaker_perspective": "The speaker argues that MARL needs careful handling of non-stationarity.",
            "section_evidence_review": "The evidence review discusses support and qualifications from the literature.",
            "section_further_reading": "Recommended sources include surveys and foundational MARL papers.",
            "html_render_path": "data/outputs/papers/video_001.html",
        },
    )

    assert response.status_code == 201
    return response.json()


def test_health_check_returns_ok(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_videos_returns_registered_videos(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    first = _create_video(client, title="First Library Video")
    second = _create_video(client, title="Second Library Video")

    response = client.get("/videos")

    assert response.status_code == 200

    videos = response.json()
    video_ids = {video["id"] for video in videos}

    assert first["id"] in video_ids
    assert second["id"] in video_ids
    assert len(videos) == 2


def test_list_videos_returns_empty_list_when_none_exist(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    response = client.get("/videos")

    assert response.status_code == 200
    assert response.json() == []


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


def test_create_evidence_for_claim_persists_evidence_record(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Evidence Video")
    claim = _create_claim(client, video["id"])

    evidence = _create_evidence(client, claim["id"])

    assert evidence["id"].startswith("evidence_")
    assert evidence["claim_id"] == claim["id"]
    assert evidence["tier"] == 1
    assert evidence["stance"] == "supports"


def test_get_evidence_record_returns_persisted_record(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Get Evidence Video")
    claim = _create_claim(client, video["id"])
    evidence = _create_evidence(client, claim["id"])

    response = client.get(f"/evidence/{evidence['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == evidence["id"]
    assert response.json()["claim_id"] == claim["id"]


def test_list_evidence_for_claim_returns_records(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="List Evidence Video")
    claim = _create_claim(client, video["id"])
    evidence = _create_evidence(client, claim["id"])

    response = client.get(f"/claims/{claim['id']}/evidence")

    assert response.status_code == 200
    assert response.json()[0]["id"] == evidence["id"]


def test_create_evidence_rejects_mismatched_claim_id(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Mismatch Evidence Video")
    claim = _create_claim(client, video["id"])

    response = client.post(
        f"/claims/{claim['id']}/evidence",
        json={
            "claim_id": "claim_other",
            "tier": 1,
            "stance": "supports",
            "source_title": "Bad Evidence Claim Link",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Evidence payload claim_id must match path claim_id"


def test_create_evidence_returns_404_for_unknown_claim(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    response = client.post(
        "/claims/claim_missing/evidence",
        json={
            "claim_id": "claim_missing",
            "tier": 1,
            "stance": "supports",
            "source_title": "Missing Claim Evidence",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found: claim_missing"


def test_get_evidence_returns_404_for_unknown_evidence(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    response = client.get("/evidence/evidence_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Evidence record not found: evidence_missing"


def test_video_audit_reports_evidence_count_and_stances(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Evidence Audit Video")
    claim = _create_claim(client, video["id"])
    _create_evidence(client, claim["id"])

    audit_response = client.get(f"/videos/{video['id']}/audit")

    assert audit_response.status_code == 200

    data = audit_response.json()
    assert data["claim_count"] == 1
    assert data["evidence_count"] == 1
    assert data["claims"][0]["evidence_count"] == 1
    assert data["claims"][0]["stances_present"] == ["supports"]


def test_create_evidence_records_audit_event(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Evidence Audit Event Video")
    claim = _create_claim(client, video["id"])
    evidence = _create_evidence(client, claim["id"])

    events_response = client.get("/audit-events")
    events = events_response.json()

    matching_events = [
        event
        for event in events
        if event["video_id"] == video["id"]
        and event["event_type"] == "evidence_created"
        and event["metadata"]["evidence_id"] == evidence["id"]
    ]

    assert len(matching_events) == 1


def test_create_paper_for_video_persists_paper(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Paper Video")

    paper = _create_paper(client, video["id"])

    assert paper["id"].startswith("paper_")
    assert paper["video_id"] == video["id"]
    assert "MARL" in paper["section_speaker_perspective"]
    assert paper["html_render_path"] == "data/outputs/papers/video_001.html"


def test_get_paper_returns_persisted_paper(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Get Paper Video")
    paper = _create_paper(client, video["id"])

    response = client.get(f"/papers/{paper['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == paper["id"]
    assert response.json()["video_id"] == video["id"]


def test_list_papers_for_video_returns_records(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="List Papers Video")
    paper = _create_paper(client, video["id"])

    response = client.get(f"/videos/{video['id']}/papers")

    assert response.status_code == 200
    assert response.json()[0]["id"] == paper["id"]


def test_create_paper_rejects_mismatched_video_id(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Mismatch Paper Video")

    response = client.post(
        f"/videos/{video['id']}/papers",
        json={
            "video_id": "video_other",
            "section_speaker_perspective": "Bad video link.",
            "section_evidence_review": "",
            "section_further_reading": "",
            "html_render_path": "data/outputs/papers/bad.html",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Paper payload video_id must match path video_id"


def test_create_paper_returns_404_for_unknown_video(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    response = client.post(
        "/videos/video_missing/papers",
        json={
            "video_id": "video_missing",
            "section_speaker_perspective": "Missing video.",
            "section_evidence_review": "",
            "section_further_reading": "",
            "html_render_path": "data/outputs/papers/missing.html",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Video not found: video_missing"


def test_get_paper_returns_404_for_unknown_paper(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    response = client.get("/papers/paper_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Paper not found: paper_missing"


def test_create_paper_records_audit_event(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Paper Audit Event Video")
    paper = _create_paper(client, video["id"])

    events_response = client.get("/audit-events")
    events = events_response.json()

    matching_events = [
        event
        for event in events
        if event["video_id"] == video["id"]
        and event["event_type"] == "paper_created"
        and event["metadata"]["paper_id"] == paper["id"]
    ]

    assert len(matching_events) == 1
    assert matching_events[0]["metadata"]["has_speaker_perspective"] is True


def test_video_summary_reports_backend_counts(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)
    video = _create_video(client, title="Summary API Video")
    claim = _create_claim(client, video["id"])
    _create_evidence(client, claim["id"])
    _create_paper(client, video["id"])

    response = client.get(f"/videos/{video['id']}/summary")

    assert response.status_code == 200

    data = response.json()
    assert data["video_id"] == video["id"]
    assert data["title"] == "Summary API Video"
    assert data["claim_count"] == 1
    assert data["evidence_count"] == 1
    assert data["paper_count"] == 1
    assert data["run_count"] == 1
    assert data["audit_event_count"] >= 4
    assert data["has_generated_paper"] is True
    assert data["has_evidence"] is True


def test_video_summary_returns_404_for_unknown_video(tmp_path, monkeypatch):
    client = _make_test_client(tmp_path, monkeypatch)

    response = client.get("/videos/video_missing/summary")

    assert response.status_code == 404
    assert response.json()["detail"] == "Video not found: video_missing"
