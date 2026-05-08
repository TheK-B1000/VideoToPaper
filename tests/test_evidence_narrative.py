import pytest

from src.integration.evidence_narrative import (
    NarrativeGenerationResult,
    build_deterministic_fallback_narrative,
    build_evidence_narrative_prompt,
    generate_evidence_narrative,
)


class FakeNarrativeClient:
    def __init__(self, response: str):
        self.response = response
        self.prompt_seen = None
        self.max_output_tokens_seen = None

    def generate(self, prompt: str, *, max_output_tokens: int) -> str:
        self.prompt_seen = prompt
        self.max_output_tokens_seen = max_output_tokens
        return self.response


class FailingNarrativeClient:
    def generate(self, prompt: str, *, max_output_tokens: int) -> str:
        raise RuntimeError("boom")


def sample_claim():
    return {
        "claim_id": "claim_001",
        "verbatim_quote": "Non-stationarity makes multi-agent learning difficult.",
    }


def sample_adjudication():
    return {
        "claim_id": "claim_001",
        "verdict": "well_supported_with_qualifications",
        "confidence": "high",
        "evidence_summary": {
            "supports": ["Foerster 2018"],
            "qualifies": ["Vinyals 2019"],
            "complicates": [],
            "contradicts": [],
        },
    }


def sample_evidence_records():
    return [
        {
            "claim_id": "claim_001",
            "stance": "supports",
            "citation_label": "Foerster 2018",
            "key_finding": "Opponent learning creates non-stationary dynamics.",
        },
        {
            "claim_id": "claim_001",
            "stance": "qualifies",
            "citation_label": "Vinyals 2019",
            "key_finding": "Large-scale self-play can reduce some practical instability.",
        },
    ]


def test_builds_prompt_with_claim_verdict_and_evidence():
    prompt = build_evidence_narrative_prompt(
        claim=sample_claim(),
        adjudication=sample_adjudication(),
        evidence_records=sample_evidence_records(),
    )

    assert "Claim ID:" in prompt
    assert "claim_001" in prompt
    assert "Non-stationarity makes multi-agent learning difficult." in prompt
    assert "well_supported_with_qualifications" in prompt
    assert "Foerster 2018" in prompt
    assert "Vinyals 2019" in prompt
    assert "Use only the evidence records provided" in prompt
    assert "inquiry tone" in prompt


def test_deterministic_fallback_uses_verdict_confidence_and_sources():
    narrative = build_deterministic_fallback_narrative(
        adjudication=sample_adjudication(),
    )

    assert "well_supported_with_qualifications" in narrative
    assert "high confidence" in narrative
    assert "Foerster 2018" in narrative
    assert "Vinyals 2019" in narrative


def test_generate_narrative_uses_fallback_when_llm_disabled():
    result = generate_evidence_narrative(
        claim=sample_claim(),
        adjudication=sample_adjudication(),
        evidence_records=sample_evidence_records(),
        use_llm=False,
    )

    assert isinstance(result, NarrativeGenerationResult)
    assert result.used_llm is False
    assert result.fallback_reason == "LLM narrative generation disabled."
    assert "Foerster 2018" in result.narrative


def test_generate_narrative_uses_client_when_enabled():
    client = FakeNarrativeClient(
        "The speaker's claim is broadly supported, though the evidence also suggests important qualifications."
    )

    result = generate_evidence_narrative(
        claim=sample_claim(),
        adjudication=sample_adjudication(),
        evidence_records=sample_evidence_records(),
        narrative_client=client,
        use_llm=True,
        max_output_tokens=500,
    )

    assert result.used_llm is True
    assert result.fallback_reason is None
    assert "broadly supported" in result.narrative
    assert client.prompt_seen is not None
    assert "Foerster 2018" in client.prompt_seen
    assert client.max_output_tokens_seen == 500


def test_generate_narrative_falls_back_when_client_missing():
    result = generate_evidence_narrative(
        claim=sample_claim(),
        adjudication=sample_adjudication(),
        evidence_records=sample_evidence_records(),
        narrative_client=None,
        use_llm=True,
    )

    assert result.used_llm is False
    assert result.fallback_reason == "No narrative client was provided."
    assert "Foerster 2018" in result.narrative


def test_generate_narrative_falls_back_when_client_fails():
    result = generate_evidence_narrative(
        claim=sample_claim(),
        adjudication=sample_adjudication(),
        evidence_records=sample_evidence_records(),
        narrative_client=FailingNarrativeClient(),
        use_llm=True,
    )

    assert result.used_llm is False
    assert result.fallback_reason is not None
    assert "Narrative client failed" in result.fallback_reason
    assert "Foerster 2018" in result.narrative


def test_rejects_prompt_without_verbatim_quote():
    bad_claim = {
        "claim_id": "claim_001",
    }

    with pytest.raises(ValueError, match="verbatim_quote"):
        build_evidence_narrative_prompt(
            claim=bad_claim,
            adjudication=sample_adjudication(),
            evidence_records=sample_evidence_records(),
        )
