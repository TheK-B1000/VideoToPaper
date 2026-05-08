from src.evaluation.validation_summary_writer import write_validation_summary


def test_write_validation_summary_creates_markdown_file(tmp_path):
    payload = {
        "valid": False,
        "error_count": 1,
        "errors": ["claims[0] is missing claim_id."],
    }

    output_path = tmp_path / "reports" / "validation_summary.md"

    written_path = write_validation_summary(payload, output_path)

    assert written_path == output_path
    assert output_path.exists()

    summary = output_path.read_text(encoding="utf-8")

    assert "# Paper Artifact Validation Summary" in summary
    assert "**Valid:** FAIL" in summary
    assert "- claims[0] is missing claim_id." in summary


def test_write_validation_summary_creates_parent_directories(tmp_path):
    payload = {
        "valid": True,
        "error_count": 0,
        "errors": [],
    }

    output_path = tmp_path / "nested" / "validation" / "summary.md"

    write_validation_summary(payload, output_path)

    assert output_path.exists()