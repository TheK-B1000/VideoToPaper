from src.evaluation.evaluation_architecture_doc import (
    render_evaluation_architecture_doc,
    write_evaluation_architecture_doc,
)


def test_render_evaluation_architecture_doc_includes_major_sections():
    doc = render_evaluation_architecture_doc()

    assert "# Evaluation System Architecture" in doc
    assert "## Purpose" in doc
    assert "## Data Flow" in doc
    assert "## Validation Layer" in doc
    assert "## Evaluation Layer" in doc
    assert "## Publishability Decision" in doc
    assert "## Output Artifacts" in doc
    assert "## Design Rationale" in doc


def test_render_evaluation_architecture_doc_includes_data_flow():
    doc = render_evaluation_architecture_doc()

    assert "Generated Paper Artifact JSON" in doc
    assert "Paper Artifact Validator" in doc
    assert "Four-Axis Evaluation Harness" in doc
    assert "Publishability Gate" in doc
    assert "evaluation_artifact_index.json" in doc


def test_render_evaluation_architecture_doc_includes_four_axes():
    doc = render_evaluation_architecture_doc()

    assert "Steelman accuracy" in doc
    assert "Evidence balance" in doc
    assert "Citation integrity" in doc
    assert "Clip-anchor accuracy" in doc


def test_render_evaluation_architecture_doc_includes_commands():
    doc = render_evaluation_architecture_doc()

    assert "python main.py --stage evaluation" in doc
    assert "python main.py --stage sample_artifact" in doc
    assert "python scripts/smoke_evaluation_suite.py" in doc


def test_write_evaluation_architecture_doc_creates_markdown_file(tmp_path):
    output_path = tmp_path / "docs" / "evaluation_architecture.md"

    written_path = write_evaluation_architecture_doc(output_path)

    assert written_path == output_path
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")

    assert "# Evaluation System Architecture" in content
    assert "Generated Paper Artifact JSON" in content


def test_write_evaluation_architecture_doc_accepts_custom_content(tmp_path):
    output_path = tmp_path / "docs" / "custom_architecture.md"

    write_evaluation_architecture_doc(
        output_path,
        content="# Custom Architecture\n",
    )

    assert output_path.read_text(encoding="utf-8") == "# Custom Architecture\n"
