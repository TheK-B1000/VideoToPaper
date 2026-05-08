from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.evaluation.paper_artifact_exporter import (
    build_paper_artifact,
    write_paper_artifact,
)
from src.evaluation.paper_artifact_validator import validate_paper_artifact


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Input JSON not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export evaluator-ready paper artifact JSON."
    )

    parser.add_argument(
        "--claims",
        required=True,
        help="Path to claims JSON. Expected shape: list or {'claims': [...]}",
    )

    parser.add_argument(
        "--speaker-perspective",
        required=True,
        help="Path to speaker perspective JSON.",
    )

    parser.add_argument(
        "--adjudications",
        required=True,
        help="Path to adjudications JSON. Expected shape: list or {'adjudications': [...]}",
    )

    parser.add_argument(
        "--evidence-records",
        required=True,
        help="Path to evidence records JSON. Expected shape: list or {'evidence_records': [...]}",
    )

    parser.add_argument(
        "--references",
        required=False,
        help="Optional references JSON. Expected shape: list or {'references': [...]}",
    )

    parser.add_argument(
        "--rendered-clips",
        required=False,
        help="Optional rendered clips JSON. Expected shape: list or {'rendered_clips': [...]}",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Path where the paper artifact JSON should be written.",
    )

    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Write the artifact without validating the evaluator contract.",
    )

    return parser


def _unwrap_list(payload: Any, key: str) -> list[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        return payload[key]

    raise ValueError(f"Expected a list or an object containing list key: {key}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    claims_payload = load_json(Path(args.claims))
    speaker_perspective = load_json(Path(args.speaker_perspective))
    adjudications_payload = load_json(Path(args.adjudications))
    evidence_payload = load_json(Path(args.evidence_records))

    references = None
    if args.references:
        references = _unwrap_list(load_json(Path(args.references)), "references")

    rendered_clips = None
    if args.rendered_clips:
        rendered_clips = _unwrap_list(
            load_json(Path(args.rendered_clips)), "rendered_clips"
        )

    artifact = build_paper_artifact(
        claims=_unwrap_list(claims_payload, "claims"),
        speaker_perspective=speaker_perspective,
        adjudications=_unwrap_list(adjudications_payload, "adjudications"),
        evidence_records=_unwrap_list(evidence_payload, "evidence_records"),
        references=references,
        rendered_clips=rendered_clips,
    )

    if not args.skip_validation:
        validate_paper_artifact(artifact).raise_if_invalid()

    written_path = write_paper_artifact(
        paper_artifact=artifact,
        output_path=Path(args.output),
    )

    print(f"Paper artifact written to: {written_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
