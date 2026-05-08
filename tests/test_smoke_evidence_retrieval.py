import json

from scripts import smoke_evidence_retrieval as smoke


def test_write_smoke_inputs_creates_claims_and_config(tmp_path, monkeypatch):
    smoke_dir = tmp_path / "smoke"
    claims_path = smoke_dir / "claim_inventory_smoke.json"
    output_path = smoke_dir / "evidence_retrieval_smoke.json"
    config_path = smoke_dir / "evidence_retrieval_smoke_config.json"

    monkeypatch.setattr(smoke, "SMOKE_DIR", smoke_dir)
    monkeypatch.setattr(smoke, "CLAIMS_PATH", claims_path)
    monkeypatch.setattr(smoke, "OUTPUT_PATH", output_path)
    monkeypatch.setattr(smoke, "CONFIG_PATH", config_path)

    smoke.write_smoke_inputs()

    assert claims_path.exists()
    assert config_path.exists()

    claims_payload = json.loads(claims_path.read_text(encoding="utf-8"))
    config_payload = json.loads(config_path.read_text(encoding="utf-8"))

    assert claims_payload["claims"][0]["claim_id"] == "claim_smoke_001"
    assert claims_payload["claims"][0]["verification_strategy"] == "literature_review"

    retrieval_config = config_payload["evidence_retrieval"]

    assert retrieval_config["claim_inventory_path"] == str(claims_path)
    assert retrieval_config["output_path"] == str(output_path)
    assert retrieval_config["source"] == "all"
    assert retrieval_config["per_query_limit"] == 1
    assert retrieval_config["dry_run"] is False
