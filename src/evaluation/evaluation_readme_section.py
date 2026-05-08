from __future__ import annotations

from pathlib import Path
from typing import Optional, Union


def render_evaluation_readme_section() -> str:
    """
    Render a README-ready Markdown section describing the evaluation system.
    """
    return """## Paper Evaluation System

The evaluation system verifies generated inquiry papers as monitored quality gates, not ad-hoc checks.

It evaluates four publishability axes:

| Axis | What It Checks |
| --- | --- |
| Steelman accuracy | Speaker-perspective assertions are anchored to verbatim claims, with qualification preservation and hedge drift checks. |
| Evidence balance | Strong verdicts are rejected when retrieval is skewed. |
| Citation integrity | Rendered references resolve to retrieved evidence records. |
| Clip-anchor accuracy | Rendered clip timestamps stay within configured anchor tolerance. |

### Generate Sample Artifacts

```bash
python main.py --stage sample_artifact \\
  --output data/outputs/sample_paper_artifact.json \\
  --publishable
python main.py --stage sample_artifact \\
  --output data/outputs/bad_sample_paper_artifact.json \\
  --unpublishable
```

### Run Smoke Suite

```bash
python scripts/smoke_evaluation_suite.py \\
  --output-dir data/outputs/smoke_evaluation_suite \\
  --run-prefix local_eval_suite
```

The smoke suite verifies three scenarios:

- A valid publishable artifact passes.
- A structurally valid but unpublishable artifact fails publishability gates.
- A malformed artifact fails validation before audit generation.

The suite also writes:

`data/outputs/smoke_evaluation_suite/summary.md`
"""


def write_evaluation_readme_section(
    output_path: Union[str, Path],
    *,
    section: Optional[str] = None,
) -> Path:
    """
    Write a generated evaluation README section to disk.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(section or render_evaluation_readme_section(), encoding="utf-8")
    return path