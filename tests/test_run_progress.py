import json
from pathlib import Path

import pytest

from src.frontend.run_progress import (
    ProgressStep,
    RunProgress,
    load_run_progress,
    summarize_progress,
)


def test_progress_step_from_dict_accepts_valid_step():
    step = ProgressStep.from_dict(
        {
            "name": "claim_inventory",
            "status": "completed",
            "started_at": "2026-05-08T12:00:00",
            "finished_at": "2026-05-08T12:00:05",
            "elapsed_seconds": 5,
            "message": "Claim inventory completed.",
        }
    )

    assert step.name == "claim_inventory"
    assert step.status == "completed"
    assert step.elapsed_seconds == 5.0
    assert step.message == "Claim inventory completed."


def test_progress_step_rejects_missing_name():
    with pytest.raises(ValueError, match="missing a name"):
        ProgressStep.from_dict(
            {
                "status": "completed",
            }
        )


def test_progress_step_rejects_invalid_status():
    with pytest.raises(ValueError, match="Invalid progress step status"):
        ProgressStep.from_dict(
            {
                "name": "evidence_retrieval",
                "status": "almost_done",
            }
        )


def test_run_progress_from_dict_computes_completion_ratio():
    progress = RunProgress.from_dict(
        {
            "run_id": "run_001",
            "status": "running",
            "current_step": "evidence_retrieval",
            "elapsed_seconds": 12.5,
            "steps": [
                {"name": "source_ingestion", "status": "completed"},
                {"name": "claim_inventory", "status": "completed"},
                {"name": "evidence_retrieval", "status": "running"},
                {"name": "paper_assembly", "status": "queued"},
            ],
        }
    )

    assert progress.run_id == "run_001"
    assert progress.status == "running"
    assert progress.current_step == "evidence_retrieval"
    assert progress.completion_ratio == 0.5
    assert progress.has_failed is False


def test_run_progress_detects_failed_step():
    progress = RunProgress.from_dict(
        {
            "run_id": "run_002",
            "status": "failed",
            "current_step": "html_assembly",
            "steps": [
                {"name": "source_ingestion", "status": "completed"},
                {"name": "html_assembly", "status": "failed"},
            ],
        }
    )

    assert progress.has_failed is True


def test_run_progress_rejects_missing_run_id():
    with pytest.raises(ValueError, match="missing run_id"):
        RunProgress.from_dict(
            {
                "status": "running",
                "steps": [],
            }
        )


def test_run_progress_rejects_non_list_steps():
    with pytest.raises(ValueError, match="steps must be a list"):
        RunProgress.from_dict(
            {
                "run_id": "run_003",
                "status": "running",
                "steps": {"name": "bad_shape"},
            }
        )


def test_load_run_progress_reads_file(tmp_path: Path):
    progress_path = tmp_path / "progress.json"

    progress_path.write_text(
        json.dumps(
            {
                "run_id": "run_004",
                "status": "completed",
                "current_step": None,
                "elapsed_seconds": 30,
                "steps": [
                    {"name": "source_ingestion", "status": "completed"},
                    {"name": "paper_assembly", "status": "completed"},
                ],
            }
        ),
        encoding="utf-8",
    )

    progress = load_run_progress(progress_path)

    assert progress is not None
    assert progress.run_id == "run_004"
    assert progress.status == "completed"
    assert progress.completion_ratio == 1.0


def test_load_run_progress_returns_none_for_missing_file(tmp_path: Path):
    progress = load_run_progress(tmp_path / "missing.json")

    assert progress is None


def test_summarize_progress_counts_step_statuses():
    progress = RunProgress.from_dict(
        {
            "run_id": "run_005",
            "status": "running",
            "current_step": "evidence_retrieval",
            "elapsed_seconds": 44,
            "steps": [
                {"name": "source_ingestion", "status": "completed"},
                {"name": "claim_inventory", "status": "completed"},
                {"name": "evidence_retrieval", "status": "running"},
                {"name": "paper_assembly", "status": "queued"},
                {"name": "extra_cleanup", "status": "skipped"},
            ],
        }
    )

    summary = summarize_progress(progress)

    assert summary["run_id"] == "run_005"
    assert summary["completed_steps"] == 2
    assert summary["running_steps"] == 1
    assert summary["queued_steps"] == 1
    assert summary["skipped_steps"] == 1
    assert summary["failed_steps"] == 0
    assert summary["total_steps"] == 5
    assert summary["completion_ratio"] == 0.4
    assert summary["has_failed"] is False