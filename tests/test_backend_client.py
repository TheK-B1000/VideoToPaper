import json
from urllib import error
from urllib.request import Request

import pytest

from src.frontend.backend_client import (
    BackendClient,
    BackendClientConfig,
    _extract_error_message,
    _parse_json_object,
)
from src.frontend.run_request import create_inquiry_run_request


class FakeResponse:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


def test_backend_client_rejects_empty_base_url():
    with pytest.raises(ValueError, match="base_url"):
        BackendClient(BackendClientConfig(base_url=" "))


def test_backend_client_health_check_success(monkeypatch):
    captured = {}

    def fake_urlopen(req: Request, timeout: float):
        captured["url"] = req.full_url
        captured["timeout"] = timeout
        captured["method"] = req.get_method()
        return FakeResponse(
            status=200,
            payload={"status": "ok"},
        )

    monkeypatch.setattr("src.frontend.backend_client.request.urlopen", fake_urlopen)

    client = BackendClient(
        BackendClientConfig(
            base_url="http://localhost:8000/",
            timeout_seconds=5.0,
        )
    )

    response = client.health_check()

    assert response.ok is True
    assert response.status_code == 200
    assert response.data == {"status": "ok"}
    assert captured["url"] == "http://localhost:8000/health"
    assert captured["timeout"] == 5.0
    assert captured["method"] == "GET"


def test_backend_client_submit_run_request_posts_json(monkeypatch):
    captured = {}

    def fake_urlopen(req: Request, timeout: float):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["content_type"] = req.headers["Content-type"]

        return FakeResponse(
            status=202,
            payload={
                "request_id": captured["body"]["request_id"],
                "run_id": "run_001",
            },
        )

    monkeypatch.setattr("src.frontend.backend_client.request.urlopen", fake_urlopen)

    run_request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1, 2],
    )

    client = BackendClient(BackendClientConfig(base_url="http://localhost:8000"))

    response = client.submit_run_request(run_request)

    assert response.ok is True
    assert response.status_code == 202
    assert response.request_id == run_request.request_id
    assert response.run_id == "run_001"
    assert captured["url"] == "http://localhost:8000/inquiries/run"
    assert captured["method"] == "POST"
    assert captured["body"]["video_id"] == "ABC123xyz_9"
    assert captured["content_type"] == "application/json"


def test_backend_client_get_run_progress_rejects_empty_run_id():
    client = BackendClient(BackendClientConfig(base_url="http://localhost:8000"))

    with pytest.raises(ValueError, match="run_id"):
        client.get_run_progress(" ")


def test_backend_client_handles_http_error(monkeypatch):
    def fake_urlopen(req: Request, timeout: float):
        raise error.HTTPError(
            url=req.full_url,
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=FakeErrorBody({"detail": "Run not found."}),
        )

    monkeypatch.setattr("src.frontend.backend_client.request.urlopen", fake_urlopen)

    client = BackendClient(BackendClientConfig(base_url="http://localhost:8000"))

    response = client.get_run_progress("run_missing")

    assert response.ok is False
    assert response.status_code == 404
    assert response.error_message == "Run not found."


def test_backend_client_handles_url_error(monkeypatch):
    def fake_urlopen(req: Request, timeout: float):
        raise error.URLError("connection refused")

    monkeypatch.setattr("src.frontend.backend_client.request.urlopen", fake_urlopen)

    client = BackendClient(BackendClientConfig(base_url="http://localhost:8000"))

    response = client.health_check()

    assert response.ok is False
    assert response.status_code == 0
    assert "connection refused" in response.error_message


def test_parse_json_object_handles_empty_body():
    assert _parse_json_object("") == {}


def test_parse_json_object_wraps_list_value():
    assert _parse_json_object("[1, 2, 3]") == {"value": [1, 2, 3]}


def test_parse_json_object_wraps_invalid_json():
    assert _parse_json_object("not-json") == {"raw_body": "not-json"}


def test_extract_error_message_prefers_detail():
    assert _extract_error_message({"detail": "Bad request."}) == "Bad request."
    assert _extract_error_message({"error": "Nope."}) == "Nope."
    assert _extract_error_message({"message": "Try again."}) == "Try again."
    assert _extract_error_message({}) is None


class FakeErrorBody:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def close(self):
        return None
