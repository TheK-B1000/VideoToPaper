from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union


@dataclass(frozen=True)
class EvaluationDevLog:
    title: str
    built: List[str] = field(default_factory=list)
    tested: List[str] = field(default_factory=list)
    learned: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    interview_explanation: Optional[str] = None


def _render_bullets(items: List[str], fallback: str = "Nothing recorded.") -> str:
    if not items:
        return f"- {fallback}"

    return "\n".join(f"- {item}" for item in items)


def render_evaluation_dev_log(log: EvaluationDevLog) -> str:
    """
    Render a Markdown development log for the evaluation system.

    This is meant for weekly reflection, project documentation, and portfolio notes.
    """
    interview_explanation = (
        log.interview_explanation
        if log.interview_explanation
        else "No interview explanation recorded."
    )

    return f"""# {log.title}

## What I Built

{_render_bullets(log.built)}

## What I Tested

{_render_bullets(log.tested)}

## What I Learned

{_render_bullets(log.learned)}

## Next Steps

{_render_bullets(log.next_steps)}

## Interview Explanation

{interview_explanation}
"""


def build_default_evaluation_dev_log() -> EvaluationDevLog:
    """
    Build a ready-to-use development log for the evaluation system.
    """
    return EvaluationDevLog(
        title="Evaluation Harness Development Log",
        built=[
            "Implemented a four-axis evaluation harness for steelman accuracy, evidence balance, citation integrity, and clip-anchor accuracy.",
            "Added audit report and audit summary outputs for machine-readable and human-readable inspection.",
            "Added artifact validation so malformed paper artifacts stop before audit generation.",
            "Added validation reports and validation summaries for structural diagnostics.",
            "Added manifests and artifact indexes to make each evaluation run traceable.",
            "Added sample artifact generation and smoke scripts for passing, unpublishable, and malformed artifacts.",
            "Added a paper artifact exporter that converts assembler-style output files into the evaluator-ready artifact contract.",
            "Added an export-and-evaluate pipeline that exports paper artifacts and immediately runs evaluation.",
            "Added assembler-style fixtures and an export-and-evaluate smoke test to verify the bridge from paper assembly output to audit artifacts.",
            "Added README-ready documentation for the evaluation system.",
        ],
        tested=[
            "Verified clean paper artifacts produce publishable audit reports.",
            "Verified structurally valid but unpublishable artifacts fail the publishability gate.",
            "Verified malformed artifacts produce validation diagnostics and do not produce audit reports.",
            "Verified assembler-style JSON files can be exported into a valid paper artifact.",
            "Verified the export-and-evaluate bridge produces paper artifacts, audit reports, summaries, manifests, and artifact indexes.",
            "Verified CLI, stage runner, config loader, smoke scripts, and summary generation paths.",
        ],
        learned=[
            "Validation and evaluation should be separate because malformed input is different from an unpublishable paper.",
            "Audit artifacts are more useful when they exist in both JSON and Markdown forms.",
            "A smoke suite should test success, expected publishability failure, and validation failure.",
            "The evaluator needs a stable artifact contract so upstream paper assembly can change internally without breaking audit logic.",
            "Bridge smoke tests are valuable because they verify integration boundaries, not just isolated modules.",
            "The evaluation layer is part of the product, not just a test utility.",
        ],
        next_steps=[
            "Replace assembler fixtures with the real paper assembler output once the assembler emits the required JSON parts.",
            "Add richer metric details once real generated papers contain full citation and retrieval payloads.",
            "Surface audit summaries in the operator interface later.",
        ],
        interview_explanation=(
            "I built the evaluation layer as a quality gate for generated research papers. "
            "Instead of assuming the paper is trustworthy because it reads well, the system checks four explicit properties: "
            "whether the speaker was represented accurately, whether the evidence retrieval was balanced, whether citations resolve to real retrieved sources, "
            "and whether embedded clips match the quoted moments. I also separated structural validation from publishability evaluation so malformed artifacts are caught before audit generation."
        ),
    )


def write_evaluation_dev_log(
    output_path: Union[str, Path],
    log: Optional[EvaluationDevLog] = None,
) -> Path:
    """
    Write a Markdown development log for the evaluation system.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rendered = render_evaluation_dev_log(
        log if log is not None else build_default_evaluation_dev_log()
    )

    path.write_text(rendered, encoding="utf-8")

    return path