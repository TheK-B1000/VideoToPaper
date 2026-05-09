import json

from src.argument.run_argument_structure import run_argument_structure


def test_run_argument_structure_creates_outputs(tmp_path):
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
            "char_start": 0,
            "char_end": 54,
            "start_seconds": 0.0,
            "end_seconds": 8.0,
        },
        {
            "segment_id": "seg_0002",
            "source_text": "For example, a chunk can miss the important context. ",
            "clean_text": "For example, a chunk can miss the important context.",
            "char_start": 54,
            "char_end": 107,
            "start_seconds": 8.0,
            "end_seconds": 16.0,
        },
        {
            "segment_id": "seg_0003",
            "source_text": "However, overlap helps preserve meaning across boundaries.",
            "clean_text": "However, overlap helps preserve meaning across boundaries.",
            "char_start": 107,
            "char_end": 162,
            "start_seconds": 16.0,
            "end_seconds": 24.0,
        },
    ]

    transcript_data = {
        "source_text": "".join(seg["source_text"] for seg in segments),
        "segments": segments,
    }

    input_path.write_text(json.dumps(transcript_data), encoding="utf-8")

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
            "max_estimated_cost_usd_per_day": 5.0,
            "max_estimated_cost_usd_per_month": 30.0,
            "max_estimated_cost_usd_per_call": 0.1,
            "allowed_models": ["gpt-4o-mini"],
            "model_pricing": {
                "gpt-4o-mini": {
                    "input_cost_per_1m_tokens": 0.15,
                    "output_cost_per_1m_tokens": 0.60,
                },
            },
            "max_prompt_chars": 500000,
            "max_llm_retries_per_call": 1,
            "budget_persistence_dir": str(tmp_path / "budget"),
            "fail_closed": True,
        },
    }

    config_path.write_text(json.dumps(config_data), encoding="utf-8")

    run_log = run_argument_structure(config_path=str(config_path))

    assert run_log["status"] == "success"
    assert run_log["pipeline_name"] == "argument_structure"

    assert chunks_path.exists()
    assert anchors_path.exists()
    assert argument_map_path.exists()

    chunks_output = json.loads(chunks_path.read_text(encoding="utf-8"))

    assert chunks_output["stage"] == "argument_structure"
    assert chunks_output["input_path"] == str(input_path)
    assert chunks_output["chunk_count"] >= 1
    assert "validation" in chunks_output
    assert "internal" in chunks_output["validation"]
    assert "source_alignment" in chunks_output["validation"]
    chunk_list = chunks_output["chunks"]
    assert isinstance(chunk_list, list)
    assert len(chunk_list) >= 1
    assert "chunk_id" in chunk_list[0]
    assert "source_text" in chunk_list[0]

    internal_val = chunks_output["validation"]["internal"]
    alignment_val = chunks_output["validation"]["source_alignment"]
    assert internal_val["invalid_chunk_count"] == 0
    assert alignment_val["chunk_source_alignment_pass_rate"] == 1.0

    anchors_output = json.loads(anchors_path.read_text(encoding="utf-8"))
    argument_map_output = json.loads(argument_map_path.read_text(encoding="utf-8"))

    assert anchors_output["stage"] == "argument_structure"
    assert "anchors" in anchors_output

    assert argument_map_output["stage"] == "argument_structure"
    assert "argument_map" in argument_map_output
    assert "validation" in argument_map_output

    assert "chunk_count" in run_log["metrics"]
    assert "chunk_source_alignment_pass_rate" in run_log["metrics"]
    assert "anchor_moment_count" in run_log["metrics"]
    assert "argument_map_valid" in run_log["metrics"]