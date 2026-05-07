import json
from pathlib import Path

import pytest

from src.pipelines.run_evidence_integration_pipeline import (
    group_evidence_by_claim_id,
    normalize_claim_inventory,
    normalize_evidence_records,
    run_evidence_integration_pipeline,
    should_integrate_claim,
)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class FakeNarrativeClient:
    def __init__(self, response: str):
        self.response = response
        self.calls = 0

    def generate(self, prompt: str, *, max_output_tokens: int) -> str:
        self.calls += 1
        return self.response


def test_normalizes_claim_inventory_from_claims_key():
    document = {
        "claims": [
            {
                "claim_id": "claim_001",
                "verbatim_quote": "Example claim.",
            }
        ]
    }

    claims = normalize_claim_inventory(document)

    assert len(claims) == 1
    assert claims[0]["claim_id"] == "claim_001"


def test_normalizes_evidence_records_from_records_key():
    document = {
        "records": [
            {
                "claim_id": "claim_001",
                "stance": "supports",
                "citation_label": "Example 2024",
            }
        ]
    }

    records = normalize_evidence_records(document)

    assert len(records) == 1
    assert records[0]["claim_id"] == "claim_001"


def test_groups_evidence_by_claim_id():
    records = [
        {
            "claim_id": "claim_001",
            "stance": "supports",
            "citation_label": "Support 2024",
        },
        {
            "claim_id": "claim_001",
            "stance": "qualifies",
            "citation_label": "Qualification 2024",
        },
        {
            "claim_id": "claim_002",
            "stance": "contradicts",
            "citation_label": "Contrary 2024",
        },
    ]

    grouped = group_evidence_by_claim_id(records)

    assert len(grouped["claim_001"]) == 2
    assert len(grouped["claim_002"]) == 1


def test_should_integrate_only_literature_review_claims():
    empirical_claim = {
        "claim_id": "claim_001",
        "claim_type": "empirical_technical",
        "verification_strategy": "literature_review",
    }

    normative_claim = {
        "claim_id": "claim_002",
        "claim_type": "normative",
        "verification_strategy": "ethical_analysis",
    }

    assert should_integrate_claim(empirical_claim) is True
    assert should_integrate_claim(normative_claim) is False


def test_pipeline_writes_adjudications_and_skips_non_empirical_claims(tmp_path):
    claim_inventory_path = tmp_path / "claim_inventory.json"
    evidence_records_path = tmp_path / "evidence_records.json"
    output_path = tmp_path / "adjudications.json"

    write_json(
        claim_inventory_path,
        {
            "claims": [
                {
                    "claim_id": "claim_001",
                    "verbatim_quote": "Non-stationarity makes multi-agent learning difficult.",
                    "claim_type": "empirical_technical",
                    "verification_strategy": "literature_review",
                },
                {
                    "claim_id": "claim_002",
                    "verbatim_quote": "Researchers should be more careful.",
                    "claim_type": "normative",
                    "verification_strategy": "ethical_analysis",
                },
            ]
        },
    )

    write_json(
        evidence_records_path,
        {
            "evidence_records": [
                {
                    "claim_id": "claim_001",
                    "stance": "supports",
                    "citation_label": "Foerster 2018",
                    "title": "Learning with Opponent-Learning Awareness",
                    "source": "Example Journal",
                    "tier": 1,
                    "identifier": "doi:support",
                    "url": "https://example.com/support",
                    "key_finding": "Opponent learning can create non-stationary training dynamics.",
                },
                {
                    "claim_id": "claim_001",
                    "stance": "qualifies",
                    "citation_label": "Vinyals 2019",
                    "title": "Grandmaster Level in StarCraft II",
                    "source": "Nature",
                    "tier": 1,
                    "identifier": "doi:qualify",
                    "url": "https://example.com/qualify",
                    "key_finding": "Scale can reduce some practical learning instability.",
                },
            ]
        },
    )

    result = run_evidence_integration_pipeline(
        claim_inventory_path=claim_inventory_path,
        evidence_records_path=evidence_records_path,
        output_path=output_path,
        run_log_dir=tmp_path / "logs" / "runs",
    )

    assert output_path.exists()
    assert result["schema_version"] == "week7.v1"

    assert result["metrics"]["claims_loaded"] == 2
    assert result["metrics"]["evidence_records_loaded"] == 2
    assert result["metrics"]["adjudications_written"] == 1
    assert result["metrics"]["claims_skipped"] == 1

    adjudication = result["adjudications"][0]

    assert adjudication["claim_id"] == "claim_001"
    assert adjudication["verdict"] == "well_supported_with_qualifications"
    assert adjudication["confidence"] == "high"
    assert adjudication["evidence_summary"]["supports"] == ["Foerster 2018"]
    assert adjudication["evidence_summary"]["qualifies"] == ["Vinyals 2019"]

    skipped = result["skipped_claims"][0]
    assert skipped["claim_id"] == "claim_002"


