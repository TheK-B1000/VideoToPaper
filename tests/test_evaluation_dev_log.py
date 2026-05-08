from src.evaluation.evaluation_dev_log import (
    EvaluationDevLog,
    build_default_evaluation_dev_log,
    render_evaluation_dev_log,
    write_evaluation_dev_log,
)


def test_render_evaluation_dev_log_includes_sections():
    log = EvaluationDevLog(
        title="Test Dev Log",
        built=["Built the evaluator."],
        tested=["Tested the happy path."],
        learned=["Validation should happen before evaluation."],
        next_steps=["Connect to assembler output."],
        interview_explanation="I built a quality gate for generated papers.",
    )

    rendered = render_evaluation_dev_log(log)

    assert "# Test Dev Log" in rendered
    assert "## What I Built" in rendered
    assert "- Built the evaluator." in rendered
    assert "## What I Tested" in rendered
    assert "- Tested the happy path." in rendered
    assert "## What I Learned" in rendered
    assert "- Validation should happen before evaluation." in rendered
    assert "## Next Steps" in rendered
    assert "- Connect to assembler output." in rendered
    assert "## Interview Explanation" in rendered
    assert "I built a quality gate for generated papers." in rendered


def test_render_evaluation_dev_log_uses_fallbacks_for_empty_lists():
    log = EvaluationDevLog(title="Empty Log")

    rendered = render_evaluation_dev_log(log)

    assert "- Nothing recorded." in rendered
    assert "No interview explanation recorded." in rendered


def test_build_default_evaluation_dev_log_contains_core_evaluation_work():
    log = build_default_evaluation_dev_log()

    rendered = render_evaluation_dev_log(log)

    assert "Evaluation Harness Development Log" in rendered
    assert "four-axis evaluation harness" in rendered
    assert "steelman accuracy" in rendered
    assert "evidence balance" in rendered
    assert "citation integrity" in rendered
    assert "clip-anchor accuracy" in rendered


def test_write_evaluation_dev_log_creates_markdown_file(tmp_path):
    output_path = tmp_path / "logs" / "evaluation_dev_log.md"

    written_path = write_evaluation_dev_log(output_path)

    assert written_path == output_path
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")

    assert "# Evaluation Harness Development Log" in content
    assert "## What I Built" in content
    assert "## Interview Explanation" in content


def test_write_evaluation_dev_log_accepts_custom_log(tmp_path):
    output_path = tmp_path / "logs" / "custom_log.md"

    log = EvaluationDevLog(
        title="Custom Evaluation Notes",
        built=["Added a custom diagnostic."],
    )

    write_evaluation_dev_log(output_path, log=log)

    content = output_path.read_text(encoding="utf-8")

    assert "# Custom Evaluation Notes" in content
    assert "- Added a custom diagnostic." in content


def test_build_default_evaluation_dev_log_mentions_export_bridge():
    log = build_default_evaluation_dev_log()
    rendered = render_evaluation_dev_log(log)

    assert "paper artifact exporter" in rendered
    assert "export-and-evaluate pipeline" in rendered
    assert "assembler-style fixtures" in rendered
    assert "real paper assembler output" in rendered