import json
from pathlib import Path

import pytest

from src.frontend.backend_client import BackendResponse
from src.frontend.backend_progress_sync import (
    backend_response_to_progress_sync_result,
    normalize_backend_progress_payload,
    save_progress_snapshot,
    sync_backend_progress,
)
from src.frontend.run_progress import RunProgress


class FakeBackendClient:
    def __init__(self, response: BackendResponse):
        self.response = response
        self.requested_run_id = None

    def get_run_progress(self, run_id: str):
        self.requested_run_id = run_id
        return self.response


def test_normalize_backend_progress_payload_accepts_native_shape():
    payload = {
        "run_id": "run_001",
        "status": "running",
        "current_step": "claim_inventory",
        "elapsed_seconds": 12.5,
        "steps": [
            {"name": "source_ingestion", "status": "completed"},
            {"name": "claim_inventory", "status": "running"},
        ],
    }

    normalized = normalize_backend_progress_payload(payload, run_id="fallback")

    assert normalized["run_id"] == "run_001"
    assert normalized["status"] == "running"
    assert normalized["current_step"] == "claim_inventory"
    assert len(normalized["steps"]) == 2


def test_normalize_backend_progress_payload_accepts_wrapped_shape():
    payload = {
        "run_id": "run_002",
        "progress": {
            "status": "running",
            "current_step": "evidence_retrieval",
            "steps": [
                {"name": "evidence_retrieval", "status": "running"},
            ],
        },
    }

    normalized = normalize_backend_progress_payload(payload, run_id="fallback")

    assert normalized["run_id"] == "run_002"
    assert normalized["status"] == "running"
    assert normalized["current_step"] == "evidence_retrieval"


def test_normalize_backend_progress_payload_accepts_minimal_shape():
    payload = {
        "status": "running",
        "stage": "html_assembly",
        "elapsed_seconds": 9.0,
        "message": "Rendering paper.",
    }

    normalized = normalize_backend_progress_payload(payload, run_id="run_003")

    assert normalized["run_id"] == "run_003"
    assert normalized["status"] == "running"
    assert normalized["current_step"] == "html_assembly"
    assert normalized["steps"][0]["name"] == "html_assembly"
    assert normalized["steps"][0]["status"] == "running"
    assert normalized["steps"][0]["message"] == "Rendering paper."


def test_backend_response_to_progress_sync_result_success_without_snapshot():
    response = BackendResponse(
        status_code=200,
        ok=True,
        data={
            "run_id": "run_004",
            "status": "running",
            "current_step": "evaluation",
            "steps": [
                {"name": "evaluation", "status": "running"},
            ],
        },
    )

    result = backend_response_to_progress_sync_result(
        response,
        run_id="run_004",
    )

    assert result.synced is True
    assert result.run_id == "run_004"
    assert result.progress is not None
    assert result.progress.current_step == "evaluation"
    assert result.snapshot_path is None
    assert result.message == "Backend progress synced."


def test_backend_response_to_progress_sync_result_success_with_snapshot(tmp_path: Path):
    response = BackendResponse(
        status_code=200,
        ok=True,
        data={
            "run_id": "run_005",
            "status": "completed",
            "current_step": None,
            "elapsed_seconds": 20,
            "steps": [
                {"name": "source_ingestion", "status": "completed"},
                {"name": "evaluation", "status": "completed"},
            ],
        },
    )

    result = backend_response_to_progress_sync_result(
        response,
        run_id="run_005",
        snapshot_dir=tmp_path,
    )

    assert result.synced is True
    assert result.snapshot_path is not None

    snapshot_path = Path(result.snapshot_path)

    assert snapshot_path.exists()

    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))

    assert payload["run_id"] == "run_005"
    assert payload["status"] == "completed"
    assert len(payload["steps"]) == 2


def test_backend_response_to_progress_sync_result_failure():
    response = BackendResponse(
        status_code=404,
        ok=False,
        data={"detail": "Run not found."},
        error_message="Run not found.",
    )

    result = backend_response_to_progress_sync_result(
        response,
        run_id="missing_run",
    )

    assert result.synced is False
    assert result.progress is None
    assert result.message == "Run not found."


def test_backend_response_to_progress_sync_result_handles_bad_payload():
    response = BackendResponse(
        status_code=200,
        ok=True,
        data={
            "run_id": "",
            "status": "running",
            "steps": "bad shape",
        },
    )

    result = backend_response_to_progress_sync_result(
        response,
        run_id="run_bad",
    )

    assert result.synced is False
    assert result.progress is None
    assert "steps must be a list" in result.message


def test_sync_backend_progress_calls_client_and_saves_snapshot(tmp_path: Path):
    client = FakeBackendClient(
        BackendResponse(
            status_code=200,
            ok=True,
            data={
                "run_id": "run_006",
                "status": "running",
                "current_step": "claim_inventory",
                "steps": [
                    {"name": "claim_inventory", "status": "running"},
                ],
            },
        )
    )

    result = sync_backend_progress(
        run_id="run_006",
        client=client,
        snapshot_dir=tmp_path,
    )

    assert client.requested_run_id == "run_006"
    assert result.synced is True
    assert result.snapshot_path is not None


def test_sync_backend_progress_rejects_empty_run_id():
    client = FakeBackendClient(
        BackendResponse(status_code=200, ok=True, data={})
    )

    with pytest.raises(ValueError, match="run_id"):
        sync_backend_progress(
            run_id=" ",
            client=client,
        )

    assert client.requested_run_id is None


def test_save_progress_snapshot_writes_progress(tmp_path: Path):
    progress = RunProgress.from_dict(
        {
            "run_id": "run_007",
            "status": "completed",
            "current_step": None,
            "steps": [
                {"name": "evaluation", "status": "completed"},
            ],
        }
    )

    output_path = save_progress_snapshot(
        progress,
        snapshot_dir=tmp_path,
    )

    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["run_id"] == "run_007"
    assert payload["steps"][0]["name"] == "evaluation"