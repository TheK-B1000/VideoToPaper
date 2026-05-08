import json

from src.evaluation.assembler_fixture_writer import (
    build_assembler_fixture_payloads,
    write_assembler_fixtures,
)


def test_build_assembler_fixture_payloads_contains_expected_sections():
    payloads = build_assembler_fixture_payloads()

    assert "claims" in payloads
    assert "speaker_perspective" in payloads
    assert "adjudications" in payloads
    assert "evidence_records" in payloads

    assert payloads["claims"]["claims"][0]["claim_id"] == "claim_001"
    assert (
        payloads["speaker_perspective"]["narrative_blocks"][0]["verbatim_anchors"]
        == ["claim_001"]
    )
    assert payloads["adjudications"]["adjudications"][0]["balance_score"] == "balanced"
    assert (
        payloads["evidence_records"]["evidence_records"][0]["evidence_record_id"]
        == "evidence_001"
    )


def test_write_assembler_fixtures_creates_expected_files(tmp_path):
    paths = write_assembler_fixtures(tmp_path)

    assert paths["claims"].exists()
    assert paths["speaker_perspective"].exists()
    assert paths["adjudications"].exists()
    assert paths["evidence_records"].exists()

    claims = json.loads(paths["claims"].read_text(encoding="utf-8"))
    speaker = json.loads(paths["speaker_perspective"].read_text(encoding="utf-8"))
    adjudications = json.loads(paths["adjudications"].read_text(encoding="utf-8"))
    evidence = json.loads(paths["evidence_records"].read_text(encoding="utf-8"))

    assert claims["claims"][0]["claim_id"] == "claim_001"
    assert speaker["narrative_blocks"][0]["verbatim_anchors"] == ["claim_001"]
    assert (
        adjudications["adjudications"][0]["verdict"]
        == "well_supported_with_qualifications"
    )
    assert evidence["evidence_records"][0]["identifier"] == "10.1234/example-study"
