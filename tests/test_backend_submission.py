import pytest

from src.frontend.backend_client import BackendResponse
from src.frontend.backend_submission import (
    backend_response_to_submission_result,
    submit_queued_request_to_backend,
)
from src.frontend.run_queue import wrap_request_for_queue
from src.frontend.run_request import create_inquiry_run_request


class FakeBackendClient:
    def __init__(self, response: BackendResponse):
        self.response = response
        self.submitted_request = None

    def submit_run_request(self, run_request):
        self.submitted_request = run_request
        return self.response


def test_backend_response_to_submission_result_success():
    response = BackendResponse(
        status_code=202,
        ok=True,
        data={
            "request_id": "request_001",
            "run_id": "run_001",
        },
    )

    result = backend_response_to_submission_result(
        response,
        fallback_request_id="fallback_request",
    )

    assert result.submitted is True
    assert result.status == "submitted"
    assert result.request_id == "request_001"
    assert result.run_id == "run_001"
    assert result.message == "Run request submitted to backend."


def test_backend_response_to_submission_result_uses_fallback_request_id():
    response = BackendResponse(
        status_code=202,
        ok=True,
        data={
            "run_id": "run_001",
        },
    )

    result = backend_response_to_submission_result(
        response,
        fallback_request_id="fallback_request",
    )

    assert result.submitted is True
    assert result.request_id == "fallback_request"
    assert result.run_id == "run_001"


def test_backend_response_to_submission_result_failure():
    response = BackendResponse(
        status_code=500,
        ok=False,
        data={"detail": "Backend exploded politely."},
        error_message="Backend exploded politely.",
    )

    result = backend_response_to_submission_result(
        response,
        fallback_request_id="request_001",
    )

    assert result.submitted is False
    assert result.status == "failed"
    assert result.request_id == "request_001"
    assert result.run_id is None
    assert result.message == "Backend exploded politely."


def test_submit_queued_request_to_backend_submits_executable_request():
    request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1, 2],
    )

    queued = wrap_request_for_queue(
        request,
        status="pending",
    )

    fake_client = FakeBackendClient(
        BackendResponse(
            status_code=202,
            ok=True,
            data={
                "request_id": request.request_id,
                "run_id": "run_123",
            },
        )
    )

    result = submit_queued_request_to_backend(
        queued,
        client=fake_client,
    )

    assert result.submitted is True
    assert result.run_id == "run_123"
    assert fake_client.submitted_request == request


def test_submit_queued_request_to_backend_rejects_non_executable_request():
    request = create_inquiry_run_request(
        youtube_url="https://youtu.be/ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1],
    )

    queued = wrap_request_for_queue(
        request,
        status="running",
    )

    fake_client = FakeBackendClient(
        BackendResponse(
            status_code=202,
            ok=True,
            data={"run_id": "run_123"},
        )
    )

    with pytest.raises(ValueError, match="cannot be submitted"):
        submit_queued_request_to_backend(
            queued,
            client=fake_client,
        )

    assert fake_client.submitted_request is None


def test_submission_result_to_dict_contains_operator_fields():
    response = BackendResponse(
        status_code=202,
        ok=True,
        data={
            "request_id": "request_001",
            "run_id": "run_001",
            "status": "accepted",
        },
    )

    result = backend_response_to_submission_result(
        response,
        fallback_request_id="request_001",
    )

    payload = result.to_dict()

    assert payload["submitted"] is True
    assert payload["status"] == "submitted"
    assert payload["request_id"] == "request_001"
    assert payload["run_id"] == "run_001"
    assert payload["response_data"]["status"] == "accepted"