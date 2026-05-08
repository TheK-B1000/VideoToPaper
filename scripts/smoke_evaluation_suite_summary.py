from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Expected JSON file not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def status_label(value: Optional[bool]) -> str:
    if value is True:
        return "PASS"
    if value is False:
        return "FAIL"
    return "N/A"


def render_suite_summary(output_dir: Path) -> str:
    passing_dir = output_dir / "passing"
    unpublishable_dir = output_dir / "unpublishable"
    malformed_dir = output_dir / "malformed"

    passing_audit = load_json(passing_dir / "audit_report.json")
    passing_index = load_json(passing_dir / "evaluation_artifact_index.json")

    unpublishable_audit = load_json(unpublishable_dir / "bad_audit_report.json")
    unpublishable_index = load_json(
        unpublishable_dir / "bad_evaluation_artifact_index.json"
    )

    malformed_validation = load_json(malformed_dir / "validation_report.json")
    malformed_index = load_json(malformed_dir / "evaluation_artifact_index.json")

    unpublishable_decision = unpublishable_audit.get(
        "publishability_decision",
        {},
    )

    malformed_errors = malformed_validation.get("errors", [])

    lines = [
        "# Evaluation Smoke Suite Summary",
        "",
        "## Scenario Results",
        "",
        "| Scenario | Structural Validity | Publishability | Expected Outcome |",
        "| --- | --- | --- | --- |",
        (
            f"| Passing artifact | {status_label(passing_index.get('valid'))} | "
            f"{status_label(passing_audit.get('publishable'))} | Passes evaluation |"
        ),
        (
            f"| Unpublishable artifact | {status_label(unpublishable_index.get('valid'))} | "
            f"{status_label(unpublishable_audit.get('publishable'))} | Fails publishability gates |"
        ),
        (
            f"| Malformed artifact | {status_label(malformed_index.get('valid'))} | "
            f"{status_label(malformed_index.get('publishable'))} | Fails validation before audit |"
        ),
        "",
        "## Blocking Axes For Unpublishable Artifact",
        "",
    ]

    blocking_axes = unpublishable_decision.get("blocking_axes", [])
    if blocking_axes:
        lines.extend(f"- {axis}" for axis in blocking_axes)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Validation Errors For Malformed Artifact",
            "",
        ]
    )

    if malformed_errors:
        lines.extend(f"- {error}" for error in malformed_errors)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Output Folders",
            "",
            f"- Passing: `{passing_dir}`",
            f"- Unpublishable: `{unpublishable_dir}`",
            f"- Malformed: `{malformed_dir}`",
        ]
    )

    return "\n".join(lines).strip() + "\n"


def write_suite_summary(
    output_dir: Path,
    summary_path: Path,
) -> Path:
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    summary = render_suite_summary(output_dir)
    summary_path.write_text(summary, encoding="utf-8")

    return summary_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a Markdown summary for the evaluation smoke suite."
    )

    parser.add_argument(
        "--output-dir",
        default="data/outputs/smoke_evaluation_suite",
        help="Directory containing passing, unpublishable, and malformed smoke outputs.",
    )

    parser.add_argument(
        "--summary-path",
        default="data/outputs/smoke_evaluation_suite/summary.md",
        help="Path where the Markdown smoke suite summary should be written.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    summary_path = Path(args.summary_path)

    written_path = write_suite_summary(
        output_dir=output_dir,
        summary_path=summary_path,
    )

    print(f"Smoke suite summary written to: {written_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())