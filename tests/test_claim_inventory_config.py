import json
from pathlib import Path

import pytest

from src.core.claim_inventory_config import (
    CANONICAL_CLAIM_TYPES,
    CLAIM_INVENTORY_KEYS,
    parse_claim_inventory_settings,
)
from src.core.config import load_config

REPO_ROOT = Path(__file__).resolve().parents[1]
ARGUMENT_CONFIG_PATH = REPO_ROOT / "configs" / "argument_config.json"


def test_argument_config_loads_with_claim_inventory_section():
    config = load_config(ARGUMENT_CONFIG_PATH)
    assert "claim_inventory" in config


def test_repo_argument_config_claim_inventory_matches_expected_contract():
    config = load_config(ARGUMENT_CONFIG_PATH)
    section = parse_claim_inventory_settings(config)

    assert section is not None
    assert set(section.keys()) == CLAIM_INVENTORY_KEYS

    assert section["enabled"] is True
    assert section["drop_non_verbatim_claims"] is True
    assert section["require_embed_url"] is True
    assert section["output_path"] == "data/processed/claim_inventory.json"

    allowed = section["allowed_claim_types"]
    assert set(allowed) == CANONICAL_CLAIM_TYPES


def test_parse_claim_inventory_settings_returns_none_when_absent():
    assert parse_claim_inventory_settings({"stage": "x"}) is None


def test_parse_claim_inventory_settings_accepts_empty_allowed_claim_types(tmp_path):
    section = {
        "enabled": True,
        "drop_non_verbatim_claims": True,
        "require_embed_url": True,
        "allowed_claim_types": [],
        "output_path": "data/processed/claim_inventory.json",
    }
    config_path = tmp_path / "cfg.json"
    config_path.write_text(
        json.dumps({**_minimal_config_shell(), "claim_inventory": section}),
        encoding="utf-8",
    )
    config = load_config(config_path)
    parsed = parse_claim_inventory_settings(config)
    assert parsed is not None
    assert parsed["allowed_claim_types"] == []


def test_parse_claim_inventory_settings_rejects_unknown_claim_type(tmp_path):
    base = {
        "enabled": True,
        "drop_non_verbatim_claims": True,
        "require_embed_url": True,
        "allowed_claim_types": ["empirical_technical", "not_a_real_type"],
        "output_path": "data/processed/claim_inventory.json",
    }
    config_path = tmp_path / "cfg.json"
    config_path.write_text(
        json.dumps({**_minimal_config_shell(), "claim_inventory": base}),
        encoding="utf-8",
    )
    config = load_config(config_path)

    with pytest.raises(ValueError, match="unknown claim type"):
        parse_claim_inventory_settings(config)


def test_parse_claim_inventory_settings_rejects_extra_keys(tmp_path):
    section = {
        "enabled": True,
        "drop_non_verbatim_claims": True,
        "require_embed_url": True,
        "allowed_claim_types": list(CANONICAL_CLAIM_TYPES),
        "output_path": "data/processed/claim_inventory.json",
        "unexpected": True,
    }
    config_path = tmp_path / "cfg.json"
    config_path.write_text(
        json.dumps({**_minimal_config_shell(), "claim_inventory": section}),
        encoding="utf-8",
    )
    config = load_config(config_path)

    with pytest.raises(ValueError, match="unknown keys"):
        parse_claim_inventory_settings(config)


def _minimal_config_shell() -> dict:
    return {
        "stage": "argument_structure",
        "input_path": "data/x.json",
        "output_paths": {},
        "chunking": {},
        "anchors": {},
        "llm": {},
        "safety": {},
    }
