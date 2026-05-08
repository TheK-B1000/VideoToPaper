import json

import pytest

from src.evaluation.paper_artifact_validator import ArtifactValidationResult
from src.evaluation.validation_report_writer import (
    build_validation_report_payload,
    load_validation_report,
    write_validation_report,
)


def test_build_validation_report_payload_for_valid_result():
    result = ArtifactValidationResult(valid=True, errors=[])

    payload = build_validation_report_payload(result)

    assert payload == {
        "valid": True,
        "error_count": 0,
        "errors": [],
    }


def test_build_validation_report_payload_for_invalid_result():
    result = ArtifactValidationResult(
        valid=False,
        errors=[
            "Missing required top-level field: claims",
            "references must be a list.",
        ],
    )

    payload = build_validation_report_payload(result)

    assert payload["valid"] is False
    assert payload["error_count"] == 2
    assert payload["errors"] == [
        "Missing required top-level field: claims",
        "references must be a list.",
    ]


def test_write_validation_report_creates_json_file(tmp_path):
    result = ArtifactValidationResult(
        valid=False,
        errors=["claims[0] is missing claim_id."],
    )

    output_path = tmp_path / "reports" / "validation_report.json"

    written_path = write_validation_report(result, output_path)

    assert written_path == output_path
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["valid"] is False
    assert payload["error_count"] == 1
    assert payload["errors"] == ["claims[0] is missing claim_id."]


def test_write_validation_report_creates_parent_directories(tmp_path):
    result = ArtifactValidationResult(valid=True, errors=[])
    output_path = tmp_path / "nested" / "validation" / "report.json"

    write_validation_report(result, output_path)

    assert output_path.exists()


def test_load_validation_report_reads_json(tmp_path):
    result = ArtifactValidationResult(
        valid=False,
        errors=["rendered_clips[0].end must be greater than start."],
    )

    output_path = tmp_path / "validation_report.json"
    write_validation_report(result, output_path)

    loaded = load_validation_report(output_path)

    assert loaded["valid"] is False
    assert loaded["error_count"] == 1
    assert loaded["errors"] == [
        "rendered_clips[0].end must be greater than start."
    ]


def test_load_validation_report_raises_for_missing_file(tmp_path):
    missing_path = tmp_path / "missing_validation_report.json"

    with pytest.raises(FileNotFoundError):
        load_validation_report(missing_path)