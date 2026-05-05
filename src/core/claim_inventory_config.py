from __future__ import annotations

from typing import Any

CLAIM_INVENTORY_KEYS = frozenset(
    {
        "enabled",
        "drop_non_verbatim_claims",
        "require_embed_url",
        "allowed_claim_types",
        "output_path",
    }
)

CANONICAL_CLAIM_TYPES = frozenset(
    {
        "empirical_technical",
        "empirical_historical",
        "empirical_scientific",
        "interpretive",
        "normative",
        "anecdotal",
        "predictive",
    }
)


def parse_claim_inventory_settings(config: dict[str, Any]) -> dict[str, Any] | None:
    """
    Read and validate the optional Week 3 ``claim_inventory`` subsection.

    Returns ``None`` when the section is absent (older configs). Raises
    ``ValueError`` when the section exists but is malformed.
    """
    if "claim_inventory" not in config:
        return None

    section = config["claim_inventory"]
    if not isinstance(section, dict):
        raise ValueError("claim_inventory must be an object")

    missing = CLAIM_INVENTORY_KEYS - section.keys()
    if missing:
        raise ValueError(f"claim_inventory missing keys: {sorted(missing)}")

    extra = set(section.keys()) - CLAIM_INVENTORY_KEYS
    if extra:
        raise ValueError(f"claim_inventory unknown keys: {sorted(extra)}")

    if not isinstance(section["enabled"], bool):
        raise ValueError("claim_inventory.enabled must be a boolean")

    if not isinstance(section["drop_non_verbatim_claims"], bool):
        raise ValueError("claim_inventory.drop_non_verbatim_claims must be a boolean")

    if not isinstance(section["require_embed_url"], bool):
        raise ValueError("claim_inventory.require_embed_url must be a boolean")

    output_path = section["output_path"]
    if not isinstance(output_path, str) or not output_path.strip():
        raise ValueError("claim_inventory.output_path must be a non-empty string")

    allowed = section["allowed_claim_types"]
    if not isinstance(allowed, list):
        raise ValueError("claim_inventory.allowed_claim_types must be a list")

    # Empty list is valid: pipeline treats it as "allow all canonical claim types".

    for claim_type in allowed:
        if not isinstance(claim_type, str):
            raise ValueError("claim_inventory.allowed_claim_types entries must be strings")
        if claim_type not in CANONICAL_CLAIM_TYPES:
            raise ValueError(f"unknown claim type in allowed_claim_types: {claim_type!r}")

    return dict(section)
