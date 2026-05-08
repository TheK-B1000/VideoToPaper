import json
from pathlib import Path

import pytest

from src.frontend.queue_status import (
    build_queue_status_payload,
    mark_request_completed,
    mark_request_failed,
    mark_request_queued,
    mark_request_running,
    update_queue_status_file,
)
from src.frontend.run_queue import load_queued_run_request, wrap_request_for_queue
from src.frontend.run_request import create_inquiry_run_request, save_run_request


def test_build_queue_status_payload_preserves_request_data():
    request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1, 2],
    )

    queued = wrap_request_for_queue(
        request,
        status="pending",
        request_path="data/run_requests/request_001.json",
    )

    payload = build_queue_status_payload(
        queued,
        status="queued",
        progress_path="logs/runs/run_001/progress.json",
    )

    assert payload["request"]["request_id"] == request.request_id
    assert payload["status"] == "queued"
    assert payload["progress_path"] == "logs/runs/run_001/progress.json"
    assert payload["result_inquiry_id"] is None
    assert payload["last_updated_at"]


def test_build_queue_status_payload_rejects_invalid_status():
    request = create_inquiry_run_request(
        youtube_url="https://youtu.be/ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1],
    )

    queued = wrap_request_for_queue(request, status="pending")

    with pytest.raises(ValueError, match="Invalid queue status"):
        build_queue_status_payload(
            queued,
            status="half_launched",
        )


def test_update_queue_status_file_wraps_plain_request(tmp_path: Path):
    request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=4,
        source_tiers=[1, 2],
    )

    request_path = save_run_request(request, tmp_path)

    update_queue_status_file(
        request_path,
        status="queued",
        progress_path="logs/runs/run_001/progress.json",
    )

    payload = json.loads(request_path.read_text(encoding="utf-8"))

    assert "request" in payload
    assert payload["request"]["request_id"] == request.request_id
    assert payload["status"] == "queued"
    assert payload["progress_path"] == "logs/runs/run_001/progress.json"

    loaded = load_queued_run_request(request_path)

    assert loaded.status == "queued"
    assert loaded.progress_path == "logs/runs/run_001/progress.json"
    assert loaded.is_executable is True


def test_mark_request_queued_sets_progress_path(tmp_path: Path):
    request = create_inquiry_run_request(
        youtube_url="https://youtu.be/ABC123xyz_9",
        claim_type_filter=["predictive"],
        retrieval_depth=2,
        source_tiers=[1],
    )

    request_path = save_run_request(request, tmp_path)

    mark_request_queued(
        request_path,
        progress_path="logs/runs/run_002/progress.json",
    )

    queued = load_queued_run_request(request_path)

    assert queued.status == "queued"
    assert queued.progress_path == "logs/runs/run_002/progress.json"


def test_mark_request_running_preserves_existing_progress_path(tmp_path: Path):
    request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/embed/ABC123xyz_9",
        claim_type_filter=["empirical_scientific"],
        retrieval_depth=3,
        source_tiers=[1],
    )

    request_path = save_run_request(request, tmp_path)

    mark_request_queued(
        request_path,
        progress_path="logs/runs/run_003/progress.json",
    )

    mark_request_running(request_path)

    queued = load_queued_run_request(request_path)

    assert queued.status == "running"
    assert queued.progress_path == "logs/runs/run_003/progress.json"


def test_mark_request_completed_sets_result_inquiry_id(tmp_path: Path):
    request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1],
    )

    request_path = save_run_request(request, tmp_path)

    mark_request_completed(
        request_path,
        result_inquiry_id="inquiry_001",
        progress_path="logs/runs/run_004/progress.json",
    )

    queued = load_queued_run_request(request_path)

    assert queued.status == "completed"
    assert queued.result_inquiry_id == "inquiry_001"
    assert queued.progress_path == "logs/runs/run_004/progress.json"
    assert queued.is_executable is False


def test_mark_request_failed_sets_failed_status(tmp_path: Path):
    request = create_inquiry_run_request(
        youtube_url="https://youtu.be/ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1],
    )

    request_path = save_run_request(request, tmp_path)

    mark_request_failed(request_path)

    queued = load_queued_run_request(request_path)

    assert queued.status == "failed"
    assert queued.is_executable is False


def test_update_queue_status_file_rejects_invalid_status(tmp_path: Path):
    request = create_inquiry_run_request(
        youtube_url="https://youtu.be/ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1],
    )

    request_path = save_run_request(request, tmp_path)

    with pytest.raises(ValueError, match="Invalid queue status"):
        update_queue_status_file(
            request_path,
            status="banana_mode",
        )