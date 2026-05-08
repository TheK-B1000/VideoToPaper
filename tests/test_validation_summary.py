from src.evaluation.validation_summary import render_validation_summary


def test_render_validation_summary_for_valid_payload():
    payload = {
        "valid": True,
        "error_count": 0,
        "errors": [],
    }

    summary = render_validation_summary(payload)

    assert "# Paper Artifact Validation Summary" in summary
    assert "**Valid:** PASS" in summary
    assert "**Error Count:** 0" in summary
    assert "- No validation errors found." in summary


def test_render_validation_summary_for_invalid_payload():
    payload = {
        "valid": False,
        "error_count": 2,
        "errors": [
            "Missing required top-level field: claims",
            "rendered_clips[0].end must be greater than start.",
        ],
    }

    summary = render_validation_summary(payload)

    assert "**Valid:** FAIL" in summary
    assert "**Error Count:** 2" in summary
    assert "- Missing required top-level field: claims" in summary
    assert "- rendered_clips[0].end must be greater than start." in summary


def test_render_validation_summary_handles_missing_optional_fields():
    payload = {}

    summary = render_validation_summary(payload)

    assert "**Valid:** FAIL" in summary
    assert "**Error Count:** 0" in summary
    assert "- No validation errors found." in summary