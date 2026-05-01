from src.argument.chunker import chunk_transcript_segments
from src.core.config import load_config
from src.data.json_store import load_json, save_json
from src.ops.run_tracker import (
    create_run_log,
    record_metric,
    record_error,
    finish_run_log,
    save_run_log
)

def run_argument_structure(config_path: str = "configs/argument_config.json") -> dict:
    """
    Run the argument structure stage.

    For now, this stage only performs transcript chunking.
    Later, this same runner will also produce:
    - argument_map.json
    - anchor_moments.json

    Args:
        config_path: Path to the argument structure config file.

    Returns:
        The completed run log.
    """
    config = load_config(config_path)

    input_path = config["input_path"]
    chunks_path = config["output_paths"]["chunks"]
    chunking_config = config["chunking"]

    run_log = create_run_log(
        config_path=config_path,
        input_path=input_path,
        output_path=chunks_path,
        pipeline_name="argument_structure",
    )

    try:
        transcript_data = load_json(input_path)

        segments = _extract_segments(transcript_data)

        chunks = chunk_transcript_segments(
            segments=segments,
            max_chunk_chars=chunking_config["max_chunk_chars"],
            min_chunk_chars=chunking_config["min_chunk_chars"],
            overlap_segments=chunking_config.get("overlap_segments", 0),
        )

        chunk_dicts = [chunk.to_dict() for chunk in chunks]

        save_json(chunk_dicts, chunks_path)
        record_metric(run_log, "chunk_count", len(chunk_dicts))
        finish_run_log(run_log, "success")

    except Exception as e:
        record_error(run_log, str(e))
        finish_run_log(run_log, "failed")
        raise

    finally:
        save_run_log(run_log)

    return run_log


def _extract_segments(transcript_data: dict) -> list[dict]:
    """Normalize stored transcript JSON into chunker-facing segment dicts."""
    if not isinstance(transcript_data, dict):
        raise TypeError("transcript_data must be a dictionary")

    segments = transcript_data.get("segments")
    if not isinstance(segments, list):
        raise ValueError("transcript_data must contain a segments list")

    normalized: list[dict] = []
    for index, seg in enumerate(segments):
        if not isinstance(seg, dict):
            raise TypeError("each segment must be a dictionary")

        source_text = seg.get("source_text")
        if source_text is None:
            source_text = seg.get("text", "")
        if not isinstance(source_text, str):
            raise TypeError("segment source_text/text must be a string")

        segment_id = seg.get("segment_id") or seg.get("id") or f"seg_{index + 1:04d}"

        normalized.append(
            {
                "segment_id": segment_id,
                "source_text": source_text,
                "clean_text": seg.get(
                    "cleaned_text", seg.get("clean_text", source_text)
                ),
                "char_start": int(seg["char_start"]),
                "char_end": int(seg["char_end"]),
                "start_seconds": float(
                    seg.get("start_seconds", seg["start_time"])
                ),
                "end_seconds": float(seg.get("end_seconds", seg["end_time"])),
            }
        )

    return normalized