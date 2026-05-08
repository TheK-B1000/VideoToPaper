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