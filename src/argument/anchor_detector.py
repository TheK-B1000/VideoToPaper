from src.argument.argument_models import TranscriptChunk


DEFAULT_ANCHOR_PATTERNS = {
    "verbal_claim": [
        "the key point is",
        "the main point is",
        "the problem is",
        "this means",
        "what this means is",
        "this shows",
        "the reason is",
        "therefore",
        "so the claim is",
        "this matters because",
    ],
    "definition": [
        "is defined as",
        "what i mean by",
        "when i say",
        "refers to",
        "means that",
    ],
    "example": [
        "for example",
        "for instance",
        "imagine",
        "let's say",
        "suppose",
    ],
    "qualification": [
        "however",
        "but",
        "except",
        "with the exception",
        "it depends",
        "not always",
        "in some cases",
    ],
    "summary_claim": [
        "in summary",
        "to summarize",
        "the takeaway is",
        "the conclusion is",
        "overall",
    ],
}


def detect_anchor_moments(
    chunks: list[TranscriptChunk],
    allowed_types: list[str] | None = None,
    patterns: dict[str, list[str]] | None = None,
) -> list[dict]:
    """
    Detect candidate anchor moments from transcript chunks using deterministic
    phrase-based heuristics.

    This does not use an LLM. It only identifies possible citation-worthy
    transcript moments based on anchor phrases.

    Args:
        chunks: Transcript chunks to scan.
        allowed_types: Anchor types allowed by config.
        patterns: Optional custom phrase patterns by anchor type.

    Returns:
        List of anchor candidate dictionaries.
    """
    if not isinstance(chunks, list):
        raise TypeError("chunks must be a list")

    if allowed_types is not None and not isinstance(allowed_types, list):
        raise TypeError("allowed_types must be a list or None")

    active_patterns = patterns or DEFAULT_ANCHOR_PATTERNS

    if not isinstance(active_patterns, dict):
        raise TypeError("patterns must be a dictionary")

    allowed_type_set = set(allowed_types) if allowed_types is not None else set(active_patterns.keys())

    anchors: list[dict] = []

    for chunk in chunks:
        if not isinstance(chunk, TranscriptChunk):
            raise TypeError("each chunk must be a TranscriptChunk")

        chunk_anchors = _detect_anchors_in_chunk(
            chunk=chunk,
            allowed_type_set=allowed_type_set,
            patterns=active_patterns,
            starting_index=len(anchors) + 1,
        )

        anchors.extend(chunk_anchors)

    return anchors


def _detect_anchors_in_chunk(
    chunk: TranscriptChunk,
    allowed_type_set: set[str],
    patterns: dict[str, list[str]],
    starting_index: int,
) -> list[dict]:
    """
    Detect anchors within a single chunk.
    """
    source_text_lower = chunk.source_text.lower()
    anchors: list[dict] = []
    anchor_number = starting_index

    for anchor_type, phrases in patterns.items():
        if anchor_type not in allowed_type_set:
            continue

        if not isinstance(phrases, list):
            raise TypeError("each pattern entry must be a list of strings")

        for phrase in phrases:
            if not isinstance(phrase, str):
                raise TypeError("anchor pattern phrases must be strings")

            phrase_clean = phrase.strip().lower()

            if not phrase_clean:
                continue

            search_start = 0

            while True:
                match_index = source_text_lower.find(phrase_clean, search_start)

                if match_index == -1:
                    break

                anchor = _build_anchor(
                    anchor_number=anchor_number,
                    chunk=chunk,
                    anchor_type=anchor_type,
                    signal=phrase_clean,
                    local_start=match_index,
                    local_end=match_index + len(phrase_clean),
                )

                anchors.append(anchor)
                anchor_number += 1
                search_start = match_index + len(phrase_clean)

    return sorted(anchors, key=lambda anchor: anchor["char_start"])


def _build_anchor(
    anchor_number: int,
    chunk: TranscriptChunk,
    anchor_type: str,
    signal: str,
    local_start: int,
    local_end: int,
) -> dict:
    """
    Build an anchor candidate dictionary from a phrase match inside a chunk.
    """
    if local_start < 0:
        raise ValueError("local_start cannot be negative")

    if local_end < local_start:
        raise ValueError("local_end cannot be less than local_start")

    char_start = chunk.char_start + local_start
    char_end = chunk.char_start + local_end

    source_text = chunk.source_text[local_start:local_end]

    return {
        "anchor_id": f"anchor_{anchor_number:04d}",
        "chunk_id": chunk.chunk_id,
        "type": anchor_type,
        "source_text": source_text,
        "char_start": char_start,
        "char_end": char_end,
        "start_seconds": chunk.start_seconds,
        "end_seconds": chunk.end_seconds,
        "confidence": "heuristic",
        "signal": signal,
    }