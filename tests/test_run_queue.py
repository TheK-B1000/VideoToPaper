import json
from pathlib import Path

import pytest

from src.frontend.run_queue import (
    discover_run_requests,
    filter_queued_requests,
    load_queued_run_request,
    summarize_queue,
    wrap_request_for_queue,
)
from src.frontend.run_request import create_inquiry_run_request


def test_load_queued_run_request_supports_plain_request_file(tmp_path: Path):
    request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1, 2],
    )

    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(request.to_dict()),
        encoding="utf-8",
    )

    queued = load_queued_run_request(request_path)

    assert queued.request_id == request.request_id
    assert queued.status == "pending"
    assert queued.is_executable is True
    assert queued.request_path == request_path.as_posix()


def test_load_queued_run_request_supports_wrapped_queue_file(tmp_path: Path):
    request = create_inquiry_run_request(
        youtube_url="https://youtu.be/ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=2,
        source_tiers=[1],
    )

    request_path = tmp_path / "queued_request.json"
    request_path.write_text(
        json.dumps(
            {
                "request": request.to_dict(),
                "status": "running",
                "progress_path": "logs/runs/run_001.json",
                "result_inquiry_id": None,
                "last_updated_at": "2026-05-08T12:30:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    queued = load_queued_run_request(request_path)

    assert queued.request_id == request.request_id
    assert queued.status == "running"
    assert queued.is_executable is False
    assert queued.progress_path == "logs/runs/run_001.json"
    assert queued.last_updated_at == "2026-05-08T12:30:00+00:00"


def test_load_queued_run_request_rejects_invalid_status(tmp_path: Path):
    request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1],
    )

    request_path = tmp_path / "bad_status.json"
    request_path.write_text(
        json.dumps(
            {
                "request": request.to_dict(),
                "status": "half-baked",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid queue status"):
        load_queued_run_request(request_path)


def test_discover_run_requests_skips_invalid_files(tmp_path: Path):
    valid_request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1],
    )

    (tmp_path / "valid.json").write_text(
        json.dumps(valid_request.to_dict()),
        encoding="utf-8",
    )

    (tmp_path / "invalid.json").write_text(
        "{bad json",
        encoding="utf-8",
    )

    requests = discover_run_requests(tmp_path)

    assert len(requests) == 1
    assert requests[0].request_id == valid_request.request_id


def test_filter_queued_requests_by_status_and_query():
    first_request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1],
    )

    second_request = create_inquiry_run_request(
        youtube_url="https://youtu.be/DEF456uvw_1",
        claim_type_filter=["predictive"],
        retrieval_depth=2,
        source_tiers=[2],
    )

    queued = [
        wrap_request_for_queue(first_request, status="pending"),
        wrap_request_for_queue(second_request, status="completed"),
    ]

    pending = filter_queued_requests(
        queued,
        query="ABC123",
        status="pending",
    )

    assert len(pending) == 1
    assert pending[0].request.video_id == "ABC123xyz_9"

    completed = filter_queued_requests(
        queued,
        query="DEF456",
        status="completed",
    )

    assert len(completed) == 1
    assert completed[0].status == "completed"


def test_summarize_queue_counts_statuses():
    first_request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1],
    )

    second_request = create_inquiry_run_request(
        youtube_url="https://youtu.be/DEF456uvw_1",
        claim_type_filter=["predictive"],
        retrieval_depth=2,
        source_tiers=[2],
    )

    third_request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/embed/GHI789rst_2",
        claim_type_filter=["empirical_scientific"],
        retrieval_depth=4,
        source_tiers=[1, 2],
    )

    queued = [
        wrap_request_for_queue(first_request, status="pending"),
        wrap_request_for_queue(second_request, status="running"),
        wrap_request_for_queue(third_request, status="failed"),
    ]

    summary = summarize_queue(queued)

    assert summary["total"] == 3
    assert summary["pending"] == 1
    assert summary["running"] == 1
    assert summary["failed"] == 1
    assert summary["completed"] == 0
    assert summary["executable"] == 1


def test_wrap_request_for_queue_rejects_invalid_status():
    request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1],
    )

    with pytest.raises(ValueError, match="Invalid queue status"):
        wrap_request_for_queue(request, status="lost_in_space")