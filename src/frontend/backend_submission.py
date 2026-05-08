from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.frontend.backend_client import BackendClient, BackendResponse
from src.frontend.run_queue import QueuedRunRequest


@dataclass(frozen=True)
class BackendSubmissionResult:
    submitted: bool
    status: str
    request_id: str
    run_id: str | None
    message: str
    response_data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "submitted": self.submitted,
            "status": self.status,
            "request_id": self.request_id,
            "run_id": self.run_id,
            "message": self.message,
            "response_data": self.response_data,
        }


def submit_queued_request_to_backend(
    queued_request: QueuedRunRequest,
    *,
    client: BackendClient,
) -> BackendSubmissionResult:
    """
    Submit a queued request to the backend API.

    The frontend should only submit requests that are executable from the queue.
    Backend failures are returned as structured results instead of raising,
    so Streamlit can show a clean operator-facing message.
    """
    if not queued_request.is_executable:
        raise ValueError(
            f"Request {queued_request.request_id} cannot be submitted from status "
            f"{queued_request.status!r}."
        )

    response = client.submit_run_request(queued_request.request)

    return backend_response_to_submission_result(
        response,
        fallback_request_id=queued_request.request_id,
    )


def backend_response_to_submission_result(
    response: BackendResponse,
    *,
    fallback_request_id: str,
) -> BackendSubmissionResult:
    request_id = response.request_id or fallback_request_id
    run_id = response.run_id

    if response.ok:
        return BackendSubmissionResult(
            submitted=True,
            status="submitted",
            request_id=request_id,
            run_id=run_id,
            message="Run request submitted to backend.",
            response_data=response.data,
        )

    return BackendSubmissionResult(
        submitted=False,
        status="failed",
        request_id=request_id,
        run_id=run_id,
        message=response.error_message or "Backend submission failed.",
        response_data=response.data,
    )