import json
from pathlib import Path

import main


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_main_runs_evidence_integration_stage(tmp_path):
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

    result = main.main(
        [
            "--stage",
            "evidence_integration",
            "--claim-inventory-path",
            str(claim_inventory_path),
            "--evidence-records-path",
            str(evidence_records_path),
            "--output-path",
            str(output_path),
            "--run-log-dir",
            str(run_log_dir),
        ]
    )

    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "week7.v1"
    assert payload["metrics"]["adjudications_written"] == 1
    assert payload["validation"]["is_valid"] is True
    assert payload["cherry_picking_guard"]["publishable_for_week8"] is True

    assert result is not None
    assert result["metrics"]["adjudications_written"] == 1
    assert Path(result["run_log_path"]).exists()
