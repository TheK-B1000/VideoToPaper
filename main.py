import argparse

from src.data.json_store import load_json
from src.ops.run_tracker import (
    create_run_log,
    record_metric,
    record_error,
    finish_run_log,
    save_run_log,
)
from src.source.ingestion import ingest_source


def _run_source_ingestion() -> None:
    config_path = "configs/default_config.json"

    transcript_path = "data/raw/raw_transcript.json"
    registry_output_path = "data/outputs/video_registry.json"
    processed_transcript_output_path = "data/processed/processed_transcript.json"

    run_log = create_run_log(
        config_path=config_path,
        input_path=transcript_path,
        output_path=processed_transcript_output_path,
        pipeline_name="source_ingestion",
    )

    try:
        config = load_json(config_path)

        result = ingest_source(
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="What Most People Get Wrong About Reinforcement Learning",
            duration_seconds=2840,
            transcript_path=transcript_path,
            registry_output_path=registry_output_path,
            processed_transcript_output_path=processed_transcript_output_path,
            speaker_name="Dr. Jane Smith",
            speaker_credentials="Professor of Computer Science",
            speaker_stated_motivations="Concerned about misconceptions in popular AI discourse",
            speaker_notes="Mock source used for Week 1 ingestion testing",
            transcript_origin="mock",
            config=config,
        )

        processed_segments = result["transcript_record"]["segments"]

        record_metric(run_log, "processed_segment_count", len(processed_segments))
        record_metric(
            run_log,
            "source_text_char_count",
            len(result["transcript_record"]["source_text"]),
        )
        record_metric(
            run_log,
            "video_duration_seconds",
            result["video_record"]["duration_seconds"],
        )

        finish_run_log(run_log, "success")

        print("Source ingestion complete")
        print(f"Registry output: {registry_output_path}")
        print(f"Processed transcript output: {processed_transcript_output_path}")
        print(f"Segments processed: {len(processed_segments)}")

    except Exception as error:
        record_error(run_log, str(error))
        finish_run_log(run_log, "failed")
        raise

    finally:
        save_run_path = save_run_log(run_log)
        print(f"Run log saved to: {save_run_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="VideoToPaper pipeline entrypoints")
    parser.add_argument(
        "--stage",
        choices=(
            "source_ingestion",
            "claim_inventory",
            "speaker_perspective",
            "steelman",
        ),
        default="source_ingestion",
        help=(
            "Pipeline stage (default: Week 1 source ingestion demo). "
            "Week 4: steelman or speaker_perspective."
        ),
    )
    args, forwarded = parser.parse_known_args()

    if args.stage == "claim_inventory":
        from src.pipelines.claim_inventory_pipeline import main as claim_inventory_main

        raise SystemExit(claim_inventory_main(forwarded))

    if args.stage in ("speaker_perspective", "steelman"):
        from src.pipelines.run_steelman_pipeline import main as steelman_main

        raise SystemExit(steelman_main(forwarded))

    if forwarded:
        parser.error(
            "unrecognized arguments for source_ingestion: {}".format(" ".join(forwarded))
        )

    _run_source_ingestion()


if __name__ == "__main__":
    main()
