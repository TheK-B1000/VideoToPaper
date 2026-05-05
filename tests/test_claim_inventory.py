import pytest

from src.core.claim_inventory import (
    AnchorClip,
    build_claim_embed_url,
    build_claim_inventory,
    claim_inventory_to_dicts,
    create_claim_record,
    load_claim_inventory_payload,
    map_claim_type_to_strategy,
    save_claim_inventory,
    summarize_claim_inventory,
    validate_candidate_claim,
    verify_verbatim_quote,
)


def test_verbatim_quote_matches_source_offsets():
    source_text = "Multi-agent RL faces non-stationarity in competitive environments."
    quote = "non-stationarity"

    start = source_text.index(quote)
    end = start + len(quote)

    assert verify_verbatim_quote(source_text, quote, start, end) is True


def test_verbatim_quote_fails_when_offsets_do_not_match():
    source_text = "Single-agent algorithms often assume stationarity."
    quote = "algorithms often"

    wrong_start = 0
    wrong_end = len(quote)

    assert verify_verbatim_quote(source_text, quote, wrong_start, wrong_end) is False

def test_empirical_claim_routes_to_literature_review():
    assert map_claim_type_to_strategy("empirical_technical") == "literature_review"


def test_normative_claim_does_not_route_to_literature_review():
    assert map_claim_type_to_strategy("normative") == "no_external_verification"


def test_interpretive_claim_does_not_route_to_literature_review():
    assert map_claim_type_to_strategy("interpretive") == "source_context_review"


def test_embed_url_uses_clip_timing():
    clip = AnchorClip(start=252.4, end=263.0)

    embed_url = build_claim_embed_url(
        "https://www.youtube-nocookie.com/embed/ABC123",
        clip,
    )

    assert embed_url == (
        "https://www.youtube-nocookie.com/embed/ABC123"
        "?start=252&end=263&rel=0"
    )


def test_create_claim_record_returns_record_for_valid_verbatim_claim():
    source_text = "Standard single-agent algorithms assume stationarity."
    quote = "single-agent algorithms assume stationarity"

    start = source_text.index(quote)
    end = start + len(quote)

    record = create_claim_record(
        claim_id="claim_0001",
        source_text=source_text,
        verbatim_quote=quote,
        anchor_chunk="chunk_001",
        char_offset_start=start,
        char_offset_end=end,
        anchor_clip=AnchorClip(start=10.2, end=15.9),
        claim_type="empirical_technical",
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
    )

    assert record is not None
    assert record.claim_id == "claim_0001"
    assert record.verbatim_quote == quote
    assert record.verification_strategy == "literature_review"
    assert "start=10" in record.embed_url
    assert "end=15" in record.embed_url


def test_create_claim_record_keeps_non_verbatim_when_require_verbatim_disabled():
    source_text = "The speaker says one thing."
    span_text = "one thing"
    start = source_text.index(span_text)
    end = start + len(span_text)
    mismatched_quote = "x" * len(span_text)

    record = create_claim_record(
        claim_id="claim_0002",
        source_text=source_text,
        verbatim_quote=mismatched_quote,
        anchor_chunk="chunk_001",
        char_offset_start=start,
        char_offset_end=end,
        anchor_clip=AnchorClip(start=5.0, end=9.0),
        claim_type="empirical_technical",
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
        require_verbatim=False,
    )

    assert record is not None
    assert record.verbatim_quote == mismatched_quote


def test_create_claim_record_drops_non_verbatim_claim():
    source_text = "The speaker says one thing."
    quote = "The speaker says something else."

    record = create_claim_record(
        claim_id="claim_0002",
        source_text=source_text,
        verbatim_quote=quote,
        anchor_chunk="chunk_001",
        char_offset_start=0,
        char_offset_end=len(quote),
        anchor_clip=AnchorClip(start=5.0, end=9.0),
        claim_type="empirical_technical",
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
    )

    assert record is None


def test_invalid_clip_range_raises_error():
    with pytest.raises(ValueError):
        build_claim_embed_url(
            "https://www.youtube-nocookie.com/embed/ABC123",
            AnchorClip(start=20.0, end=10.0),
        )

