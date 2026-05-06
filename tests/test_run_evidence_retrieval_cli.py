import json

import pytest

from src.pipelines.run_evidence_retrieval import ClaimForRetrieval
from src.pipelines.run_evidence_retrieval_cli import (
    _build_dry_run_result,
    _build_retrieval_summary,
    _enforce_retrieval_quality_gate,
    _extract_claims,
    _load_evidence_retrieval_config,
    _load_json,
    _validate_source,
    _write_retrieval_run_log,
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


def test_load_evidence_retrieval_config_reads_section(tmp_path):
    config_path = tmp_path / "argument_config.json"

    config_path.write_text(
        json.dumps(
            {
                "evidence_retrieval": {
                    "claim_inventory_path": "data/processed/claims.json",
                    "output_path": "data/processed/evidence.json",
                    "source": "openalex",
                    "per_query_limit": 2,
                    "dry_run": True,
                }
            }
        ),
        encoding="utf-8",
    )

    config = _load_evidence_retrieval_config(str(config_path))

    assert config["source"] == "openalex"
    assert config["per_query_limit"] == 2
    assert config["dry_run"] is True


def test_load_evidence_retrieval_config_rejects_non_object_section(tmp_path):
    config_path = tmp_path / "argument_config.json"

    config_path.write_text(
        json.dumps({"evidence_retrieval": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must be an object"):
        _load_evidence_retrieval_config(str(config_path))


def test_validate_source_accepts_known_sources():
    assert _validate_source("all") == "all"
    assert _validate_source("openalex") == "openalex"
    assert _validate_source("semantic_scholar") == "semantic_scholar"


def test_validate_source_rejects_unknown_source():
    with pytest.raises(ValueError, match="source must be one of"):
        _validate_source("google-scholar")


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
    assert payload["dry_run"] is False
    assert payload["source"] == "all"
    assert payload["per_query_limit"] == 3
    assert payload["retrieval_exhausted_query_count_total"] == 0
    assert payload["retrieval_summary"]["total_claims"] == 0
    assert payload["retrieval_summary"]["publishable_for_week5"] is False
    assert payload["fail_on_unbalanced"] is False
    assert payload["retrieval_results"] == []


def test_quality_gate_passes_when_disabled_even_if_unbalanced():
    summary = {
        "publishable_for_week5": False,
        "claims_needing_review": ["claim_001"],
    }

    _enforce_retrieval_quality_gate(
        retrieval_summary=summary,
        fail_on_unbalanced=False,
    )


def test_quality_gate_passes_when_publishable():
    summary = {
        "publishable_for_week5": True,
        "claims_needing_review": [],
    }

    _enforce_retrieval_quality_gate(
        retrieval_summary=summary,
        fail_on_unbalanced=True,
    )


def test_quality_gate_raises_when_enabled_and_unbalanced():
    summary = {
        "publishable_for_week5": False,
        "claims_needing_review": ["claim_001", "claim_002"],
    }

    with pytest.raises(RuntimeError, match="quality gate failed"):
        _enforce_retrieval_quality_gate(
            retrieval_summary=summary,
            fail_on_unbalanced=True,
        )


def test_build_retrieval_summary_counts_balanced_and_skewed_results():
    retrieval_results = [
        {
            "claim_id": "claim_001",
            "balance_score": "balanced",
            "evidence_records": [
                {"source": "OpenAlex"},
                {"source": "Semantic Scholar"},
            ],
        },
        {
            "claim_id": "claim_002",
            "balance_score": "supportive_skewed",
            "evidence_records": [
                {"source": "OpenAlex"},
            ],
        },
        {
            "claim_id": "claim_003",
            "balance_score": "insufficient",
            "evidence_records": [],
        },
    ]

    summary = _build_retrieval_summary(retrieval_results)

    assert summary["total_claims"] == 3
    assert summary["total_evidence_records"] == 3
    assert summary["balance_counts"]["balanced"] == 1
    assert summary["balance_counts"]["supportive_skewed"] == 1
    assert summary["balance_counts"]["contrary_skewed"] == 0
    assert summary["balance_counts"]["insufficient"] == 1
    assert summary["balance_rate"] == 1 / 3
    assert summary["claims_needing_review"] == ["claim_002", "claim_003"]
    assert summary["sources_seen"] == ["OpenAlex", "Semantic Scholar"]
    assert summary["publishable_for_week5"] is False


def test_build_retrieval_summary_marks_all_balanced_claims_publishable():
    retrieval_results = [
        {
            "claim_id": "claim_001",
            "balance_score": "balanced",
            "evidence_records": [
                {"source": "OpenAlex"},
                {"source": "Semantic Scholar"},
            ],
        },
        {
            "claim_id": "claim_002",
            "balance_score": "balanced",
            "evidence_records": [
                {"source": "OpenAlex"},
            ],
        },
    ]

    summary = _build_retrieval_summary(retrieval_results)

    assert summary["total_claims"] == 2
    assert summary["balance_counts"]["balanced"] == 2
    assert summary["claims_needing_review"] == []
    assert summary["balance_rate"] == 1.0
    assert summary["publishable_for_week5"] is True


def test_build_retrieval_summary_empty_run_is_not_publishable():
    summary = _build_retrieval_summary([])

    assert summary["total_claims"] == 0
    assert summary["total_evidence_records"] == 0
    assert summary["balance_rate"] == 0.0
    assert summary["claims_needing_review"] == []
    assert summary["sources_seen"] == []
    assert summary["publishable_for_week5"] is False


def test_write_retrieval_run_log_creates_audit_file(tmp_path):
    claim_inventory_path = tmp_path / "claim_inventory.json"
    output_path = tmp_path / "evidence_retrieval.json"
    log_dir = tmp_path / "logs"

    claim_inventory_path.write_text("{}", encoding="utf-8")
    output_path.write_text("{}", encoding="utf-8")

    retrieval_summary = {
        "total_claims": 1,
        "total_evidence_records": 2,
        "balance_counts": {
            "balanced": 1,
            "supportive_skewed": 0,
            "contrary_skewed": 0,
            "insufficient": 0,
        },
        "balance_rate": 1.0,
        "claims_needing_review": [],
        "sources_seen": ["DryRun"],
        "publishable_for_week5": True,
    }

    log_path = _write_retrieval_run_log(
        source_claim_inventory=claim_inventory_path,
        output_path=output_path,
        dry_run=True,
        source="all",
        per_query_limit=3,
        fail_on_unbalanced=True,
        retrieval_count=1,
        retrieval_summary=retrieval_summary,
        log_dir=log_dir,
    )

    assert log_path.exists()
    assert log_path.parent == log_dir
    assert log_path.name.startswith("evidence_retrieval_")
    assert log_path.suffix == ".json"

    payload = json.loads(log_path.read_text(encoding="utf-8"))

    assert payload["stage"] == "evidence_retrieval"
    assert payload["source_claim_inventory"] == str(claim_inventory_path)
    assert payload["output_path"] == str(output_path)
    assert payload["dry_run"] is True
    assert payload["source"] == "all"
    assert payload["per_query_limit"] == 3
    assert payload["fail_on_unbalanced"] is True
    assert payload["retrieval_count"] == 1
    assert payload["retrieval_summary"]["publishable_for_week5"] is True
    assert "run_id" in payload
    assert "started_at" in payload
    assert "finished_at" in payload


def test_dry_run_result_returns_balanced_fake_evidence():
    claim = ClaimForRetrieval(
        claim_id="claim_001",
        claim_text="Multi-agent environments are non-stationary.",
        claim_type="empirical_technical",
        verification_strategy="literature_review",
    )

    result = _build_dry_run_result(claim)

    assert result.claim_id == "claim_001"
    assert result.balance_score == "balanced"
    assert len(result.queries_executed) == 4
    assert len(result.evidence_records) == 2

    stances = {record.stance for record in result.evidence_records}

    assert stances == {"supports", "qualifies"}


def test_dry_run_result_returns_insufficient_for_non_literature_claim():
    claim = ClaimForRetrieval(
        claim_id="claim_002",
        claim_text="This is a moral interpretation.",
        claim_type="normative",
        verification_strategy="argument_analysis",
    )

    result = _build_dry_run_result(claim)

    assert result.claim_id == "claim_002"
    assert result.balance_score == "insufficient"
    assert result.queries_executed == []
    assert result.evidence_records == []


def test_run_evidence_retrieval_cli_dry_run_writes_fake_evidence(tmp_path):
    input_path = tmp_path / "claim_inventory.json"
    output_path = tmp_path / "evidence_retrieval.json"

    input_path.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "verbatim_quote": "Multi-agent environments are non-stationary.",
                        "claim_type": "empirical_technical",
                        "verification_strategy": "literature_review",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result_path = run_evidence_retrieval_cli(
        claim_inventory_path=str(input_path),
        output_path=str(output_path),
        dry_run=True,
    )

    assert result_path == output_path

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["dry_run"] is True
    assert payload["fail_on_unbalanced"] is False
    assert payload["source"] == "all"
    assert payload["per_query_limit"] == 3
    assert payload["retrieval_count"] == 1
    assert payload["retrieval_summary"]["total_claims"] == 1
    assert payload["retrieval_summary"]["balance_counts"]["balanced"] == 1
    assert payload["retrieval_summary"]["publishable_for_week5"] is True
    assert payload["retrieval_summary"]["sources_seen"] == ["DryRun"]

    result = payload["retrieval_results"][0]

    assert result["claim_id"] == "claim_001"
    assert result["balance_score"] == "balanced"
    assert len(result["evidence_records"]) == 2


def test_run_evidence_retrieval_cli_writes_quality_gate_setting(tmp_path):
    input_path = tmp_path / "claim_inventory.json"
    output_path = tmp_path / "evidence_retrieval.json"

    input_path.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "verbatim_quote": "Multi-agent environments are non-stationary.",
                        "claim_type": "empirical_technical",
                        "verification_strategy": "literature_review",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    run_evidence_retrieval_cli(
        claim_inventory_path=str(input_path),
        output_path=str(output_path),
        dry_run=True,
        fail_on_unbalanced=True,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["fail_on_unbalanced"] is True
    assert payload["retrieval_summary"]["publishable_for_week5"] is True


def test_run_evidence_retrieval_cli_uses_config_values(tmp_path):
    claim_inventory_path = tmp_path / "claims.json"
    output_path = tmp_path / "evidence.json"
    config_path = tmp_path / "argument_config.json"

    claim_inventory_path.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "verbatim_quote": "Multi-agent environments are non-stationary.",
                        "claim_type": "empirical_technical",
                        "verification_strategy": "literature_review",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    config_path.write_text(
        json.dumps(
            {
                "evidence_retrieval": {
                    "claim_inventory_path": str(claim_inventory_path),
                    "output_path": str(output_path),
                    "source": "semantic_scholar",
                    "per_query_limit": 2,
                    "dry_run": True,
                }
            }
        ),
        encoding="utf-8",
    )

    result_path = run_evidence_retrieval_cli(config_path=str(config_path))

    assert result_path == output_path

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["dry_run"] is True
    assert payload["fail_on_unbalanced"] is False
    assert payload["source"] == "semantic_scholar"
    assert payload["per_query_limit"] == 2
    assert payload["retrieval_count"] == 1


def test_run_evidence_retrieval_cli_explicit_args_override_config(tmp_path):
    config_claims_path = tmp_path / "config_claims.json"
    explicit_claims_path = tmp_path / "explicit_claims.json"
    config_output_path = tmp_path / "config_output.json"
    explicit_output_path = tmp_path / "explicit_output.json"
    config_path = tmp_path / "argument_config.json"

    config_claims_path.write_text(
        json.dumps({"claims": []}),
        encoding="utf-8",
    )

    explicit_claims_path.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_id": "claim_override",
                        "verbatim_quote": "Explicit arguments should win.",
                        "claim_type": "empirical_technical",
                        "verification_strategy": "literature_review",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    config_path.write_text(
        json.dumps(
            {
                "evidence_retrieval": {
                    "claim_inventory_path": str(config_claims_path),
                    "output_path": str(config_output_path),
                    "source": "openalex",
                    "per_query_limit": 1,
                    "dry_run": True,
                }
            }
        ),
        encoding="utf-8",
    )

    result_path = run_evidence_retrieval_cli(
        config_path=str(config_path),
        claim_inventory_path=str(explicit_claims_path),
        output_path=str(explicit_output_path),
        source="all",
        per_query_limit=4,
        dry_run=True,
    )

    assert result_path == explicit_output_path
    assert not config_output_path.exists()

    payload = json.loads(explicit_output_path.read_text(encoding="utf-8"))

    assert payload["source"] == "all"
    assert payload["per_query_limit"] == 4
    assert payload["fail_on_unbalanced"] is False
    assert payload["retrieval_count"] == 1
