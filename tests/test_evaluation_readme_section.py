from src.evaluation.evaluation_readme_section import render_evaluation_readme_section


def test_render_evaluation_readme_section_includes_smoke_workflow():
    section = render_evaluation_readme_section()

    assert "## Paper Evaluation System" in section
    assert "python main.py --stage sample_artifact" in section
    assert "python scripts/smoke_evaluation_suite.py" in section
    assert "A valid publishable artifact passes." in section
    assert (
        "A structurally valid but unpublishable artifact fails publishability gates."
        in section
    )
    assert "A malformed artifact fails validation before audit generation." in section
    assert "`data/outputs/smoke_evaluation_suite/summary.md`" in section