def test_pipeline_marks_empirical_claim_with_no_evidence_as_insufficient(tmp_path):
    claim_inventory_path = tmp_path / "claim_inventory.json"
    evidence_records_path = tmp_path / "evidence_records.json"
    output_path = tmp_path / "adjudications.json"

    write_json(
        claim_inventory_path,
        [
            {
                "claim_id": "claim_001",
                "verbatim_quote": "This claim has no retrieved evidence.",
                "claim_type": "empirical",
                "verification_strategy": "literature_review",
            }
        ],
    )

    write_json(evidence_records_path, [])

    result = run_evidence_integration_pipeline(
        claim_inventory_path=claim_inventory_path,
        evidence_records_path=evidence_records_path,
        output_path=output_path,
        run_log_dir=tmp_path / "logs" / "runs",
    )

    adjudication = result["adjudications"][0]

    assert adjudication["claim_id"] == "claim_001"
    assert adjudication["verdict"] == "insufficient_evidence"
    assert adjudication["confidence"] == "low"
    assert adjudication["guard_reason"] is not None
    assert result["metrics"]["guarded_adjudications"] == 1


def test_pipeline_rejects_evidence_record_without_claim_id():
    records = [
        {
            "stance": "supports",
            "citation_label": "Broken Evidence 2024",
        }
    ]

    with pytest.raises(ValueError, match="claim_id"):
        group_evidence_by_claim_id(records)


def test_pipeline_writes_mlops_run_log(tmp_path):
    claim_inventory_path = tmp_path / "claim_inventory.json"
    evidence_records_path = tmp_path / "evidence_records.json"
    output_path = tmp_path / "adjudications.json"
    run_log_dir = tmp_path / "logs" / "runs"

    write_json(
        claim_inventory_path,
        {
            "claims": [
                {
                    "claim_id": "claim_001",
                    "verbatim_quote": "Non-stationarity makes multi-agent learning difficult.",
                    "claim_type": "empirical_technical",
                    "verification_strategy": "literature_review",
                }
            ]
        },
    )

    write_json(
        evidence_records_path,
        {
            "evidence_records": [
                {
                    "claim_id": "claim_001",
                    "stance": "supports",
                    "citation_label": "Foerster 2018",
                    "title": "Learning with Opponent-Learning Awareness",
                    "tier": 1,
                    "identifier": "doi:support",
                },
                {
                    "claim_id": "claim_001",
                    "stance": "qualifies",
                    "citation_label": "Vinyals 2019",
                    "title": "Grandmaster Level in StarCraft II",
                    "tier": 1,
                    "identifier": "doi:qualify",
                },
            ]
        },
    )

    result = run_evidence_integration_pipeline(
        claim_inventory_path=claim_inventory_path,
        evidence_records_path=evidence_records_path,
        output_path=output_path,
        run_log_dir=run_log_dir,
    )

    run_log_path = Path(result["run_log_path"])

    assert run_log_path.exists()
    assert run_log_path.parent == run_log_dir

    run_log = json.loads(run_log_path.read_text(encoding="utf-8"))

    assert run_log["pipeline_name"] == "evidence_integration"
    assert run_log["stage"] == "week7"
    assert run_log["status"] == "completed"
    assert run_log["run_id"] == result["run_id"]

    assert run_log["input_paths"]["claim_inventory"] == str(claim_inventory_path)
    assert run_log["input_paths"]["evidence_records"] == str(evidence_records_path)
    assert run_log["output_paths"]["adjudications"] == str(output_path)

    assert run_log["settings"]["allow_skewed_adjudication"] is False
    assert run_log["settings"]["use_llm_narratives"] is False
    assert run_log["metrics"]["adjudications_written"] == 1
    assert run_log["metrics"]["guarded_adjudications"] == 0
    assert run_log["metrics"]["llm_narratives_used"] == 0
    assert run_log["metrics"]["fallback_narratives_used"] == 1


def test_pipeline_writes_failed_run_log_when_input_is_missing(tmp_path):
    claim_inventory_path = tmp_path / "missing_claim_inventory.json"
    evidence_records_path = tmp_path / "evidence_records.json"
    output_path = tmp_path / "adjudications.json"
    run_log_dir = tmp_path / "logs" / "runs"

    write_json(evidence_records_path, [])

    with pytest.raises(FileNotFoundError):
        run_evidence_integration_pipeline(
            claim_inventory_path=claim_inventory_path,
            evidence_records_path=evidence_records_path,
            output_path=output_path,
            run_log_dir=run_log_dir,
        )

    run_logs = list(run_log_dir.glob("evidence_integration_*.json"))

    assert len(run_logs) == 1

    run_log = json.loads(run_logs[0].read_text(encoding="utf-8"))

    assert run_log["pipeline_name"] == "evidence_integration"
    assert run_log["stage"] == "week7"
    assert run_log["status"] == "failed"
    assert "error" in run_log
    assert "JSON input file not found" in run_log["error"]


