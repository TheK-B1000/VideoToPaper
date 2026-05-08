from __future__ import annotations

from pathlib import Path
from typing import Optional, Union


def render_evaluation_handoff_note() -> str:
    """
    Render a Markdown handoff note for the completed evaluation module.
    """
    return """# Evaluation Module Handoff Note

## Status

The evaluation module is ready to connect to real paper assembler output.

It now supports:

- Structural validation before evaluation.
- Four-axis publishability evaluation.
- Human-readable and machine-readable audit artifacts.
- Validation diagnostics for malformed artifacts.
- Run manifests and artifact indexes.
- Config-driven output paths.
- CLI and main-stage entry points.
- Sample artifact generation.
- Positive, negative, and malformed smoke tests.
- Closeout documentation and module status reporting.

## Verification Command

Run:

```bash
python scripts/verify_evaluation_module.py \\
  --smoke-output-dir data/outputs/smoke_evaluation_suite \\
  --docs-output-dir docs/evaluation \\
  --status-output docs/evaluation/evaluation_module_status.md \\
  --run-prefix final_eval_verify
```

Expected result:

Evaluation module verification passed.

Expected status report:

docs/evaluation/evaluation_module_status.md

The status report should say:

Module Ready: YES

## Main Entry Points

Generate a sample artifact:

```bash
python main.py --stage sample_artifact \\
  --output data/outputs/sample_paper_artifact.json \\
  --publishable
```

Run evaluation:

```bash
python main.py --stage evaluation \\
  --paper-artifact data/outputs/sample_paper_artifact.json \\
  --config-path configs/evaluation_config.json \\
  --run-id local_eval_001 \\
  --print-summary
```

Generate closeout docs:

```bash
python main.py --stage evaluation_closeout \\
  --output-dir docs/evaluation
```

## Important Design Boundary

Validation and evaluation are separate.

Validation answers:

Is this artifact structurally shaped correctly?

Evaluation answers:

Is this structurally valid artifact publishable?

A malformed artifact should produce validation diagnostics and stop before audit generation.
A structurally valid but low-quality artifact should produce audit diagnostics and fail publishability.

## Next Engineering Step

Connect the evaluator to the real paper assembler output.

The assembler should emit a paper artifact JSON with:

claims
speaker_perspective
adjudications
evidence_records
references
rendered_clips

Then call:

```python
from src.evaluation.evaluation_runner import run_paper_evaluation

result = run_paper_evaluation(
    paper_artifact=paper_artifact,
    paper_artifact_path="data/outputs/paper_artifact.json",
    audit_report_path="data/outputs/audit_report.json",
    audit_summary_path="data/outputs/audit_summary.md",
    manifest_path="data/outputs/evaluation_manifest.json",
    validation_report_path="data/outputs/validation_report.json",
    metadata={"run_id": run_id},
)
```

## Interview Explanation

I built the evaluation module as a quality gate for generated inquiry papers. It separates structural validation from publishability evaluation, then checks four explicit axes: steelman accuracy, evidence balance, citation integrity, and clip-anchor accuracy. The result is not just a pass/fail value. It produces audit reports, summaries, manifests, artifact indexes, validation diagnostics, and smoke-test evidence so the system can be inspected and defended.
"""


def write_evaluation_handoff_note(
    output_path: Union[str, Path],
    content: Optional[str] = None,
) -> Path:
    """
    Write the evaluation module handoff note to disk.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rendered = content if content is not None else render_evaluation_handoff_note()
    path.write_text(rendered, encoding="utf-8")

    return path
