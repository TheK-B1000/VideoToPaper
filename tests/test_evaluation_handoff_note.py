from src.evaluation.evaluation_handoff_note import (
    render_evaluation_handoff_note,
    write_evaluation_handoff_note,
)


def test_render_evaluation_handoff_note_includes_status_and_next_step():
    note = render_evaluation_handoff_note()

    assert "# Evaluation Module Handoff Note" in note
    assert "The evaluation module is ready to connect to real paper assembler output." in note
    assert "## Next Engineering Step" in note
    assert "Connect the evaluator to the real paper assembler output." in note


def test_render_evaluation_handoff_note_includes_verification_command():
    note = render_evaluation_handoff_note()

    assert "python scripts/verify_evaluation_module.py" in note
    assert "--smoke-output-dir data/outputs/smoke_evaluation_suite" in note
    assert "--docs-output-dir docs/evaluation" in note
    assert "--status-output docs/evaluation/evaluation_module_status.md" in note


def test_render_evaluation_handoff_note_includes_design_boundary():
    note = render_evaluation_handoff_note()

    assert "Validation and evaluation are separate." in note
    assert "Is this artifact structurally shaped correctly?" in note
    assert "Is this structurally valid artifact publishable?" in note


def test_render_evaluation_handoff_note_includes_runner_example():
    note = render_evaluation_handoff_note()

    assert "from src.evaluation.evaluation_runner import run_paper_evaluation" in note
    assert "run_paper_evaluation(" in note
    assert "paper_artifact_path=" in note
    assert "audit_report_path=" in note


def test_write_evaluation_handoff_note_creates_markdown_file(tmp_path):
    output_path = tmp_path / "docs" / "evaluation_handoff_note.md"

    written_path = write_evaluation_handoff_note(output_path)

    assert written_path == output_path
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")

    assert "# Evaluation Module Handoff Note" in content
    assert "## Interview Explanation" in content


def test_write_evaluation_handoff_note_accepts_custom_content(tmp_path):
    output_path = tmp_path / "docs" / "custom_handoff.md"

    write_evaluation_handoff_note(
        output_path,
        content="# Custom Handoff\n",
    )

    assert output_path.read_text(encoding="utf-8") == "# Custom Handoff\n"
