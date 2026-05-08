import json
from pathlib import Path

import pytest

from src.frontend.operator_activity import (
    OperatorActivity,
    append_activity,
    create_activity,
    filter_activities,
    read_activity_log,
    record_activity,
)


def test_create_activity_builds_valid_activity():
    activity = create_activity(
        activity_type="request_created",
        message="Created a request.",
        request_id="request_001",
        metadata={"source": "test"},
    )

    assert activity.activity_id.startswith("activity_")
    assert activity.activity_type == "request_created"
    assert activity.message == "Created a request."
    assert activity.request_id == "request_001"
    assert activity.metadata == {"source": "test"}


def test_create_activity_rejects_invalid_type():
    with pytest.raises(ValueError, match="Invalid activity type"):
        create_activity(
            activity_type="banana_event",
            message="Nope.",
        )


def test_create_activity_rejects_empty_message():
    with pytest.raises(ValueError, match="message cannot be empty"):
        create_activity(
            activity_type="request_created",
            message=" ",
        )


def test_operator_activity_from_dict_rejects_missing_message():
    with pytest.raises(ValueError, match="missing a message"):
        OperatorActivity.from_dict(
            {
                "activity_id": "activity_001",
                "activity_type": "request_created",
                "created_at": "2026-05-08T12:00:00+00:00",
            }
        )


def test_append_and_read_activity_log_round_trip(tmp_path: Path):
    log_path = tmp_path / "operator_activity.jsonl"

    activity = create_activity(
        activity_type="run_launched",
        message="Launched local run.",
        request_id="request_001",
        run_id="run_001",
    )

    append_activity(activity, log_path)

    loaded = read_activity_log(log_path)

    assert len(loaded) == 1
    assert loaded[0].activity_id == activity.activity_id
    assert loaded[0].activity_type == "run_launched"
    assert loaded[0].request_id == "request_001"
    assert loaded[0].run_id == "run_001"


def test_record_activity_creates_and_appends(tmp_path: Path):
    log_path = tmp_path / "activity.jsonl"

    activity = record_activity(
        activity_type="audit_opened",
        message="Opened audit report.",
        artifact_path="data/inquiries/demo/audit_report.json",
        log_path=log_path,
    )

    loaded = read_activity_log(log_path)

    assert len(loaded) == 1
    assert loaded[0].activity_id == activity.activity_id
    assert loaded[0].artifact_path == "data/inquiries/demo/audit_report.json"


def test_read_activity_log_skips_bad_lines(tmp_path: Path):
    log_path = tmp_path / "activity.jsonl"

    good_activity = create_activity(
        activity_type="paper_opened",
        message="Opened paper.",
        artifact_path="paper.html",
    )

    log_path.write_text(
        "\n".join(
            [
                "{bad json",
                json.dumps(good_activity.to_dict()),
                json.dumps({"activity_type": "invalid", "message": "bad"}),
            ]
        ),
        encoding="utf-8",
    )

    loaded = read_activity_log(log_path)

    assert len(loaded) == 1
    assert loaded[0].activity_type == "paper_opened"


def test_read_activity_log_applies_limit(tmp_path: Path):
    log_path = tmp_path / "activity.jsonl"

    first = create_activity(
        activity_type="request_created",
        message="First.",
        request_id="request_001",
    )

    second = create_activity(
        activity_type="request_created",
        message="Second.",
        request_id="request_002",
    )

    append_activity(first, log_path)
    append_activity(second, log_path)

    loaded = read_activity_log(log_path, limit=1)

    assert len(loaded) == 1


def test_filter_activities_by_type_and_query():
    first = create_activity(
        activity_type="request_created",
        message="Created request for reinforcement learning video.",
        request_id="request_001",
    )

    second = create_activity(
        activity_type="audit_opened",
        message="Opened audit report.",
        artifact_path="audit.json",
    )

    filtered = filter_activities(
        [first, second],
        activity_type="request_created",
        query="reinforcement",
    )

    assert filtered == [first]

    no_match = filter_activities(
        [first, second],
        activity_type="audit_opened",
        query="reinforcement",
    )

    assert no_match == []