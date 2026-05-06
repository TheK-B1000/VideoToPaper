import json
from pathlib import Path

import pytest

from src.pipelines.run_evidence_retrieval_cli import (
    _extract_claims,
    _load_json,
    run_evidence_retrieval_cli,
)


def test_load_json_rejects_missing_file(tmp_path):
    missing_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError, match="JSON file not found"):
        _load_json(missing_path)


def test_extract_claims_supports_claims_key():
    payload = {
        "claims": [
            {
                "claim_id": "claim_001",
                "verbatim_quote": "Multi-agent environments are non-stationary.",
                "claim_type": "empirical_technical",
                "verification_strategy": "literature_review",
            }
        ]
    }

    claims = _extract_claims(payload)

    assert len(claims) == 1
    assert claims[0].claim_id == "claim_001"
    assert claims[0].claim_text == "Multi-agent environments are non-stationary."
    assert claims[0].verification_strategy == "literature_review"


def test_extract_claims_supports_claim_inventory_key():
    payload = {
        "claim_inventory": [
            {
                "id": "claim_002",
                "claim_text": "This is an interpretive claim.",
                "claim_type": "interpretive",
                "verification_strategy": "argument_analysis",
            }
        ]
    }

    claims = _extract_claims(payload)

    assert len(claims) == 1
    assert claims[0].claim_id == "claim_002"
    assert claims[0].claim_text == "This is an interpretive claim."
    assert claims[0].verification_strategy == "argument_analysis"


def test_extract_claims_returns_empty_list_when_no_claims_exist():
    claims = _extract_claims({})

    assert claims == []


def test_run_evidence_retrieval_cli_writes_output_for_empty_inventory(tmp_path):
    input_path = tmp_path / "claim_inventory.json"
    output_path = tmp_path / "evidence_retrieval.json"

    input_path.write_text(
        json.dumps({"claims": []}),
        encoding="utf-8",
    )

    result_path = run_evidence_retrieval_cli(
        claim_inventory_path=str(input_path),
        output_path=str(output_path),
    )

    assert result_path == output_path
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["source_claim_inventory"] == str(input_path)
    assert payload["retrieval_count"] == 0
    assert payload["retrieval_exhausted_query_count_total"] == 0
    assert payload["retrieval_results"] == []