from __future__ import annotations

from pathlib import Path
from typing import Optional, Union


def render_evaluation_architecture_doc() -> str:
    """
    Render a Markdown architecture/data-flow sketch for the evaluation module.
    """
    return """# Evaluation System Architecture

This document explains how generated paper artifacts move through validation, evaluation, audit reporting, and artifact indexing.

## Purpose

The evaluation system acts as the quality gate for generated inquiry papers. It answers two different questions:

1. Is the paper artifact structurally valid?
2. If valid, is the paper publishable?

Those questions are intentionally separated. A malformed artifact should fail validation before any audit report is produced. A structurally valid artifact may still fail publishability if it has weak evidence balance, broken citations, or clip-anchor drift.

## Data Flow

```text
Assembler Output JSON Parts
        |
        v
Paper Artifact Exporter
        |
        v
Evaluator-Ready Paper Artifact JSON
        |
        v
Paper Artifact Validator
        |
        |-- invalid --> validation_report.json
        |              validation_summary.md
        |              evaluation_artifact_index.json
        |
        v
Four-Axis Evaluation Harness
        |
        v
Publishability Gate
        |
        v
audit_report.json
audit_summary.md
evaluation_manifest.json
evaluation_artifact_index.json
```

## Validation Layer

The validation layer checks the artifact contract before evaluation begins.

It verifies:

- Required top-level fields exist.
- Claims have IDs, verbatim quotes, and anchor clips.
- Clip ranges are numeric and valid.
- Speaker-perspective anchors reference known claims.
- Adjudications reference known claims.
- References resolve to known evidence records.
- Rendered clips reference known claims.

If validation fails, evaluation stops. No audit report, audit summary, or manifest should be produced.

## Export Layer

The export layer converts assembler-style output files into the evaluator-ready artifact contract.

Expected assembler-style inputs:

- `claims.json`
- `speaker_perspective.json`
- `adjudications.json`
- `evidence_records.json`
- Optional `references.json`
- Optional `rendered_clips.json`

The exporter writes:

- `paper_artifact.json`

This artifact becomes the input to validation and evaluation.

## Evaluation Layer

The evaluation harness checks four publishability axes:

| Axis | Failure Mode It Guards Against |
| --- | --- |
| Steelman accuracy | The speaker is misrepresented or unsupported assertions appear in the speaker perspective. |
| Evidence balance | The paper presents a strong conclusion despite skewed retrieval. |
| Citation integrity | Rendered references do not resolve to retrieved evidence records. |
| Clip-anchor accuracy | Embedded clips drift away from the claimed source moment. |

## Publishability Decision

The publishability gate converts raw metric results into a human-readable decision.

It produces:

- `publishable`
- `blocking_axes`
- `reasons`

This makes the evaluator useful for humans, not just scripts.

## Output Artifacts

### Successful Validation and Evaluation

- `audit_report.json`
- `audit_summary.md`
- `evaluation_manifest.json`
- `evaluation_artifact_index.json`

### Validation Failure

- `validation_report.json`
- `validation_summary.md`
- `evaluation_artifact_index.json`

## CLI Entry Points

Run evaluation:

```bash
python main.py --stage evaluation \
  --paper-artifact data/outputs/sample_paper_artifact.json \
  --config-path configs/evaluation_config.json \
  --run-id local_eval_001 \
  --print-summary
```

Export and evaluate assembler-style output:

```bash
python main.py --stage export_and_evaluate \
  --claims data/outputs/assembler_fixture/claims.json \
  --speaker-perspective data/outputs/assembler_fixture/speaker_perspective.json \
  --adjudications data/outputs/assembler_fixture/adjudications.json \
  --evidence-records data/outputs/assembler_fixture/evidence_records.json \
  --paper-artifact data/outputs/assembler_fixture/paper_artifact.json \
  --config-path configs/evaluation_config.json \
  --run-id assembler_eval_001 \
  --print-summary
```

Generate sample artifacts:

```bash
python main.py --stage sample_artifact \
  --output data/outputs/sample_paper_artifact.json \
  --publishable
```

Run smoke suite:

```bash
python scripts/smoke_evaluation_suite.py \
  --output-dir data/outputs/smoke_evaluation_suite \
  --run-prefix local_eval_suite
```

## Design Rationale

The system separates validation from evaluation because malformed input and unpublishable output are different engineering problems.

Malformed input means the artifact contract is broken.

Unpublishable output means the artifact is shaped correctly, but it fails one or more quality gates.

That distinction makes debugging cleaner, audit artifacts more honest, and the overall pipeline easier to explain.
"""


def write_evaluation_architecture_doc(
    output_path: Union[str, Path],
    content: Optional[str] = None,
) -> Path:
    """
    Write the evaluation architecture/data-flow document to disk.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rendered = content if content is not None else render_evaluation_architecture_doc()
    path.write_text(rendered, encoding="utf-8")

    return path
