from __future__ import annotations

from pathlib import Path

from src.core.claim_inventory import build_claim_inventory, save_claim_inventory
from src.data.json_store import load_json

DEFAULT_ARGUMENT_MAP_PATH = Path("data/processed/argument_map.json")
DEFAULT_CHUNKS_PATH = Path("data/processed/chunks.json")
DEFAULT_CLAIM_INVENTORY_PATH = Path("data/processed/claim_inventory.json")

ARGUMENT_MAP_ITEM_SECTIONS = (
    "thesis_candidates",
    "supporting_points",
    "qualifications",
    "examples",
    "summary_claims",
)

ITEM_TYPE_TO_CLAIM_TYPE: dict[str, str] = {
    "supporting_point": "empirical_technical",
    "definition": "interpretive",
    "example": "anecdotal",
    "qualification": "interpretive",
    "summary_claim": "empirical_technical",
}


def load_chunks_payload(chunks_path: str | Path) -> list[dict]:
    data = load_json(str(chunks_path))
    chunks = data.get("chunks")
    if not isinstance(chunks, list):
        raise ValueError("chunks payload must contain a list field 'chunks'")
    return chunks


def load_argument_map_document(argument_map_path: str | Path) -> dict:
    data = load_json(str(argument_map_path))
    inner = data.get("argument_map")
    if isinstance(inner, dict):
        return inner
    if data.get("map_type") == "heuristic_argument_map":
        return data
    raise ValueError(
        "argument map payload must include 'argument_map' "
        "or be a bare heuristic_argument_map dict"
    )


def build_source_text_by_chunk_id(chunks: list[dict]) -> dict[str, str]:
    out: dict[str, str] = {}
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        chunk_id = chunk.get("chunk_id")
        source_text = chunk.get("source_text")
        if isinstance(chunk_id, str) and isinstance(source_text, str):
            out[chunk_id] = source_text
    return out


def _chunks_by_id(chunks: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        cid = chunk.get("chunk_id")
        if isinstance(cid, str):
            out[cid] = chunk
    return out


def _iter_argument_items(argument_map: dict) -> list[dict]:
    items: list[dict] = []
    for section in ARGUMENT_MAP_ITEM_SECTIONS:
        section_items = argument_map.get(section)
        if not isinstance(section_items, list):
            continue
        for item in section_items:
            if isinstance(item, dict):
                items.append(item)
    return items


def candidate_claims_from_argument_map(
    argument_map: dict,
    chunks_by_id: dict[str, dict],
) -> list[dict]:
    """
    Turn Week 2 argument-map rows into Week 3 claim-inventory candidate dicts.

    Anchor char offsets are global transcript offsets; claim verification uses
    chunk-local offsets into chunk ``source_text``.
    """
    seen_ids: set[str] = set()
    candidates: list[dict] = []

    for item in _iter_argument_items(argument_map):
        item_id = item.get("item_id")
        if not isinstance(item_id, str) or not item_id.strip():
            continue
        if item_id in seen_ids:
            continue

        chunk_id = item.get("chunk_id")
        if not isinstance(chunk_id, str):
            continue

        chunk = chunks_by_id.get(chunk_id)
        if chunk is None:
            continue

        item_type = item.get("item_type")
        claim_type = ITEM_TYPE_TO_CLAIM_TYPE.get(item_type)
        if claim_type is None:
            continue

        verbatim = item.get("source_text")
        if not isinstance(verbatim, str) or not verbatim.strip():
            continue

        try:
            chunk_char_start = int(chunk["char_start"])
            g_start = int(item["char_start"])
            g_end = int(item["char_end"])
        except (KeyError, TypeError, ValueError):
            continue

        local_start = g_start - chunk_char_start
        local_end = g_end - chunk_char_start

        source_text = chunk.get("source_text")
        if not isinstance(source_text, str):
            continue

        if local_start < 0 or local_end > len(source_text) or local_end <= local_start:
            continue

        if source_text[local_start:local_end] != verbatim:
            continue

        try:
            clip_start = float(item["start_seconds"])
            clip_end = float(item["end_seconds"])
        except (KeyError, TypeError, ValueError):
            continue

        candidates.append(
            {
                "claim_id": item_id,
                "verbatim_quote": verbatim,
                "anchor_chunk": chunk_id,
                "char_offset_start": local_start,
                "char_offset_end": local_end,
                "anchor_clip": {"start": clip_start, "end": clip_end},
                "claim_type": claim_type,
            }
        )
        seen_ids.add(item_id)

    return candidates


def run_claim_inventory_pipeline(
    *,
    embed_base_url: str,
    argument_map_path: str | Path = DEFAULT_ARGUMENT_MAP_PATH,
    chunks_path: str | Path = DEFAULT_CHUNKS_PATH,
    output_path: str | Path = DEFAULT_CLAIM_INVENTORY_PATH,
) -> Path:
    """
    Week 2 → Week 3: load chunks and argument map, build verified claim inventory,
    persist JSON (including summary), return output path.
    """
    chunks = load_chunks_payload(chunks_path)
    argument_map = load_argument_map_document(argument_map_path)
    chunks_by_id = _chunks_by_id(chunks)
    source_text_by_chunk_id = build_source_text_by_chunk_id(chunks)

    candidate_claims = candidate_claims_from_argument_map(
        argument_map=argument_map,
        chunks_by_id=chunks_by_id,
    )

    inventory = build_claim_inventory(
        candidate_claims=candidate_claims,
        source_text_by_chunk_id=source_text_by_chunk_id,
        embed_base_url=embed_base_url,
    )

    return save_claim_inventory(inventory=inventory, output_path=output_path)
