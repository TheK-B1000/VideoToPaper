from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Union

from src.evaluation.evaluation_architecture_doc import write_evaluation_architecture_doc
from src.evaluation.evaluation_completion_checklist import (
    write_evaluation_completion_checklist,
)
from src.evaluation.evaluation_dev_log import write_evaluation_dev_log
from src.evaluation.evaluation_readme_section import write_evaluation_readme_section


@dataclass(frozen=True)
class EvaluationCloseoutBundle:
    readme_section_path: Path
    architecture_doc_path: Path
    dev_log_path: Path
    checklist_path: Path

    def to_dict(self) -> Dict[str, str]:
        return {
            "readme_section_path": str(self.readme_section_path),
            "architecture_doc_path": str(self.architecture_doc_path),
            "dev_log_path": str(self.dev_log_path),
            "checklist_path": str(self.checklist_path),
        }


def write_evaluation_closeout_bundle(
    output_dir: Union[str, Path],
) -> EvaluationCloseoutBundle:
    """
    Write the closeout documentation bundle for the evaluation system.

    This creates the README section, architecture document, development log,
    and completion checklist in one folder.
    """
    base_dir = Path(output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    readme_section_path = write_evaluation_readme_section(
        base_dir / "evaluation_readme_section.md"
    )
    architecture_doc_path = write_evaluation_architecture_doc(
        base_dir / "evaluation_architecture.md"
    )
    dev_log_path = write_evaluation_dev_log(
        base_dir / "evaluation_dev_log.md"
    )
    checklist_path = write_evaluation_completion_checklist(
        base_dir / "evaluation_completion_checklist.md"
    )

    return EvaluationCloseoutBundle(
        readme_section_path=readme_section_path,
        architecture_doc_path=architecture_doc_path,
        dev_log_path=dev_log_path,
        checklist_path=checklist_path,
    )
