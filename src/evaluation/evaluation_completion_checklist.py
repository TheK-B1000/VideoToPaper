from __future__ import annotations

from pathlib import Path
from typing import Optional, Union


def render_evaluation_completion_checklist() -> str:
    """
    Render a Markdown checklist for closing the evaluation module.
    """
    return """# Evaluation Module Completion Checklist

Use this checklist before closing the evaluation module.

## Code Artifacts

- [ ] Four-axis evaluation harness exists.
- [ ] Audit report writer exists.
- [ ] Audit summary writer exists.
- [ ] Publishability gate exists.
- [ ] Paper artifact validator exists.
- [ ] Validation report writer exists.
- [ ] Validation summary writer exists.
- [ ] Evaluation manifest writer exists.
- [ ] Evaluation artifact index exists.
- [ ] Evaluation CLI is wired into the main stage runner.
- [ ] Sample artifact CLI is wired into the main stage runner.
- [ ] Paper artifact exporter exists.
- [ ] Paper artifact export CLI is wired into the main stage runner.
- [ ] Export-and-evaluate pipeline exists.
- [ ] Assembler fixture generator exists.
- [ ] Export-and-evaluate smoke script exists.
- [ ] README documentation generator exists.
- [ ] Development log generator exists.

## Test Coverage

- [ ] Clean paper artifact passes evaluation.
- [ ] Structurally valid but unpublishable artifact fails publishability gates.
- [ ] Malformed artifact fails validation before audit generation.
- [ ] Audit report JSON is written.
- [ ] Audit summary Markdown is written.
- [ ] Validation report JSON is written for malformed artifacts.
- [ ] Validation summary Markdown is written for malformed artifacts.
- [ ] Manifest JSON records run metadata.
- [ ] Artifact index JSON records all produced artifacts.
- [ ] Config file controls evaluation outputs.
- [ ] CLI paths can override config paths.
- [ ] Main stage runner can execute evaluation.
- [ ] Main stage runner can generate sample artifacts.
- [ ] Assembler-style fixture files can be exported into `paper_artifact.json`.
- [ ] Exported paper artifacts pass structural validation.
- [ ] Export-and-evaluate pipeline produces audit artifacts.
- [ ] Export-and-evaluate smoke test passes.
- [ ] Module status report tracks export bridge artifacts.
- [ ] README docs generator writes Markdown.
- [ ] Development log generator writes Markdown.

## Smoke Commands

Run the full automated smoke suite:

```bash
python scripts/smoke_evaluation_suite.py \
  --output-dir data/outputs/smoke_evaluation_suite \
  --run-prefix local_eval_suite
```

Run the negative publishability smoke script:

```bash
python scripts/smoke_evaluation_failure.py \
  --output-dir data/outputs/smoke_evaluation_failure \
  --run-prefix local_eval_failure
```

Run the malformed-artifact validation-failure smoke script:

```bash
python scripts/smoke_evaluation_validation_failure.py \
  --output-dir data/outputs/smoke_evaluation_validation_failure \
  --run-prefix local_eval_validation_failure
```

Run the export-and-evaluate bridge smoke test:

```bash
python scripts/smoke_export_and_evaluate.py \
  --output-dir data/outputs/smoke_export_and_evaluate \
  --run-id export_eval_smoke_001
```

## Manual Commands

Generate assembler-style fixtures:

```bash
python main.py --stage assembler_fixture \
  --output-dir data/outputs/assembler_fixture
```

Export and evaluate assembler-style fixtures:

```bash
python main.py --stage export_and_evaluate \
  --claims data/outputs/assembler_fixture/claims.json \
  --speaker-perspective data/outputs/assembler_fixture/speaker_perspective.json \
  --adjudications data/outputs/assembler_fixture/adjudications.json \
  --evidence-records data/outputs/assembler_fixture/evidence_records.json \
  --paper-artifact data/outputs/assembler_fixture/paper_artifact.json \
  --config-path configs/evaluation_config.json \
  --run-id assembler_fixture_eval_001 \
  --print-summary
```

## Close Criteria

- [ ] All checklist items above are reviewed and intentionally marked complete/incomplete.
- [ ] A final smoke run has been captured and archived.
- [ ] The evaluation README section reflects the current workflow.
- [ ] The development log reflects what was built and what remains.
"""


def write_evaluation_completion_checklist(
    output_path: Union[str, Path],
    checklist_markdown: Optional[str] = None,
) -> Path:
    """
    Write a Markdown completion checklist for the evaluation module.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rendered = (
        checklist_markdown
        if checklist_markdown is not None
        else render_evaluation_completion_checklist()
    )
    path.write_text(rendered, encoding="utf-8")

    return path