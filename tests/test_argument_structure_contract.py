import json

from src.argument.run_argument_structure import run_argument_structure


def test_argument_structure_outputs_include_required_validation_contract(tmp_path):
    input_path = tmp_path / "processed_transcript.json"
    chunks_path = tmp_path / "chunks.json"
    anchors_path = tmp_path / "anchor_moments.json"
    argument_map_path = tmp_path / "argument_map.json"
    config_path = tmp_path / "argument_config.json"
    runs_dir = tmp_path / "runs"

    segments = [
        {
            "segment_id": "seg_0001",
            "source_text": "The key point is that retrieval can fail silently. ",
            "clean_text": "The key point is that retrieval can fail silently.",
            "start_seconds": 0.0,
            "end_seconds": 8.0,
        },
        {
            "segment_id": "seg_0002",
            "source_text": "For example, a chunk can miss important context. ",
            "clean_text": "For example, a chunk can miss important context.",
            "start_seconds": 8.0,
            "end_seconds": 16.0,
        },
        {
            "segment_id": "seg_0003",
            "source_text": "However, overlap helps preserve meaning.",
            "clean_text": "However, overlap helps preserve meaning.",
            "start_seconds": 16.0,
            "end_seconds": 24.0,
        },
    ]
    cursor = 0
    for seg in segments:
        text = seg["source_text"]
        seg["char_start"] = cursor
        cursor += len(text)
        seg["char_end"] = cursor

    transcript_data = {
        "source_text": "".join(seg["source_text"] for seg in segments),
        "segments": segments,
    }

    config_data = {
        "stage": "argument_structure",
        "input_path": str(input_path),
        "output_paths": {
            "chunks": str(chunks_path),
            "argument_map": str(argument_map_path),
            "anchor_moments": str(anchors_path),
            "run_report_dir": str(runs_dir),
            "run_report_prefix": "argument_structure",
        },
        "chunking": {
            "max_chunk_chars": 1200,
            "min_chunk_chars": 400,
            "overlap_segments": 1,
            "prefer_sentence_boundaries": True,
            "preserve_raw_offsets": True,
        },
        "anchors": {
            "allowed_types": [
                "verbal_claim",
                "definition",
                "example",
                "qualification",
                "summary_claim",
                "visual_reference",
                "diagram_or_figure",
                "demo",
            ],
            "require_timestamp": True,
            "require_char_offsets": True,
        },
        "llm": {
            "enabled": False,
            "model": None,
            "temperature": 0,
            "structured_output_required": True,
        },
        "safety": {
            "drop_invalid_offsets": True,
            "drop_unverifiable_anchors": True,
            "reject_external_knowledge": True,
            "require_supporting_point_anchor": True,
        },
        "budget": {
            "llm_enabled": False,
            "dry_run": True,
            "max_llm_calls_per_run": 5,
            "max_input_tokens_per_call": 4000,
            "max_output_tokens_per_call": 1000,
            "max_total_tokens_per_run": 10000,
            "max_estimated_cost_usd_per_run": 0.25,
            "max_retries_per_call": 1,
            "fail_closed": True,
        },
    }

    input_path.write_text(json.dumps(transcript_data), encoding="utf-8")
    config_path.write_text(json.dumps(config_data), encoding="utf-8")

    run_log = run_argument_structure(config_path=str(config_path))

    chunks_output = json.loads(chunks_path.read_text(encoding="utf-8"))
    anchors_output = json.loads(anchors_path.read_text(encoding="utf-8"))
    argument_map_output = json.loads(argument_map_path.read_text(encoding="utf-8"))

    assert chunks_output["stage"] == "argument_structure"
    assert "validation" in chunks_output
    assert "internal" in chunks_output["validation"]
    assert "source_alignment" in chunks_output["validation"]
    assert chunks_output["validation"]["internal"]["invalid_chunk_count"] == 0
    assert chunks_output["validation"]["source_alignment"]["chunk_source_alignment_pass_rate"] == 1.0

    assert anchors_output["stage"] == "argument_structure"
    assert "validation" in anchors_output
    assert anchors_output["validation"]["invalid_anchor_count"] == 0
    assert "anchors" in anchors_output

    assert argument_map_output["stage"] == "argument_structure"
    assert "validation" in argument_map_output
    assert argument_map_output["validation"]["argument_map_valid"] is True
    assert "argument_map" in argument_map_output

    required_metrics = [
        "input_segment_count",
        "chunk_count",
        "valid_chunk_count",
        "invalid_chunk_count",
        "chunk_source_alignment_pass_rate",
        "anchor_moment_count",
        "valid_anchor_count",
        "invalid_anchor_count",
        "argument_map_valid",
        "argument_item_count",
        "invalid_argument_item_count",
    ]

    for metric_name in required_metrics:
        assert metric_name in run_log["metrics"]