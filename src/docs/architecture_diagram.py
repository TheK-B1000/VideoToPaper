from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ARCHITECTURE_NODES = [
    ("video", "YouTube Video"),
    ("ingestion", "Source + Transcript Ingestion"),
    ("argument", "Argument Structure + Anchor Moments"),
    ("claims", "Claim Inventory"),
    ("steelman", "Speaker Steelman"),
    ("retrieval", "External Evidence Retrieval"),
    ("integration", "Evidence Integration"),
    ("html", "Interactive HTML Paper"),
    ("evaluation", "Four-Axis Evaluation"),
    ("studio", "Inquiry Studio"),
]


DEFAULT_ARCHITECTURE_EDGES = [
    ("video", "ingestion", "source URL, metadata, transcript"),
    ("ingestion", "argument", "clean transcript + raw offsets"),
    ("argument", "claims", "chunks + anchor moments"),
    ("claims", "steelman", "verbatim claims"),
    ("claims", "retrieval", "empirical claims"),
    ("retrieval", "integration", "evidence records"),
    ("steelman", "html", "speaker perspective blocks"),
    ("integration", "html", "claim adjudications"),
    ("html", "evaluation", "paper artifact"),
    ("claims", "evaluation", "claim anchors"),
    ("retrieval", "evaluation", "citation records"),
    ("evaluation", "studio", "audit report"),
    ("html", "studio", "generated paper"),
    ("studio", "ingestion", "run request"),
]


@dataclass(frozen=True)
class ArchitectureNode:
    node_id: str
    label: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
        }


@dataclass(frozen=True)
class ArchitectureEdge:
    source: str
    target: str
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "label": self.label,
        }


@dataclass(frozen=True)
class ArchitectureDiagram:
    title: str
    mermaid: str
    markdown: str
    nodes: list[ArchitectureNode]
    edges: list[ArchitectureEdge]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "mermaid": self.mermaid,
            "markdown": self.markdown,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }


def build_architecture_diagram(
    *,
    title: str = "The Inquiry Engine Architecture",
    nodes: list[ArchitectureNode] | None = None,
    edges: list[ArchitectureEdge] | None = None,
) -> ArchitectureDiagram:
    selected_nodes = nodes or [
        ArchitectureNode(node_id=node_id, label=label)
        for node_id, label in DEFAULT_ARCHITECTURE_NODES
    ]

    selected_edges = edges or [
        ArchitectureEdge(source=source, target=target, label=label)
        for source, target, label in DEFAULT_ARCHITECTURE_EDGES
    ]

    mermaid = render_mermaid_diagram(
        nodes=selected_nodes,
        edges=selected_edges,
    )

    markdown = "\n\n".join(
        [
            f"# {title}",
            "This diagram shows the main module boundaries and data flow for the Inquiry Engine.",
            "```mermaid",
            mermaid,
            "```",
            "## Reading the diagram",
            (
                "The system begins with a YouTube source, preserves transcript provenance and raw offsets, "
                "extracts argument structure and claim anchors, retrieves external evidence, assembles an "
                "interactive HTML paper, evaluates the output, and exposes the workflow through Inquiry Studio."
            ),
        ]
    )

    return ArchitectureDiagram(
        title=title,
        mermaid=mermaid,
        markdown=markdown,
        nodes=selected_nodes,
        edges=selected_edges,
    )


def render_mermaid_diagram(
    *,
    nodes: list[ArchitectureNode],
    edges: list[ArchitectureEdge],
) -> str:
    node_lines = [
        f'    {node.node_id}["{_escape_mermaid_label(node.label)}"]'
        for node in nodes
    ]

    edge_lines = []

    for edge in edges:
        if edge.label:
            edge_lines.append(
                f'    {edge.source} -->|"{_escape_mermaid_label(edge.label)}"| {edge.target}'
            )
        else:
            edge_lines.append(f"    {edge.source} --> {edge.target}")

    return "\n".join(
        [
            "flowchart TD",
            *node_lines,
            "",
            *edge_lines,
            "",
            "    classDef source fill:#f7f7f7,stroke:#555,stroke-width:1px;",
            "    classDef process fill:#eef6ff,stroke:#336699,stroke-width:1px;",
            "    classDef output fill:#f4fff0,stroke:#447744,stroke-width:1px;",
            "    class video source;",
            "    class ingestion,argument,claims,steelman,retrieval,integration,evaluation process;",
            "    class html,studio output;",
        ]
    )


def write_architecture_diagram(
    *,
    output_path: str | Path = "docs/architecture_diagram.md",
    title: str = "The Inquiry Engine Architecture",
    nodes: list[ArchitectureNode] | None = None,
    edges: list[ArchitectureEdge] | None = None,
) -> Path:
    diagram = build_architecture_diagram(
        title=title,
        nodes=nodes,
        edges=edges,
    )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(diagram.markdown, encoding="utf-8")
    return path


def write_architecture_mermaid(
    *,
    output_path: str | Path = "docs/architecture_diagram.mmd",
    nodes: list[ArchitectureNode] | None = None,
    edges: list[ArchitectureEdge] | None = None,
) -> Path:
    diagram = build_architecture_diagram(
        nodes=nodes,
        edges=edges,
    )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(diagram.mermaid, encoding="utf-8")
    return path


def _escape_mermaid_label(value: str) -> str:
    return value.replace('"', "'")