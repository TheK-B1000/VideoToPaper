from src.integration.adjudication_validator import validate_adjudications_payload


def valid_adjudication():
    return {
        "claim_id": "claim_001",
        "speaker_claim_summary": 'The speaker claims: "Example claim."',
        "evidence_summary": {
            "supports": ["Foerster 2018"],
            "complicates": [],
            "contradicts": [],
            "qualifies": ["Vinyals 2019"],
        },
        "verdict": "well_supported_with_qualifications",
        "confidence": "high",
        "narrative": "The evidence broadly supports the claim, with qualifications.",
        "interactive_payload": {
            "supporting_sources": [
                {
                    "title": "Support Paper",
                    "citation_label": "Foerster 2018",
                    "stance": "supports",
                }
            ],
            "contrary_sources": [],
            "qualifying_sources": [
                {
                    "title": "Qualification Paper",
                    "citation_label": "Vinyals 2019",
                    "stance": "qualifies",
                }
            ],
            "complicating_sources": [],
        },
        "narrative_generation": {
            "used_llm": False,
            "fallback_reason": "LLM narrative generation disabled.",
        },
        "guard_reason": None,
    }


def test_valid_adjudications_payload_passes():
    payload = {
        "schema_version": "week7.v1",
        "adjudications": [valid_adjudication()],
    }

    report = validate_adjudications_payload(payload)

    assert report["is_valid"] is True
    assert report["total_adjudications"] == 1
    assert report["issue_count"] == 0
    assert report["issues"] == []


def test_payload_without_adjudications_list_fails():
    payload = {
        "schema_version": "week7.v1",
        "adjudications": "not a list",
    }

    report = validate_adjudications_payload(payload)

    assert report["is_valid"] is False
    assert report["issue_count"] == 1
    assert report["issues"][0]["field"] == "adjudications"


def test_missing_required_field_fails():
    adjudication = valid_adjudication()
    adjudication.pop("interactive_payload")

    payload = {
        "adjudications": [adjudication],
    }

    report = validate_adjudications_payload(payload)

    assert report["is_valid"] is False
    assert any(
        issue["field"] == "interactive_payload"
        for issue in report["issues"]
    )


def test_invalid_verdict_fails():
    adjudication = valid_adjudication()
    adjudication["verdict"] = "totally_true_because_i_said_so"

    payload = {
        "adjudications": [adjudication],
    }

    report = validate_adjudications_payload(payload)

    assert report["is_valid"] is False
    assert any(issue["field"] == "verdict" for issue in report["issues"])


def test_empty_narrative_fails():
    adjudication = valid_adjudication()
    adjudication["narrative"] = " "

    payload = {
        "adjudications": [adjudication],
    }

    report = validate_adjudications_payload(payload)

    assert report["is_valid"] is False
    assert any(issue["field"] == "narrative" for issue in report["issues"])


def test_missing_evidence_summary_bucket_fails():
    adjudication = valid_adjudication()
    adjudication["evidence_summary"].pop("qualifies")

    payload = {
        "adjudications": [adjudication],
    }

    report = validate_adjudications_payload(payload)

    assert report["is_valid"] is False
    assert any(
        issue["field"] == "evidence_summary.qualifies"
        for issue in report["issues"]
    )


def test_invalid_interactive_payload_bucket_fails():
    adjudication = valid_adjudication()
    adjudication["interactive_payload"]["supporting_sources"] = "not a list"

    payload = {
        "adjudications": [adjudication],
    }

    report = validate_adjudications_payload(payload)

    assert report["is_valid"] is False
    assert any(
        issue["field"] == "interactive_payload.supporting_sources"
        for issue in report["issues"]
    )


def test_invalid_narrative_generation_metadata_fails():
    adjudication = valid_adjudication()
    adjudication["narrative_generation"]["used_llm"] = "nope"

    payload = {
        "adjudications": [adjudication],
    }

    report = validate_adjudications_payload(payload)

    assert report["is_valid"] is False
    assert any(
        issue["field"] == "narrative_generation.used_llm"
        for issue in report["issues"]
    )