def test_build_claim_inventory_keeps_only_verbatim_claims():
    source_text = "Standard single-agent algorithms assume stationarity."
    valid_quote = "single-agent algorithms assume stationarity"
    invalid_quote = "single-agent algorithms solve everything"

    valid_start = source_text.index(valid_quote)
    valid_end = valid_start + len(valid_quote)

    candidate_claims = [
        {
            "claim_id": "claim_0001",
            "verbatim_quote": valid_quote,
            "anchor_chunk": "chunk_001",
            "char_offset_start": valid_start,
            "char_offset_end": valid_end,
            "anchor_clip": {"start": 10.0, "end": 15.0},
            "claim_type": "empirical_technical",
        },
        {
            "claim_id": "claim_0002",
            "verbatim_quote": invalid_quote,
            "anchor_chunk": "chunk_001",
            "char_offset_start": 0,
            "char_offset_end": len(invalid_quote),
            "anchor_clip": {"start": 20.0, "end": 25.0},
            "claim_type": "empirical_technical",
        },
    ]

    inventory = build_claim_inventory(
        candidate_claims=candidate_claims,
        source_text_by_chunk_id={"chunk_001": source_text},
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
    )

    assert len(inventory) == 1
    assert inventory[0].claim_id == "claim_0001"


def test_build_claim_inventory_skips_claims_with_missing_source_chunk():
    candidate_claims = [
        {
            "claim_id": "claim_0001",
            "verbatim_quote": "missing chunk quote",
            "anchor_chunk": "chunk_missing",
            "char_offset_start": 0,
            "char_offset_end": 19,
            "anchor_clip": {"start": 10.0, "end": 15.0},
            "claim_type": "empirical_technical",
        }
    ]

    inventory = build_claim_inventory(
        candidate_claims=candidate_claims,
        source_text_by_chunk_id={},
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
    )

    assert inventory == []

def test_validate_candidate_claim_accepts_valid_candidate():
    candidate = {
        "claim_id": "claim_0001",
        "verbatim_quote": "single-agent algorithms assume stationarity",
        "anchor_chunk": "chunk_001",
        "char_offset_start": 9,
        "char_offset_end": 52,
        "anchor_clip": {"start": 10.0, "end": 15.0},
        "claim_type": "empirical_technical",
    }

    assert validate_candidate_claim(candidate) is True


def test_validate_candidate_claim_rejects_missing_required_field():
    candidate = {
        "claim_id": "claim_0001",
        "verbatim_quote": "single-agent algorithms assume stationarity",
        "anchor_chunk": "chunk_001",
        "char_offset_start": 9,
        "char_offset_end": 52,
        "anchor_clip": {"start": 10.0, "end": 15.0},
    }

    assert validate_candidate_claim(candidate) is False


def test_validate_candidate_claim_rejects_invalid_claim_type():
    candidate = {
        "claim_id": "claim_0001",
        "verbatim_quote": "single-agent algorithms assume stationarity",
        "anchor_chunk": "chunk_001",
        "char_offset_start": 9,
        "char_offset_end": 52,
        "anchor_clip": {"start": 10.0, "end": 15.0},
        "claim_type": "made_up_type",
    }

    assert validate_candidate_claim(candidate) is False


def test_build_claim_inventory_skips_malformed_candidate():
    source_text = "Standard single-agent algorithms assume stationarity."
    valid_quote = "single-agent algorithms assume stationarity"

    start = source_text.index(valid_quote)
    end = start + len(valid_quote)

    candidate_claims = [
        {
            "claim_id": "claim_0001",
            "verbatim_quote": valid_quote,
            "anchor_chunk": "chunk_001",
            "char_offset_start": start,
            "char_offset_end": end,
            "anchor_clip": {"start": 10.0, "end": 15.0},
            "claim_type": "empirical_technical",
        },
        {
            "claim_id": "claim_0002",
            "verbatim_quote": "this candidate is malformed",
            "anchor_chunk": "chunk_001",
        },
    ]

    inventory = build_claim_inventory(
        candidate_claims=candidate_claims,
        source_text_by_chunk_id={"chunk_001": source_text},
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
    )

    assert len(inventory) == 1
    assert inventory[0].claim_id == "claim_0001"


