from src.evaluation.evaluation_completion_checklist import (
    render_evaluation_completion_checklist,
    write_evaluation_completion_checklist,
)


def test_render_evaluation_completion_checklist_contains_core_sections():
    content = render_evaluation_completion_checklist()

    assert "# Evaluation Module Completion Checklist" in content
    assert "## Code Artifacts" in content
    assert "## Test Coverage" in content
    assert "## Smoke Commands" in content
    assert "## Close Criteria" in content


def test_write_evaluation_completion_checklist_writes_markdown(tmp_path):
    output_path = tmp_path / "evaluation_completion_checklist.md"

    written_path = write_evaluation_completion_checklist(output_path)

    assert written_path == output_path
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")
    assert "# Evaluation Module Completion Checklist" in content
    assert "## Close Criteria" in content


def test_render_evaluation_completion_checklist_includes_export_bridge():
    checklist = render_evaluation_completion_checklist()

    assert "Paper artifact exporter exists." in checklist
    assert "Export-and-evaluate pipeline exists." in checklist
    assert "Assembler fixture generator exists." in checklist
    assert "python scripts/smoke_export_and_evaluate.py" in checklist
    assert "python main.py --stage export_and_evaluate" in checklist
    assert "python main.py --stage assembler_fixture" in checklist
