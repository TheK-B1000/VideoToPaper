from pathlib import Path

from src.docs.architecture_diagram import (
    ArchitectureEdge,
    ArchitectureNode,
    build_architecture_diagram,
    render_mermaid_diagram,
    write_architecture_diagram,
    write_architecture_mermaid,
)


def test_build_architecture_diagram_contains_default_flow():
    diagram = build_architecture_diagram()

    assert diagram.title == "The Inquiry Engine Architecture"
    assert "flowchart TD" in diagram.mermaid
    assert "YouTube Video" in diagram.mermaid
    assert "Source + Transcript Ingestion" in diagram.mermaid
    assert "Interactive HTML Paper" in diagram.mermaid
    assert "Inquiry Studio" in diagram.mermaid
    assert "```mermaid" in diagram.markdown


def test_render_mermaid_diagram_with_custom_nodes_and_edges():
    nodes = [
        ArchitectureNode(node_id="a", label="Input"),
        ArchitectureNode(node_id="b", label="Output"),
    ]

    edges = [
        ArchitectureEdge(source="a", target="b", label="data"),
    ]

    mermaid = render_mermaid_diagram(nodes=nodes, edges=edges)

    assert 'a["Input"]' in mermaid
    assert 'b["Output"]' in mermaid
    assert 'a -->|"data"| b' in mermaid


def test_render_mermaid_diagram_escapes_quotes():
    nodes = [
        ArchitectureNode(node_id="a", label='Speaker "Quote"'),
        ArchitectureNode(node_id="b", label="Output"),
    ]

    edges = [
        ArchitectureEdge(source="a", target="b", label='uses "quote"'),
    ]

    mermaid = render_mermaid_diagram(nodes=nodes, edges=edges)

    assert "Speaker 'Quote'" in mermaid
    assert "uses 'quote'" in mermaid


def test_architecture_node_to_dict():
    node = ArchitectureNode(node_id="claims", label="Claim Inventory")

    assert node.to_dict() == {
        "node_id": "claims",
        "label": "Claim Inventory",
    }


def test_architecture_edge_to_dict():
    edge = ArchitectureEdge(
        source="claims",
        target="retrieval",
        label="empirical claims",
    )

    assert edge.to_dict() == {
        "source": "claims",
        "target": "retrieval",
        "label": "empirical claims",
    }


def test_write_architecture_diagram_creates_markdown_file(tmp_path: Path):
    output_path = tmp_path / "docs" / "architecture_diagram.md"

    written_path = write_architecture_diagram(output_path=output_path)

    assert written_path == output_path
    assert written_path.exists()

    content = written_path.read_text(encoding="utf-8")

    assert "# The Inquiry Engine Architecture" in content
    assert "```mermaid" in content
    assert "flowchart TD" in content


def test_write_architecture_mermaid_creates_mmd_file(tmp_path: Path):
    output_path = tmp_path / "docs" / "architecture_diagram.mmd"

    written_path = write_architecture_mermaid(output_path=output_path)

    assert written_path == output_path
    assert written_path.exists()

    content = written_path.read_text(encoding="utf-8")

    assert content.startswith("flowchart TD")
    assert "Inquiry Studio" in content