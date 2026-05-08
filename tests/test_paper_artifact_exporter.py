import json

import pytest

from src.evaluation.paper_artifact_exporter import (
    build_paper_artifact,
    build_references_from_evidence_records,
    build_rendered_clips_from_claims,
    load_paper_artifact,
    normalize_claims,
    normalize_evidence_records,
    write_paper_artifact,
)
from src.evaluation.paper_artifact_validator import validate_paper_artifact


def make_claims():
    return [
        {
            "claim_id": "claim_001",
            "verbatim_quote": "Balanced evidence matters.",
            "anchor_clip": {
                "start": 10,
                "end": 20,
            },
            "extra_field": "ignored",
        }
    ]


def make_speaker_perspective():
    return {
        "expected_qualifications": ["the literature may be mixed"],
        "qualifications_preserved": ["the literature may be mixed"],
        "narrative_blocks": [
            {
                "assertions": [
                    {
                        "text": "The speaker argues evidence should be weighed carefully.",
                        "hedge_drift_detected": False,
                    }
                ],
                "verbatim_anchors": ["claim_001"],
            }
        ],
    }


def make_adjudications():
    return [
        {
            "claim_id": "claim_001",
            "speaker_claim_summary": "The speaker says evidence should be balanced.",
            "balance_score": "balanced",
            "verdict": "well_supported_with_qualifications",
        }
    ]


def make_evidence_records():
    return [
        {
            "evidence_record_id": "evidence_001",
            "claim_id": "claim_001",
            "tier": 1,
            "stance": "supports",
            "title": "Example Evidence Record",
            "identifier": "10.1234/example",
            "url": "https://example.com/paper",
        }
    ]


def test_normalize_claims_keeps_required_fields_and_numeric_clip_values():
    normalized = normalize_claims(make_claims())

    assert normalized == [
        {
            "claim_id": "claim_001",
            "verbatim_quote": "Balanced evidence matters.",
            "anchor_clip": {
                "start": 10.0,
                "end": 20.0,
            },
        }
    ]


def test_normalize_evidence_records_keeps_traceable_identifiers():
    normalized = normalize_evidence_records(make_evidence_records())

    assert normalized[0]["evidence_record_id"] == "evidence_001"
    assert normalized[0]["identifier"] == "10.1234/example"
    assert normalized[0]["url"] == "https://example.com/paper"


def test_build_references_from_evidence_records_uses_evidence_ids():
    references = build_references_from_evidence_records(make_evidence_records())

    assert references == [
        {
            "evidence_record_id": "evidence_001",
            "identifier": "10.1234/example",
            "url": "https://example.com/paper",
        }
    ]


def test_build_rendered_clips_from_claims_uses_anchor_clip_ranges():
    rendered_clips = build_rendered_clips_from_claims(normalize_claims(make_claims()))

    assert rendered_clips == [
        {
            "claim_id": "claim_001",
            "start": 10.0,
            "end": 20.0,
        }
    ]


def test_build_paper_artifact_creates_valid_evaluator_contract():
    artifact = build_paper_artifact(
        claims=make_claims(),
        speaker_perspective=make_speaker_perspective(),
        adjudications=make_adjudications(),
        evidence_records=make_evidence_records(),
    )

    validation = validate_paper_artifact(artifact)

    assert validation.valid is True
    assert artifact["claims"][0]["claim_id"] == "claim_001"
    assert artifact["references"][0]["evidence_record_id"] == "evidence_001"
    assert artifact["rendered_clips"][0]["claim_id"] == "claim_001"


def test_build_paper_artifact_allows_explicit_references_and_rendered_clips():
    explicit_references = [
        {
            "evidence_record_id": "evidence_001",
            "identifier": "10.1234/example",
            "url": "https://example.com/paper",
        }
    ]

    explicit_rendered_clips = [
        {
            "claim_id": "claim_001",
            "start": 10.0,
            "end": 20.0,
        }
    ]

    artifact = build_paper_artifact(
        claims=make_claims(),
        speaker_perspective=make_speaker_perspective(),
        adjudications=make_adjudications(),
        evidence_records=make_evidence_records(),
        references=explicit_references,
        rendered_clips=explicit_rendered_clips,
    )

    assert artifact["references"] == explicit_references
    assert artifact["rendered_clips"] == explicit_rendered_clips


def test_write_and_load_paper_artifact_round_trip(tmp_path):
    artifact = build_paper_artifact(
        claims=make_claims(),
        speaker_perspective=make_speaker_perspective(),
        adjudications=make_adjudications(),
        evidence_records=make_evidence_records(),
    )

    output_path = tmp_path / "paper_artifact.json"

    written_path = write_paper_artifact(artifact, output_path)
    loaded = load_paper_artifact(output_path)

    assert written_path == output_path
    assert loaded["claims"][0]["claim_id"] == "claim_001"
    assert loaded["evidence_records"][0]["evidence_record_id"] == "evidence_001"


def test_load_paper_artifact_raises_for_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_paper_artifact(tmp_path / "missing.json")