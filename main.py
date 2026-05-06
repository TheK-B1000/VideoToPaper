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


def _inject_pipeline_argv(forwarded: list[str], args: argparse.Namespace, *, steelman: bool) -> list[str]:
    """
    Prepend flags parsed by main.py so Week 3–5 nested mains still receive them.

    Week 3 claim_inventory does not accept --claim-inventory-path; Week 4 steelman does.
    """
    prefix: list[str] = []
    if args.config_path is not None:
        prefix.extend(["--config-path", args.config_path])
    if steelman and args.claim_inventory_path is not None:
        prefix.extend(["--claim-inventory-path", args.claim_inventory_path])
    if args.output_path is not None:
        prefix.extend(["--output-path", args.output_path])
    return prefix + list(forwarded)


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
            "evidence_retrieval",
        ),
        default="source_ingestion",
        help=(
            "Pipeline stage (default: Week 1 source ingestion demo). "
            "Week 4: steelman or speaker_perspective. Week 5: evidence_retrieval."
        ),
    )
    parser.add_argument(
        "--config-path",
        default=None,
        help=(
            "Path to argument-structure JSON (Week 2–5). Supplies paths and knobs "
            "including the evidence_retrieval section when running that stage."
        ),
    )
    parser.add_argument(
        "--claim-inventory-path",
        default=None,
        help="Path to the claim inventory JSON file.",
    )
    parser.add_argument(
        "--output-path",
        default=None,
        help="Path where the stage output JSON should be written when applicable.",
    )
    parser.add_argument(
        "--source",
        default=None,
        choices=("all", "openalex", "semantic_scholar"),
        help="Evidence retrieval source to use.",
    )
    parser.add_argument(
        "--per-query-limit",
        type=int,
        default=None,
        help="Maximum number of records to retrieve per query per source.",
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Run the selected stage without live external calls where supported "
            "(Week 5). Omit to use evidence_retrieval.dry_run from config."
        ),
    )
    parser.add_argument(
        "--fail-on-unbalanced",
        action="store_true",
        default=None,
        help="Fail evidence retrieval when balance audit is not publishable.",
    )
    args, forwarded = parser.parse_known_args()

    if args.stage == "claim_inventory":
        from src.pipelines.claim_inventory_pipeline import main as claim_inventory_main

        merged = _inject_pipeline_argv(forwarded, args, steelman=False)
        raise SystemExit(claim_inventory_main(merged))

    if args.stage in ("speaker_perspective", "steelman"):
        from src.pipelines.run_steelman_pipeline import main as steelman_main

        merged = _inject_pipeline_argv(forwarded, args, steelman=True)
        raise SystemExit(steelman_main(merged))

    if args.stage == "evidence_retrieval":
        from src.pipelines.run_evidence_retrieval_cli import run_evidence_retrieval_cli

        if forwarded:
            parser.error(
                "unrecognized arguments for evidence_retrieval: {}".format(
                    " ".join(forwarded)
                )
            )

        run_evidence_retrieval_cli(
            config_path=args.config_path,
            claim_inventory_path=args.claim_inventory_path,
            output_path=args.output_path,
            source=args.source,
            per_query_limit=args.per_query_limit,
            dry_run=args.dry_run,
            fail_on_unbalanced=args.fail_on_unbalanced,
        )
        return

    if forwarded:
        parser.error(
            "unrecognized arguments for source_ingestion: {}".format(" ".join(forwarded))
        )

    if (
        args.config_path is not None
        or args.claim_inventory_path is not None
        or args.output_path is not None
        or args.dry_run is not None
        or args.source is not None
        or args.per_query_limit is not None
        or args.fail_on_unbalanced is not None
    ):
        parser.error(
            "--config-path, --claim-inventory-path, --output-path, --dry-run/--no-dry-run, "
            "--source, --per-query-limit, and --fail-on-unbalanced are only valid with "
            "claim_inventory, speaker_perspective, steelman, or evidence_retrieval."
        )

    _run_source_ingestion()


if __name__ == "__main__":
    main()
