from __future__ import annotations

import pytest

from src.frontend.run_progress import RunProgress
from src.ops.inquiry_progress_payload import (
    advance_pipeline_tick,
    build_initial_progress_log,
)


def test_build_initial_progress_log_matches_run_progress_schema():
    payload = build_initial_progress_log(
        run_id="run_001",
        request_id="request_001",
        stages=["alpha", "beta"],
    )
    progress = RunProgress.from_dict(payload)

    assert progress.run_id == "run_001"
    assert progress.status == "queued"
    assert progress.current_step == "alpha"
    assert len(progress.steps) == 2
    assert progress.steps[0].name == "alpha"
    assert progress.steps[0].status == "queued"


def test_advance_pipeline_tick_reaches_completed():
    payload = build_initial_progress_log(
        run_id="run_001",
        request_id="request_001",
        stages=["only_stage"],
    )

    for _ in range(50):
        payload = advance_pipeline_tick(payload, tick_seconds=0.5)
        if payload["status"] == "completed":
            break
    else:
        pytest.fail("progress did not reach completed")

    RunProgress.from_dict(payload)
    assert all(s["status"] == "completed" for s in payload["steps"])
