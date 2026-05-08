from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_DECISIONS = [
    {
        "title": "Interactive HTML instead of static PDF",
        "decision": (
            "The Inquiry Engine emits interactive HTML papers because the source "
            "material is video. Static text cannot preserve the reader's ability "
            "to verify a speaker quote at the exact source moment."
        ),
        "rationale": (
            "Every verbatim citation can be paired with a YouTube embed cued to "
            "the cited timestamp. This makes the output format match the source medium."
        ),
        "tradeoffs": [
            "HTML is less traditional than PDF for academic-style papers.",
            "Browser compatibility and local-file behavior must be considered.",
            "The payoff is stronger citation verification and better reader trust.",
        ],
    },
    {
        "title": "Embed-only video citation",
        "decision": (
            "The system uses YouTube embed URLs instead of downloading, clipping, "
            "or re-hosting video content."
        ),
        "rationale": (
            "This preserves attribution, avoids redistributing creator content, "
            "and keeps the source video tied to the original platform context."
        ),
        "tradeoffs": [
            "Generated papers depend on YouTube availability.",
            "Offline playback is not supported.",
            "The copyright posture is safer and cleaner.",
        ],
    },
    {
        "title": "Verbatim source layer separate from cleaned processing layer",
        "decision": (
            "Character offsets are based on raw source text, while cleaned text is "
            "used only for readability, chunking, summarization, and processing."
        ),
        "rationale": (
            "Cleaning transcript text can change whitespace, remove filler tokens, "
            "or alter offsets. Keeping raw offsets tied to raw source text protects "
            "citation integrity."
        ),
        "tradeoffs": [
            "The pipeline has to carry both raw and cleaned text.",
            "Data models are slightly more complex.",
            "Citation verification becomes much more reliable.",
        ],
    },
    {
        "title": "Balanced retrieval as a monitored property",
        "decision": (
            "The evidence retrieval stage explicitly searches for supporting, "
            "contrary, qualifying, and complicating evidence."
        ),
        "rationale": (
            "The system is designed for inquiry, not verdict generation. Monitoring "
            "balance helps prevent cherry-picking."
        ),
        "tradeoffs": [
            "Retrieval takes more queries and more time.",
            "Some claims may have limited contrary evidence.",
            "The output becomes more trustworthy and intellectually honest.",
        ],
    },
    {
        "title": "Operator Studio before final polish",
        "decision": (
            "A Streamlit-based Inquiry Studio was built before final portfolio polish."
        ),
        "rationale": (
            "The system needed a practical operator surface for creating requests, "
            "tracking runs, inspecting audits, opening papers, and managing reruns."
        ),
        "tradeoffs": [
            "Streamlit is less customizable than a custom React frontend.",
            "It is faster to build and easier to maintain during research development.",
            "The system becomes usable earlier.",
        ],
    },
]


@dataclass(frozen=True)
class EngineeringDecision:
    title: str
    decision: str
    rationale: str
    tradeoffs: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "decision": self.decision,
            "rationale": self.rationale,
            "tradeoffs": self.tradeoffs,
        }


@dataclass(frozen=True)
class EngineeringDecisionsDocument:
    title: str
    content: str
    decisions: list[EngineeringDecision]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "decisions": [decision.to_dict() for decision in self.decisions],
        }


def build_engineering_decisions_document(
    decisions: list[EngineeringDecision] | None = None,
) -> EngineeringDecisionsDocument:
    selected_decisions = decisions or [
        EngineeringDecision(
            title=item["title"],
            decision=item["decision"],
            rationale=item["rationale"],
            tradeoffs=list(item["tradeoffs"]),
        )
        for item in DEFAULT_DECISIONS
    ]

    content = "\n\n".join(
        [
            "# Engineering Decisions — The Inquiry Engine",
            _build_intro(),
            *[
                _render_decision(index + 1, decision)
                for index, decision in enumerate(selected_decisions)
            ],
            _build_closing_section(),
        ]
    )

    return EngineeringDecisionsDocument(
        title="Engineering Decisions — The Inquiry Engine",
        content=content,
        decisions=selected_decisions,
    )


def write_engineering_decisions_document(
    *,
    output_path: str | Path = "docs/engineering_decisions.md",
    decisions: list[EngineeringDecision] | None = None,
) -> Path:
    document = build_engineering_decisions_document(decisions)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document.content, encoding="utf-8")
    return path


def _build_intro() -> str:
    return """## Purpose

This document records the major engineering decisions behind the Inquiry Engine.

The project is not only a transcript summarizer. It is an interactive, evidence-grounded video-to-paper pipeline. The decisions below explain how the system preserves citation integrity, balances evidence, respects the source medium, and remains operable as a real research tool."""


def _render_decision(index: int, decision: EngineeringDecision) -> str:
    tradeoff_lines = "\n".join(f"- {tradeoff}" for tradeoff in decision.tradeoffs)

    return f"""## {index}. {decision.title}

### Decision

{decision.decision}

### Rationale

{decision.rationale}

### Tradeoffs

{tradeoff_lines}"""


def _build_closing_section() -> str:
    return """## Summary

The central design pattern is simple: preserve the source, reconstruct the speaker charitably, retrieve balanced evidence, render the result in a format that preserves video context, and evaluate the output before trusting it.

The system favors traceability over flash. Every major feature exists to help the reader verify, inspect, or rerun the inquiry."""
