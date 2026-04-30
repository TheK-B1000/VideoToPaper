from dataclasses import dataclass

@dataclass
class TranscriptChunk:
    """
    Represents a transcript chunk with source-text offsets and timing preserved.

    Chunk overlap (see configs ``chunking.overlap_chars``) duplicates text only
    for retrieval context. ``char_start`` / ``char_end`` must always slice the
    same underlying ``source_text`` as the transcript string—never synthetic
    ranges invented for the overlapped copy when ``overlap_reuses_source_offsets``
    is true in config.
    """
    chunk_id: str
    source_text: str
    clean_text: str
    char_start: int
    char_end: int
    start_seconds: float
    end_seconds: float
    segment_ids: list[str]
    chunk_type: str = "transcript_window"

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "source_text": self.source_text,
            "clean_text": self.clean_text,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "segment_ids": self.segment_ids,
            "chunk_type": self.chunk_type,
        }