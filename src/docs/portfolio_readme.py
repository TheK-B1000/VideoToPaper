from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_FEATURES = [
    "YouTube source ingestion with provenance and embed-ready timing metadata",
    "Transcript chunking with offset preservation",
    "Argument and anchor-moment extraction",
    "Verbatim claim inventory with claim-type routing",
    "Speaker steelmanning grounded in source quotes",
    "Tiered external evidence retrieval",
    "Balanced evidence integration",
    "Interactive HTML paper assembly with embedded source clips",
    "Vanilla JavaScript evidence components",
    "Four-axis evaluation for steelman accuracy, evidence balance, citation integrity, and clip-anchor accuracy",
    "Streamlit Inquiry Studio for operating the engine",
]


DEFAULT_TECH_STACK = [
    "Python",
    "FastAPI",
    "Streamlit",
    "PostgreSQL-compatible schema",
    "Vanilla JavaScript",
    "HTML/CSS",
    "pytest",
    "JSON artifacts",
]


@dataclass(frozen=True)
class PortfolioReadme:
    title: str
    content: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
        }


def build_portfolio_readme(
    *,
    project_name: str = "The Inquiry Engine",
    features: list[str] | None = None,
    tech_stack: list[str] | None = None,
) -> PortfolioReadme:
    selected_features = features or DEFAULT_FEATURES
    selected_tech_stack = tech_stack or DEFAULT_TECH_STACK

    content = f"""# {project_name}

{project_name} is an interactive video-to-paper pipeline that turns a YouTube video into a research-style HTML paper with playable source citations, evidence trails, and audit reports.

The system is built around one core idea: if the source is video, the output should preserve the ability to verify the exact source moment. Every verbatim citation should be one click away from the speaker saying it.

## What it does

{_markdown_bullets(selected_features)}

## Why this project exists

Long-form video often contains serious claims, but those claims are difficult to verify while watching. A speaker may reference studies, historical events, technical concepts, or policy claims without providing a clean citation trail.

The Inquiry Engine helps solve that problem by:

- identifying the claims a speaker makes
- preserving the original video context
- retrieving external evidence
- presenting balanced support, contradiction, and qualification
- assembling the result into an interactive HTML paper
- evaluating whether the output is trustworthy enough to inspect or share

## Core design principles

### 1. Format-matched output

The project emits interactive HTML instead of a static PDF because the source material is video. A static document can quote a speaker, but it cannot preserve the source moment. This system uses embedded YouTube clips so the reader can verify the quote directly.

### 2. Charitable reconstruction

The speaker's argument is reconstructed in a way the speaker would recognize. The goal is not to dunk, debunk, or flatten nuance. The system tries to steelman first, then evaluate.

### 3. Balanced evidence retrieval

For empirical claims, the evidence layer searches for support, contradiction, complication, and qualification. Cherry-picking is treated as a failure mode, not a feature.

### 4. Audit-grade traceability

The pipeline produces artifacts that can be inspected: source records, claim inventories, retrieval trails, generated papers, and evaluation reports.

## Architecture overview

```text
YouTube Video
  ↓
Source + Transcript Ingestion
  ↓
Argument Structure + Anchor Moments
  ↓
Claim Inventory
  ↓
Speaker Steelman
  ↓
External Evidence Retrieval
  ↓
Evidence Integration
  ↓
Interactive HTML Paper
  ↓
Four-Axis Evaluation
  ↓
Inquiry Studio
  ↓
Operator Workflows + Reruns + Audits + Status
```

## Tech stack

{_markdown_bullets(selected_tech_stack)}

## Demo workflow

1. Pick a YouTube source.
2. Run the pipeline from ingestion through evaluation.
3. Open the generated HTML paper and verify clip-anchored citations.
4. Review the audit report and validation summaries.
5. Use Inquiry Studio for reruns, progress checks, backend submission, and imports.

## Portfolio highlights

- End-to-end applied AI system with traceable artifacts.
- Practical frontend + backend integration path.
- Built-in quality gates, validation, and publishability checks.
- Strong emphasis on source integrity and evidence balance.

## Repository artifacts

- `docs/engineering_decisions.md` explains major architecture choices and tradeoffs.
- `docs/inquiry_studio.md` documents the operator surface and workflows.
- `data/processed` and `data/outputs` contain pipeline artifacts.
- `logs/runs` and `logs/budget` preserve runtime and governance context.

## Closing

{project_name} is designed to be inspectable, not mystical. The portfolio value is not just model usage, but disciplined pipeline engineering: provenance, evaluability, and operator control.
"""

    return PortfolioReadme(
        title=f"{project_name} Portfolio README",
        content=content,
    )


def write_portfolio_readme(
    *,
    output_path: str | Path = "docs/portfolio_readme.md",
    project_name: str = "The Inquiry Engine",
    features: list[str] | None = None,
    tech_stack: list[str] | None = None,
) -> Path:
    readme = build_portfolio_readme(
        project_name=project_name,
        features=features,
        tech_stack=tech_stack,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(readme.content, encoding="utf-8")
    return path


def _markdown_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)