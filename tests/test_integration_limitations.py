from src.integration.integration_limitations import build_integration_limitations


def test_build_integration_limitations_always_includes_core_caveats():
    lim = build_integration_limitations()
    assert len(lim) >= 3
    joined = " ".join(lim).lower()
    assert "bibliographic" in joined or "metadata" in joined
    assert "transcript" in joined or "caption" in joined


def test_build_integration_limitations_detects_dry_run_sources():
    lim = build_integration_limitations(
        evidence_records=[
            {
                "claim_id": "c1",
                "title": "Dry-run supporting source",
                "source": "DryRun",
                "url": "https://example.com",
                "tier": 1,
                "stance": "supports",
            }
        ],
    )
    assert any("dry-run" in x.lower() or "placeholder" in x.lower() for x in lim)


def test_build_integration_limitations_preserves_existing_entries():
    lim = build_integration_limitations(
        existing=["Custom limitation from upstream."],
        evidence_records=[],
    )
    assert lim[0] == "Custom limitation from upstream."
    assert len(lim) >= 2
