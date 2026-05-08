import argparse
from pathlib import Path
from typing import Any

from src.paper.html_audit import audit_html_paper
from src.paper.artifact_manifest import write_paper_artifact_manifest
from src.paper.paper_spec_builder import build_paper_spec
from src.paper.paper_run_report import (
    utc_now_iso,
    write_paper_assembly_run_report,
)
from src.data.json_store import load_json
from src.ops.run_tracker import (
    create_run_log,
    record_metric,
    record_error,
    finish_run_log,
    save_run_log,
)
from src.pipelines.run_evaluation_pipeline import run_evaluation_pipeline
from src.pipelines.run_html_paper_pipeline import run_html_paper_pipeline
from src.pipelines.run_sample_artifact_pipeline import run_sample_artifact_pipeline
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


def main(argv: list[str] | None = None) -> dict[str, Any] | None:
    parser = argparse.ArgumentParser(
        description="VideoToPaper pipeline entrypoints",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--stage",
        choices=(
            "source_ingestion",
            "claim_inventory",
            "speaker_perspective",
            "steelman",
            "evidence_retrieval",
            "evidence_integration",
            "build_paper_spec",
            "html_paper",
            "assemble_paper",
            "audit_html_paper",
            "evaluation",
            "sample_artifact",
        ),
        default="source_ingestion",
        help=(
            "Pipeline stage (default: Week 1 source ingestion demo). "
            "Week 4: steelman or speaker_perspective. Week 5: evidence_retrieval. "
            "Week 7: evidence_integration. "
            "Week 8: build_paper_spec, html_paper, assemble_paper, and audit_html_paper."
            " Evaluation: run artifact evaluation and write an audit report."
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
        "--evidence-records-path",
        default=None,
        help="Path to the Week 5 evidence records JSON file (Week 7 evidence_integration).",
    )
    parser.add_argument(
        "--run-log-dir",
        default=None,
        help="Directory where MLOps run logs are written (Week 7 evidence_integration).",
    )
    parser.add_argument(
        "--allow-skewed-adjudication",
        action="store_true",
        help="Allow adjudication even when retrieval is skewed (Week 7 evidence_integration).",
    )
    parser.add_argument(
        "--use-llm-narratives",
        action="store_true",
        help="Enable LLM-backed evidence narratives when a client is wired in (Week 7).",
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
    parser.add_argument(
        "--source-registry-path",
        default="data/processed/source_registry.json",
        help="Path to the Week 1 source registry JSON file.",
    )
    parser.add_argument(
        "--evidence-integration-path",
        default="data/outputs/evidence_integration.json",
        help="Path to the Week 7 evidence integration JSON file.",
    )
    parser.add_argument(
        "--paper-spec-output-path",
        default="data/outputs/paper_spec.json",
        help="Path where the Week 8 paper spec JSON should be written.",
    )
    parser.add_argument(
        "--paper-title",
        default=None,
        help="Optional custom title for the assembled inquiry paper.",
    )
    parser.add_argument(
        "--paper-abstract",
        default=None,
        help="Optional custom abstract for the assembled inquiry paper.",
    )
    parser.add_argument(
        "--paper-spec-path",
        default="data/outputs/paper_spec.json",
        help="Path to the Week 8 paper spec JSON file.",
    )
    parser.add_argument(
        "--html-output-path",
        default="data/outputs/inquiry_paper.html",
        help="Path where the assembled HTML paper should be written.",
    )
    parser.add_argument(
        "--html-audit-report-path",
        default="data/outputs/html_audit_report.json",
        help="Path where the Week 8 HTML audit report should be written.",
    )
    parser.add_argument(
        "--paper-run-report-path",
        default="data/outputs/paper_assembly_run_report.json",
        help="Path where the Week 8 paper assembly run report should be written.",
    )
    parser.add_argument(
        "--paper-artifact-manifest-path",
        default="data/outputs/paper_artifact_manifest.json",
        help="Path where the Week 8 paper artifact manifest should be written.",
    )
    parser.add_argument(
        "--audit-after-assembly",
        action="store_true",
        help="Run the Week 8 HTML audit immediately after assembling the paper.",
    )
    args, forwarded = parser.parse_known_args(argv)

    if args.stage == "build_paper_spec":
        if forwarded:
            parser.error(
                "unrecognized arguments for build_paper_spec: {}".format(
                    " ".join(forwarded)
                )
            )

        output_path = build_paper_spec(
            source_registry_path=args.source_registry_path,
            claim_inventory_path=args.claim_inventory_path
            or "data/processed/claim_inventory.json",
            evidence_integration_path=args.evidence_integration_path,
            output_path=args.paper_spec_output_path,
            title=args.paper_title,
            abstract=args.paper_abstract,
        )

        print(f"Paper spec written to: {output_path}")
        return

    if args.stage == "html_paper":
        if forwarded:
            parser.error(
                "unrecognized arguments for html_paper: {}".format(
                    " ".join(forwarded)
                )
            )

        output_path = run_html_paper_pipeline(
            paper_spec_path=args.paper_spec_path,
            output_path=args.html_output_path,
        )

        print(f"HTML paper written to: {output_path}")
        return

    if args.stage == "assemble_paper":
        if forwarded:
            parser.error(
                "unrecognized arguments for assemble_paper: {}".format(
                    " ".join(forwarded)
                )
            )

        started_at = utc_now_iso()
        audit_passed = None

        paper_spec_path = build_paper_spec(
            source_registry_path=args.source_registry_path,
            claim_inventory_path=args.claim_inventory_path
            or "data/processed/claim_inventory.json",
            evidence_integration_path=args.evidence_integration_path,
            output_path=args.paper_spec_output_path,
            title=args.paper_title,
            abstract=args.paper_abstract,
        )

        html_output_path = run_html_paper_pipeline(
            paper_spec_path=paper_spec_path,
            output_path=args.html_output_path,
        )

        print(f"Paper spec written to: {paper_spec_path}")
        print(f"HTML paper written to: {html_output_path}")

        if args.audit_after_assembly:
            audit_report = audit_html_paper(
                html_path=html_output_path,
                paper_spec_path=paper_spec_path,
                report_output_path=args.html_audit_report_path,
            )

            audit_passed = audit_report.passed

            print(f"HTML audit report written to: {args.html_audit_report_path}")
            print(f"HTML audit passed: {audit_report.passed}")

            if not audit_report.passed:
                run_report_path = write_paper_assembly_run_report(
                    output_path=args.paper_run_report_path,
                    started_at=started_at,
                    source_registry_path=args.source_registry_path,
                    claim_inventory_path=args.claim_inventory_path
                    or "data/processed/claim_inventory.json",
                    evidence_integration_path=args.evidence_integration_path,
                    paper_spec_path=paper_spec_path,
                    html_output_path=html_output_path,
                    audit_requested=True,
                    audit_report_path=args.html_audit_report_path,
                    audit_passed=False,
                    status="failed_audit",
                )

                manifest_path = write_paper_artifact_manifest(
                    output_path=args.paper_artifact_manifest_path,
                    paper_spec_path=paper_spec_path,
                    html_output_path=html_output_path,
                    audit_report_path=args.html_audit_report_path,
                    run_report_path=run_report_path,
                )

                print(f"Paper assembly run report written to: {run_report_path}")
                print(f"Paper artifact manifest written to: {manifest_path}")

                for finding in audit_report.findings:
                    print(f"[{finding.severity}] {finding.code}: {finding.message}")

                raise SystemExit(1)

        run_report_path = write_paper_assembly_run_report(
            output_path=args.paper_run_report_path,
            started_at=started_at,
            source_registry_path=args.source_registry_path,
            claim_inventory_path=args.claim_inventory_path
            or "data/processed/claim_inventory.json",
            evidence_integration_path=args.evidence_integration_path,
            paper_spec_path=paper_spec_path,
            html_output_path=html_output_path,
            audit_requested=args.audit_after_assembly,
            audit_report_path=args.html_audit_report_path if args.audit_after_assembly else None,
            audit_passed=audit_passed,
            status="completed",
        )

        manifest_path = write_paper_artifact_manifest(
            output_path=args.paper_artifact_manifest_path,
            paper_spec_path=paper_spec_path,
            html_output_path=html_output_path,
            audit_report_path=args.html_audit_report_path if args.audit_after_assembly else None,
            run_report_path=run_report_path,
        )

        print(f"Paper assembly run report written to: {run_report_path}")
        print(f"Paper artifact manifest written to: {manifest_path}")
        return

    if args.stage == "audit_html_paper":
        if forwarded:
            parser.error(
                "unrecognized arguments for audit_html_paper: {}".format(
                    " ".join(forwarded)
                )
            )

        report = audit_html_paper(
            html_path=args.html_output_path,
            paper_spec_path=args.paper_spec_path,
            report_output_path=args.html_audit_report_path,
        )

        print(f"HTML audit report written to: {args.html_audit_report_path}")
        print(f"HTML audit passed: {report.passed}")

        if not report.passed:
            for finding in report.findings:
                print(f"[{finding.severity}] {finding.code}: {finding.message}")

            raise SystemExit(1)

        return

    if args.stage == "evaluation":
        raise SystemExit(run_evaluation_pipeline(forwarded))

    if args.stage == "sample_artifact":
        return run_sample_artifact_pipeline(forwarded)

    if args.stage == "evidence_integration":
        from src.pipelines.run_evidence_integration_pipeline import (
            run_evidence_integration_pipeline,
        )

        if forwarded:
            parser.error(
                "unrecognized arguments for evidence_integration: {}".format(
                    " ".join(forwarded)
                )
            )

        result = run_evidence_integration_pipeline(
            claim_inventory_path=Path(
                args.claim_inventory_path
                or "data/processed/claim_inventory.json"
            ),
            evidence_records_path=Path(
                args.evidence_records_path
                or "data/processed/evidence_records.json"
            ),
            output_path=Path(
                args.output_path or "data/processed/adjudications.json"
            ),
            run_log_dir=Path(args.run_log_dir or "logs/runs"),
            allow_skewed_adjudication=args.allow_skewed_adjudication,
            use_llm_narratives=args.use_llm_narratives,
        )

        print(
            "Evidence adjudications written to: "
            f"{result['metrics']['adjudications_written']} record(s)"
        )
        print(
            f"Output path: {args.output_path or 'data/processed/adjudications.json'}"
        )
        print(f"Run log: {result['run_log_path']}")

        if not result["validation"]["is_valid"]:
            print(
                "Validation warning: "
                f"{result['validation']['issue_count']} issue(s) found."
            )

        if not result["cherry_picking_guard"]["publishable_for_week8"]:
            print(
                "Cherry-picking guard warning: output is not publishable for Week 8 yet."
            )

        return result

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
        or args.evidence_records_path is not None
        or args.run_log_dir is not None
        or args.allow_skewed_adjudication
        or args.use_llm_narratives
        or args.dry_run is not None
        or args.source is not None
        or args.per_query_limit is not None
        or args.fail_on_unbalanced is not None
        or args.source_registry_path != "data/processed/source_registry.json"
        or args.evidence_integration_path != "data/outputs/evidence_integration.json"
        or args.paper_spec_output_path != "data/outputs/paper_spec.json"
        or args.paper_title is not None
        or args.paper_abstract is not None
        or args.paper_spec_path != "data/outputs/paper_spec.json"
        or args.html_output_path != "data/outputs/inquiry_paper.html"
        or args.html_audit_report_path != "data/outputs/html_audit_report.json"
        or args.paper_run_report_path != "data/outputs/paper_assembly_run_report.json"
        or args.paper_artifact_manifest_path != "data/outputs/paper_artifact_manifest.json"
        or args.audit_after_assembly
    ):
        parser.error(
            "--config-path, --claim-inventory-path, --output-path, --evidence-records-path, "
            "--run-log-dir, --allow-skewed-adjudication, --use-llm-narratives, "
            "--dry-run/--no-dry-run, --source, --per-query-limit, --fail-on-unbalanced, "
            "--source-registry-path, --evidence-integration-path, --paper-spec-output-path, "
            "--paper-title, --paper-abstract, --paper-spec-path, --html-output-path, "
            "--html-audit-report-path, --paper-run-report-path, --paper-artifact-manifest-path, "
            "and --audit-after-assembly "
            "are only valid with claim_inventory, speaker_perspective, steelman, "
            "evidence_retrieval, evidence_integration, build_paper_spec, "
            "html_paper, assemble_paper, or audit_html_paper."
        )

    _run_source_ingestion()


if __name__ == "__main__":
    main()
