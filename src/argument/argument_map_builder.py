from src.argument.argument_models import TranscriptChunk


def build_argument_map(
    chunks: list[TranscriptChunk],
    anchors: list[dict],
) -> dict:
    """
    Build a heuristic argument map from transcript chunks and anchor moments.

    This is the non-LLM version of argument extraction. It uses detected
    anchor types to organize possible thesis statements, supporting points,
    qualifications, examples, and summary claims.

    Args:
        chunks: Transcript chunks used as source material.
        anchors: Anchor moments detected from those chunks.

    Returns:
        A structured argument map dictionary.
    """
    if not isinstance(chunks, list):
        raise TypeError("chunks must be a list")

    if not isinstance(anchors, list):
        raise TypeError("anchors must be a list")

    chunk_lookup = _build_chunk_lookup(chunks)

    thesis_candidates = []
    supporting_points = []
    qualifications = []
    examples = []
    summary_claims = []

    for anchor in anchors:
        if not isinstance(anchor, dict):
            raise TypeError("each anchor must be a dictionary")

        anchor_type = anchor.get("type")

        if anchor_type in {"verbal_claim"}:
            supporting_points.append(
                _build_argument_item(
                    anchor=anchor,
                    chunk_lookup=chunk_lookup,
                    item_type="supporting_point",
                )
            )

        elif anchor_type == "qualification":
            qualifications.append(
                _build_argument_item(
                    anchor=anchor,
                    chunk_lookup=chunk_lookup,
                    item_type="qualification",
                )
            )

        elif anchor_type == "example":
            examples.append(
                _build_argument_item(
                    anchor=anchor,
                    chunk_lookup=chunk_lookup,
                    item_type="example",
                )
            )

        elif anchor_type == "summary_claim":
            summary_item = _build_argument_item(
                anchor=anchor,
                chunk_lookup=chunk_lookup,
                item_type="summary_claim",
            )
            summary_claims.append(summary_item)
            thesis_candidates.append(summary_item)

        elif anchor_type == "definition":
            supporting_points.append(
                _build_argument_item(
                    anchor=anchor,
                    chunk_lookup=chunk_lookup,
                    item_type="definition",
                )
            )

    return {
        "map_type": "heuristic_argument_map",
        "thesis_candidates": thesis_candidates,
        "supporting_points": supporting_points,
        "qualifications": qualifications,
        "examples": examples,
        "summary_claims": summary_claims,
        "anchor_count": len(anchors),
        "chunk_count": len(chunks),
    }


def _build_chunk_lookup(chunks: list[TranscriptChunk]) -> dict[str, TranscriptChunk]:
    """
    Build a lookup table from chunk_id to TranscriptChunk.
    """
    chunk_lookup = {}

    for chunk in chunks:
        if not isinstance(chunk, TranscriptChunk):
            raise TypeError("each chunk must be a TranscriptChunk")

        chunk_lookup[chunk.chunk_id] = chunk

    return chunk_lookup


def _build_argument_item(
    anchor: dict,
    chunk_lookup: dict[str, TranscriptChunk],
    item_type: str,
) -> dict:
    """
    Build one argument-map item from an anchor.
    """
    chunk_id = anchor.get("chunk_id")
    chunk = chunk_lookup.get(chunk_id)

    context_text = ""

    if chunk is not None:
        context_text = chunk.source_text

    return {
        "item_id": anchor["anchor_id"].replace("anchor", item_type),
        "item_type": item_type,
        "anchor_id": anchor["anchor_id"],
        "chunk_id": anchor["chunk_id"],
        "source_text": anchor["source_text"],
        "context_text": context_text,
        "char_start": anchor["char_start"],
        "char_end": anchor["char_end"],
        "start_seconds": anchor["start_seconds"],
        "end_seconds": anchor["end_seconds"],
        "confidence": "heuristic",
    }