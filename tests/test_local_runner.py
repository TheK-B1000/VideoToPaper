import json
from pathlib import Path

import pytest

from src.frontend.local_runner import (
    build_initial_progress_log,
    build_run_id,
    launch_local_run,
    launch_local_run_from_request_file,
)
from src.frontend.run_queue import wrap_request_for_queue
from src.frontend.run_request import create_inquiry_run_request, save_run_request


def test_build_run_id_contains_request_id():
    run_id = build_run_id("request_abc123")

    assert run_id.startswith("run_")
    assert run_id.endswith("_request_abc123")


def test_build_initial_progress_log_creates_queued_steps():
    progress = build_initial_progress_log(
        run_id="run_001",
        request_id="request_001",
        stages=["source_ingestion", "evaluation"],
    )

    assert progress["run_id"] == "run_001"
    assert progress["request_id"] == "request_001"
    assert progress["status"] == "queued"
    assert progress["current_step"] == "source_ingestion"
    assert len(progress["steps"]) == 2
    assert progress["steps"][0]["name"] == "source_ingestion"
    assert progress["steps"][0]["status"] == "queued"
    assert progress["steps"][1]["name"] == "evaluation"


def test_build_initial_progress_log_rejects_empty_stages():
    with pytest.raises(ValueError, match="At least one stage"):
        build_initial_progress_log(
            run_id="run_001",
            request_id="request_001",
            stages=[],
        )


def test_launch_local_run_creates_run_artifacts(tmp_path: Path):
    request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1, 2],
        stages=["source_ingestion", "claim_inventory"],
    )

    request_path = save_run_request(request, tmp_path / "requests")
    queued = wrap_request_for_queue(
        request,
        status="pending",
        request_path=request_path.as_posix(),
    )

    launch = launch_local_run(queued, runs_dir=tmp_path / "runs")

    assert launch.status == "queued"

    run_dir = Path(launch.run_dir)
    request_snapshot_path = Path(launch.request_snapshot_path)
    progress_path = Path(launch.progress_path)

    assert run_dir.exists()
    assert request_snapshot_path.exists()
    assert progress_path.exists()

    progress = json.loads(progress_path.read_text(encoding="utf-8"))

    assert progress["request_id"] == request.request_id
    assert progress["status"] == "queued"
    assert progress["current_step"] == "source_ingestion"
    assert [step["name"] for step in progress["steps"]] == [
        "source_ingestion",
        "claim_inventory",
    ]


def test_launch_local_run_rejects_non_executable_status(tmp_path: Path):
    request = create_inquiry_run_request(
        youtube_url="https://www.youtube.com/watch?v=ABC123xyz_9",
        claim_type_filter=["empirical_technical"],
        retrieval_depth=3,
        source_tiers=[1],
    )

    queued = wrap_request_for_queue(request, status="running")

    with pytest.raises(ValueError, match="not executable"):
        launch_local_run(queued, runs_dir=tmp_path / "runs")


def test_launch_local_run_from_request_file_supports_plain_request(tmp_path: Path):
    request = create_inquiry_run_request(
        youtube_url="https://youtu.be/ABC123xyz_9",
        claim_type_filter=["predictive"],
        retrieval_depth=2,
        source_tiers=[1],
        stages=["claim_inventory", "evaluation"],
    )

    request_path = save_run_request(request, tmp_path / "requests")

    launch = launch_local_run_from_request_file(
        request_path,
        runs_dir=tmp_path / "runs",
    )

    assert Path(launch.request_snapshot_path).exists()
    assert Path(launch.progress_path).exists()

    progress = json.loads(
        Path(launch.progress_path).read_text(encoding="utf-8")
    )

    assert progress["request_id"] == request.request_id
    assert [step["name"] for step in progress["steps"]] == [
        "claim_inventory",
        "evaluation",
    ]