def test_pipeline_adds_fallback_narrative_generation_metadata(tmp_path):
    claim_inventory_path = tmp_path / "claim_inventory.json"
    evidence_records_path = tmp_path / "evidence_records.json"
    output_path = tmp_path / "adjudications.json"
    run_log_dir = tmp_path / "logs" / "runs"

    write_json(
        claim_inventory_path,
        {
            "claims": [
                {
                    "claim_id": "claim_001",
                    "verbatim_quote": "Non-stationarity makes multi-agent learning difficult.",
                    "claim_type": "empirical_technical",
                    "verification_strategy": "literature_review",
                }
            ]
        },
    )

    write_json(
        evidence_records_path,
        {
            "evidence_records": [
                {
                    "claim_id": "claim_001",
                    "stance": "supports",
                    "citation_label": "Foerster 2018",
                    "title": "Learning with Opponent-Learning Awareness",
                    "tier": 1,
                    "identifier": "doi:support",
                    "key_finding": "Opponent learning can create non-stationary training dynamics.",
                },
                {
                    "claim_id": "claim_001",
                    "stance": "qualifies",
                    "citation_label": "Vinyals 2019",
                    "title": "Grandmaster Level in StarCraft II",
                    "tier": 1,
                    "identifier": "doi:qualify",
                    "key_finding": "Self-play and scale can reduce some instability.",
                },
            ]
        },
    )

    result = run_evidence_integration_pipeline(
        claim_inventory_path=claim_inventory_path,
        evidence_records_path=evidence_records_path,
        output_path=output_path,
        run_log_dir=run_log_dir,
        use_llm_narratives=False,
    )

    adjudication = result["adjudications"][0]

    assert adjudication["narrative_generation"]["used_llm"] is False
    assert adjudication["narrative_generation"]["fallback_reason"] == (
        "LLM narrative generation disabled."
    )

    assert result["metrics"]["llm_narratives_used"] == 0
    assert result["metrics"]["fallback_narratives_used"] == 1
    assert "Foerster 2018" in adjudication["narrative"]


def test_pipeline_can_use_injected_narrative_client(tmp_path):
    claim_inventory_path = tmp_path / "claim_inventory.json"
    evidence_records_path = tmp_path / "evidence_records.json"
    output_path = tmp_path / "adjudications.json"
    run_log_dir = tmp_path / "logs" / "runs"

    write_json(
        claim_inventory_path,
        {
            "claims": [
                {
                    "claim_id": "claim_001",
                    "verbatim_quote": "Non-stationarity makes multi-agent learning difficult.",
                    "claim_type": "empirical_technical",
                    "verification_strategy": "literature_review",
                }
            ]
        },
    )

    write_json(
        evidence_records_path,
        {
            "evidence_records": [
                {
                    "claim_id": "claim_001",
                    "stance": "supports",
                    "citation_label": "Foerster 2018",
                    "title": "Learning with Opponent-Learning Awareness",
                    "tier": 1,
                    "identifier": "doi:support",
                    "key_finding": "Opponent learning can create non-stationary training dynamics.",
                },
                {
                    "claim_id": "claim_001",
                    "stance": "qualifies",
                    "citation_label": "Vinyals 2019",
                    "title": "Grandmaster Level in StarCraft II",
                    "tier": 1,
                    "identifier": "doi:qualify",
                    "key_finding": "Self-play and scale can reduce some instability.",
                },
            ]
        },
    )

    client = FakeNarrativeClient(
        "The evidence broadly supports the claim, while also showing important qualifications."
    )

    result = run_evidence_integration_pipeline(
        claim_inventory_path=claim_inventory_path,
        evidence_records_path=evidence_records_path,
        output_path=output_path,
        run_log_dir=run_log_dir,
        use_llm_narratives=True,
        narrative_client=client,
    )

    adjudication = result["adjudications"][0]

    assert client.calls == 1
    assert adjudication["narrative_generation"]["used_llm"] is True
    assert adjudication["narrative_generation"]["fallback_reason"] is None
    assert "broadly supports" in adjudication["narrative"]

    assert result["metrics"]["llm_narratives_used"] == 1
    assert result["metrics"]["fallback_narratives_used"] == 0