def test_claim_inventory_to_dicts_converts_records():
    record = create_claim_record(
        claim_id="claim_0001",
        source_text="AI systems need evaluation.",
        verbatim_quote="AI systems need evaluation",
        anchor_chunk="chunk_001",
        char_offset_start=0,
        char_offset_end=26,
        anchor_clip=AnchorClip(start=1.0, end=3.0),
        claim_type="empirical_technical",
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
    )

    dicts = claim_inventory_to_dicts([record])

    assert dicts[0]["claim_id"] == "claim_0001"
    assert dicts[0]["anchor_clip"]["end"] == 3.0


def test_summarize_claim_inventory_counts_types_and_strategies():
    source_text = "Alpha beta gamma delta epsilon."
    quote_a = "Alpha beta"
    quote_b = "gamma delta"

    start_a = source_text.index(quote_a)
    end_a = start_a + len(quote_a)
    start_b = source_text.index(quote_b)
    end_b = start_b + len(quote_b)

    empirical = create_claim_record(
        claim_id="claim_emp",
        source_text=source_text,
        verbatim_quote=quote_a,
        anchor_chunk="chunk_001",
        char_offset_start=start_a,
        char_offset_end=end_a,
        anchor_clip=AnchorClip(start=1.0, end=2.0),
        claim_type="empirical_technical",
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
    )
    normative = create_claim_record(
        claim_id="claim_norm",
        source_text=source_text,
        verbatim_quote=quote_b,
        anchor_chunk="chunk_001",
        char_offset_start=start_b,
        char_offset_end=end_b,
        anchor_clip=AnchorClip(start=3.0, end=4.0),
        claim_type="normative",
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
    )

    assert empirical is not None and normative is not None

    summary = summarize_claim_inventory([empirical, normative])

    assert summary == {
        "claim_count": 2,
        "claim_type_counts": {"empirical_technical": 1, "normative": 1},
        "verification_strategy_counts": {
            "literature_review": 1,
            "no_external_verification": 1,
        },
        "has_empirical_claims": True,
    }


def test_save_claim_inventory_payload_includes_summary(tmp_path):
    source_text = "Standard single-agent algorithms assume stationarity."
    quote = "single-agent algorithms assume stationarity"

    start = source_text.index(quote)
    end = start + len(quote)

    inventory = build_claim_inventory(
        candidate_claims=[
            {
                "claim_id": "claim_0001",
                "verbatim_quote": quote,
                "anchor_chunk": "chunk_001",
                "char_offset_start": start,
                "char_offset_end": end,
                "anchor_clip": {"start": 10.0, "end": 15.0},
                "claim_type": "empirical_technical",
            }
        ],
        source_text_by_chunk_id={"chunk_001": source_text},
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
    )

    output_path = tmp_path / "claim_inventory.json"

    save_claim_inventory(
        inventory=inventory,
        output_path=output_path,
    )

    loaded_payload = load_claim_inventory_payload(output_path)

    assert loaded_payload["summary"] == summarize_claim_inventory(inventory)


def test_save_and_load_claim_inventory_payload(tmp_path):
    source_text = "Standard single-agent algorithms assume stationarity."
    quote = "single-agent algorithms assume stationarity"

    start = source_text.index(quote)
    end = start + len(quote)

    inventory = build_claim_inventory(
        candidate_claims=[
            {
                "claim_id": "claim_0001",
                "verbatim_quote": quote,
                "anchor_chunk": "chunk_001",
                "char_offset_start": start,
                "char_offset_end": end,
                "anchor_clip": {"start": 10.0, "end": 15.0},
                "claim_type": "empirical_technical",
            }
        ],
        source_text_by_chunk_id={"chunk_001": source_text},
        embed_base_url="https://www.youtube-nocookie.com/embed/ABC123",
    )

    output_path = tmp_path / "claim_inventory.json"

    saved_path = save_claim_inventory(
        inventory=inventory,
        output_path=output_path,
    )

    loaded_payload = load_claim_inventory_payload(saved_path)

    assert loaded_payload["claim_count"] == 1
    assert loaded_payload["claims"][0]["claim_id"] == "claim_0001"
    assert loaded_payload["claims"][0]["verification_strategy"] == "literature_review"
    assert loaded_payload["claims"][0]["anchor_clip"]["start"] == 10.0