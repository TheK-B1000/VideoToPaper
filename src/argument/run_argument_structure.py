from src.argument.anchor_detector import detect_anchor_moments
from src.argument.anchor_validator import validate_anchors
from src.argument.argument_map_builder import build_argument_map
from src.argument.argument_map_validator import validate_argument_map
from src.argument.chunk_validator import validate_chunks
from src.argument.chunker import chunk_transcript_segments
from src.argument.source_alignment_validator import (
    build_full_source_text_from_segments,
    validate_chunk_source_alignment,
)
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

    Chunking, anchor detection, and heuristic argument mapping produce
    chunks.json (with embedded chunk and source-alignment validation),
    anchor_moments.json, and argument_map.json (including embedded validation).

    Args:
        config_path: Path to the argument structure config file.

    Returns:
        The completed run log.
    """
    config = load_config(config_path)

    input_path = config["input_path"]
    output_paths = config["output_paths"]
    chunks_path = output_paths["chunks"]
    anchor_moments_path = output_paths["anchor_moments"]
    argument_map_path = output_paths["argument_map"]
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

        full_source_text = build_full_source_text_from_segments(segments)

        chunks = chunk_transcript_segments(
            segments=segments,
            max_chunk_chars=chunking_config["max_chunk_chars"],
            min_chunk_chars=chunking_config["min_chunk_chars"],
            overlap_segments=chunking_config.get("overlap_segments", 0),
        )

        chunk_validation_metrics = validate_chunks(chunks)

        source_alignment_metrics = validate_chunk_source_alignment(
            chunks=chunks,
            full_source_text=full_source_text,
        )

        chunk_dicts = [chunk.to_dict() for chunk in chunks]

        chunk_output = {
            "stage": config["stage"],
            "input_path": input_path,
            "chunk_count": len(chunk_dicts),
            "validation": {
                "internal": chunk_validation_metrics,
                "source_alignment": source_alignment_metrics,
            },
            "chunks": chunk_dicts,
        }

        save_json(chunk_output, chunks_path)

        anchors = detect_anchor_moments(
            chunks=chunks,
            allowed_types=config["anchors"]["allowed_types"],
        )

        anchor_validation_metrics = validate_anchors(
            anchors=anchors,
            chunks=chunks,
            allowed_types=config["anchors"]["allowed_types"],
        )

        argument_map = build_argument_map(
            chunks=chunks,
            anchors=anchors,
        )

        argument_map_validation_metrics = validate_argument_map(
            argument_map=argument_map,
            anchors=anchors,
        )

        anchor_output = {
            "stage": config["stage"],
            "input_path": output_paths["chunks"],
            "anchor_count": len(anchors),
            "anchors": anchors,
        }

        save_json(anchor_output, anchor_moments_path)

        argument_map_output = {
            "stage": config["stage"],
            "input_path": output_paths["anchor_moments"],
            "validation": argument_map_validation_metrics,
            "argument_map": argument_map,
        }

        save_json(argument_map_output, argument_map_path)

        record_metric(run_log, "input_segment_count", len(segments))
        record_metric(run_log, "chunk_count", len(chunk_dicts))

        if chunk_dicts:
            avg_chunk_chars = sum(
                len(chunk["source_text"])
                for chunk in chunk_dicts
            ) / len(chunk_dicts)

            record_metric(run_log, "avg_chunk_chars", avg_chunk_chars)
            record_metric(
                run_log,
                "min_chunk_chars",
                min(len(chunk["source_text"]) for chunk in chunk_dicts)
            )
            record_metric(
                run_log,
                "max_chunk_chars",
                max(len(chunk["source_text"]) for chunk in chunk_dicts)
            )

        for metric_name, metric_value in source_alignment_metrics.items():
            if metric_name != "misaligned_chunks":
                record_metric(run_log, metric_name, metric_value)

        if source_alignment_metrics["misaligned_chunks"]:
            record_metric(
                run_log,
                "misaligned_chunks",
                source_alignment_metrics["misaligned_chunks"],
            )

        record_metric(run_log, "anchor_moment_count", len(anchors))

        anchor_counts_by_type: dict[str, int] = {}
        for anchor in anchors:
            anchor_type = anchor["type"]
            anchor_counts_by_type[anchor_type] = (
                anchor_counts_by_type.get(anchor_type, 0) + 1
            )

        for anchor_type, count in anchor_counts_by_type.items():
            record_metric(run_log, f"anchor_{anchor_type}_count", count)

        record_metric(
            run_log,
            "anchor_valid_count",
            anchor_validation_metrics["valid_anchor_count"],
        )
        record_metric(
            run_log,
            "anchor_invalid_count",
            anchor_validation_metrics["invalid_anchor_count"],
        )
        record_metric(
            run_log,
            "anchor_type_validation_pass_rate",
            anchor_validation_metrics["anchor_type_validation_pass_rate"],
        )
        record_metric(
            run_log,
            "anchor_offset_validation_pass_rate",
            anchor_validation_metrics["anchor_offset_validation_pass_rate"],
        )
        record_metric(
            run_log,
            "anchor_timestamp_validation_pass_rate",
            anchor_validation_metrics["anchor_timestamp_validation_pass_rate"],
        )
        record_metric(
            run_log,
            "anchor_chunk_reference_pass_rate",
            anchor_validation_metrics["anchor_chunk_reference_pass_rate"],
        )
        record_metric(
            run_log,
            "anchor_source_text_validation_pass_rate",
            anchor_validation_metrics["anchor_source_text_validation_pass_rate"],
        )

        record_metric(run_log, "argument_map_type", argument_map["map_type"])
        record_metric(
            run_log,
            "thesis_candidate_count",
            len(argument_map["thesis_candidates"]),
        )
        record_metric(
            run_log,
            "supporting_point_count",
            len(argument_map["supporting_points"]),
        )
        record_metric(
            run_log,
            "qualification_count",
            len(argument_map["qualifications"]),
        )
        record_metric(run_log, "example_count", len(argument_map["examples"]))
        record_metric(
            run_log,
            "summary_claim_count",
            len(argument_map["summary_claims"]),
        )

        for metric_name, metric_value in argument_map_validation_metrics.items():
            if metric_name != "invalid_argument_items":
                record_metric(run_log, metric_name, metric_value)

        if argument_map_validation_metrics["invalid_argument_items"]:
            record_metric(
                run_log,
                "invalid_argument_items",
                argument_map_validation_metrics["invalid_argument_items"],
            )

        finish_run_log(run_log, status="success")

    except Exception as error:
        record_error(run_log, str(error))
        finish_run_log(run_log, status="failed")
        save_run_log(run_log)
        raise

    save_run_log(run_log)

    return run_log


def _extract_segments(transcript_data: dict) -> list[dict]:
    """
    Extract transcript segments from processed transcript data.

    Supports a few likely shapes so the runner is tolerant while the project evolves.
    Normalizes fields for :func:`chunk_transcript_segments`.
    """
    if not isinstance(transcript_data, dict):
        raise TypeError("transcript_data must be a dictionary")

    if "segments" in transcript_data:
        raw_list = transcript_data["segments"]
    elif "transcript" in transcript_data and isinstance(
        transcript_data["transcript"], list
    ):
        raw_list = transcript_data["transcript"]
    elif "processed_segments" in transcript_data:
        raw_list = transcript_data["processed_segments"]
    else:
        raise ValueError(
            "Could not find transcript segments. Expected one of: "
            "'segments', 'transcript', or 'processed_segments'."
        )

    if not isinstance(raw_list, list):
        raise TypeError("transcript segments must be a list")

    normalized: list[dict] = []
    for index, seg in enumerate(raw_list):
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
                    seg["start_seconds"]
                    if "start_seconds" in seg
                    else seg["start_time"]
                ),
                "end_seconds": float(
                    seg["end_seconds"]
                    if "end_seconds" in seg
                    else seg["end_time"]
                ),
            }
        )

    return normalized