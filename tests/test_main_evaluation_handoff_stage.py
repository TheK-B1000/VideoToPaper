from main import main


def test_main_can_run_evaluation_handoff_stage(tmp_path):
    output_path = tmp_path / "evaluation_handoff_note.md"

    exit_code = main(
        [
            "--stage",
            "evaluation_handoff",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")

    assert "# Evaluation Module Handoff Note" in content
    assert "## Next Engineering Step" in content
