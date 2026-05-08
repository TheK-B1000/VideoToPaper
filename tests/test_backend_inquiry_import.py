import json
from pathlib import Path

import pytest

from src.frontend.backend_client import BackendResponse
from src.frontend.backend_inquiry_import import (
    backend_response_to_inquiry_import_result,
    import_backend_inquiry,
    normalize_backend_inquiry_manifest,
    save_inquiry_manifest,
)


class FakeBackendClient:
    def __init__(self, response: BackendResponse):
        self.response = response
        self.requested_inquiry_id = None

    def get_inquiry_manifest(self, inquiry_id: str):
        self.requested_inquiry_id = inquiry_id
        return self.response


def test_normalize_backend_inquiry_manifest_accepts_native_shape():
    payload = {
        "inquiry_id": "inquiry_001",
        "title": "Native Inquiry",
        "youtube_url": "https://www.youtube.com/watch?v=ABC123xyz_9",
        "status": "completed",
        "created_at": "2026-05-08T12:00:00+00:00",
        "paper_path": "data/inquiries/inquiry_001/paper.html",
        "audit_report_path": "data/inquiries/inquiry_001/audit.json",
        "parameters": {"retrieval_depth": 3},
    }

    manifest = normalize_backend_inquiry_manifest(
        payload,
        fallback_inquiry_id="fallback",
    )

    assert manifest["inquiry_id"] == "inquiry_001"
    assert manifest["title"] == "Native Inquiry"
    assert manifest["youtube_url"] == "https://www.youtube.com/watch?v=ABC123xyz_9"
    assert manifest["paper_path"] == "data/inquiries/inquiry_001/paper.html"
    assert manifest["audit_report_path"] == "data/inquiries/inquiry_001/audit.json"
    assert manifest["parameters"]["retrieval_depth"] == 3


def test_normalize_backend_inquiry_manifest_accepts_wrapped_shape():
    payload = {
        "inquiry": {
            "inquiry_id": "inquiry_002",
            "title": "Wrapped Inquiry",
            "youtube_url": "https://youtu.be/ABC123xyz_9",
            "status": "completed",
        }
    }

    manifest = normalize_backend_inquiry_manifest(
        payload,
        fallback_inquiry_id="fallback",
    )

    assert manifest["inquiry_id"] == "inquiry_002"
    assert manifest["title"] == "Wrapped Inquiry"
    assert manifest["youtube_url"] == "https://youtu.be/ABC123xyz_9"


def test_normalize_backend_inquiry_manifest_accepts_minimal_shape():
    payload = {
        "id": "inquiry_003",
        "video": {
            "title": "Minimal Inquiry",
            "url": "https://www.youtube.com/embed/ABC123xyz_9",
        },
        "paper": {
            "html_render_path": "data/inquiries/inquiry_003/paper.html",
        },
        "audit": {
            "report_path": "data/inquiries/inquiry_003/audit_report.json",
        },
    }

    manifest = normalize_backend_inquiry_manifest(
        payload,
        fallback_inquiry_id="fallback",
    )

    assert manifest["inquiry_id"] == "inquiry_003"
    assert manifest["title"] == "Minimal Inquiry"
    assert manifest["youtube_url"] == "https://www.youtube.com/embed/ABC123xyz_9"
    assert manifest["paper_path"] == "data/inquiries/inquiry_003/paper.html"
    assert manifest["audit_report_path"] == "data/inquiries/inquiry_003/audit_report.json"


def test_normalize_backend_inquiry_manifest_rejects_missing_url():
    with pytest.raises(ValueError, match="missing youtube_url"):
        normalize_backend_inquiry_manifest(
            {
                "inquiry_id": "inquiry_bad",
                "title": "Bad Inquiry",
            },
            fallback_inquiry_id="inquiry_bad",
        )


def test_save_inquiry_manifest_writes_manifest(tmp_path: Path):
    manifest = {
        "inquiry_id": "inquiry:001",
        "title": "Saved Inquiry",
        "youtube_url": "https://www.youtube.com/watch?v=ABC123xyz_9",
        "status": "completed",
        "created_at": "2026-05-08T12:00:00+00:00",
        "paper_path": None,
        "audit_report_path": None,
        "parameters": {},
    }

    manifest_path = save_inquiry_manifest(
        manifest,
        library_dir=tmp_path,
    )

    assert manifest_path.exists()
    assert manifest_path.parent.name == "inquiry_001"

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert payload["inquiry_id"] == "inquiry:001"
    assert payload["title"] == "Saved Inquiry"


def test_backend_response_to_inquiry_import_result_success(tmp_path: Path):
    response = BackendResponse(
        status_code=200,
        ok=True,
        data={
            "inquiry_id": "inquiry_004",
            "title": "Imported Inquiry",
            "youtube_url": "https://www.youtube.com/watch?v=ABC123xyz_9",
            "status": "completed",
        },
    )

    result = backend_response_to_inquiry_import_result(
        response,
        inquiry_id="inquiry_004",
        library_dir=tmp_path,
    )

    assert result.imported is True
    assert result.inquiry_id == "inquiry_004"
    assert result.manifest_path is not None
    assert result.record is not None
    assert result.record.title == "Imported Inquiry"


def test_backend_response_to_inquiry_import_result_failure():
    response = BackendResponse(
        status_code=404,
        ok=False,
        data={"detail": "Inquiry not found."},
        error_message="Inquiry not found.",
    )

    result = backend_response_to_inquiry_import_result(
        response,
        inquiry_id="missing",
        library_dir="data/inquiries",
    )

    assert result.imported is False
    assert result.record is None
    assert result.message == "Inquiry not found."


def test_import_backend_inquiry_calls_client_and_saves_manifest(tmp_path: Path):
    client = FakeBackendClient(
        BackendResponse(
            status_code=200,
            ok=True,
            data={
                "inquiry_id": "inquiry_005",
                "title": "Client Imported Inquiry",
                "youtube_url": "https://youtu.be/ABC123xyz_9",
                "status": "completed",
            },
        )
    )

    result = import_backend_inquiry(
        inquiry_id="inquiry_005",
        client=client,
        library_dir=tmp_path,
    )

    assert client.requested_inquiry_id == "inquiry_005"
    assert result.imported is True
    assert Path(result.manifest_path).exists()


def test_import_backend_inquiry_rejects_empty_inquiry_id(tmp_path: Path):
    client = FakeBackendClient(
        BackendResponse(status_code=200, ok=True, data={})
    )

    with pytest.raises(ValueError, match="inquiry_id"):
        import_backend_inquiry(
            inquiry_id=" ",
            client=client,
            library_dir=tmp_path,
        )

    assert client.requested_inquiry_id is None