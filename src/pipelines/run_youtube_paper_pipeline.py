"""
End-to-end local run: YouTube URL → HTML inquiry paper.

Uses Week 1 ``main.py --youtube-url`` paths aligned with ``configs/argument_config.json``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.argument.run_argument_structure import run_argument_structure
from src.core.dotenv_bootstrap import try_load_dotenv
from src.frontend.inquiry_library_manifest import try_register_studio_library_after_assembly
from src.pipelines.claim_inventory_pipeline import run_claim_inventory_pipeline
from src.pipelines.paper_evidence_integration_finalize import (
    finalize_evidence_integration_json_for_paper,
)
from src.pipelines.run_evidence_integration_pipeline import (
    run_evidence_integration_pipeline,
)
from src.pipelines.run_evidence_retrieval_cli import run_evidence_retrieval_cli
from src.pipelines.run_steelman_pipeline import main as steelman_main


def run_youtube_paper_pipeline(
    *,
    repo_root: Path,
    youtube_url: str,
    config_path: str = "configs/argument_config.json",
    speaker_name: str | None = None,
    audit_after_assembly: bool = False,
    stub_evidence_retrieval: bool = False,
) -> int:
    """
    Run ingestion → argument structure → claims → steelman → retrieval → integration → finalize → assemble.

    Returns:
        Process exit code (0 on success).
    """
    try_load_dotenv()

    root = repo_root.resolve()
    py = sys.executable
    main_py = root / "main.py"

    ingest_cmd = [py, "-u", str(main_py), "--youtube-url", youtube_url.strip()]
    if speaker_name:
        ingest_cmd.extend(["--speaker-name", speaker_name.strip()])
    subprocess.run(ingest_cmd, cwd=root, check=True)

    run_argument_structure(config_path)

    run_claim_inventory_pipeline(config_path=config_path)

    steel_exit = steelman_main(["--config-path", config_path])
    if steel_exit != 0:
        return int(steel_exit)

    retrieval_path = Path(
        run_evidence_retrieval_cli(
            config_path=config_path,
            dry_run=stub_evidence_retrieval,
        ),
    ).resolve()

    evidence_records_path = retrieval_path.with_name("evidence_records.json")

    integration_out = root / "data" / "outputs" / "evidence_integration.json"
    run_evidence_integration_pipeline(
        claim_inventory_path=root / "data" / "processed" / "claim_inventory.json",
        evidence_records_path=evidence_records_path,
        output_path=integration_out,
    )

    finalize_evidence_integration_json_for_paper(
        integration_path=integration_out,
        speaker_perspective_path=root / "data" / "processed" / "speaker_perspective.json",
        evidence_records_path=evidence_records_path,
    )

    assemble_cmd = [py, "-u", str(main_py), "--stage", "assemble_paper"]
    if audit_after_assembly:
        assemble_cmd.append("--audit-after-assembly")
    subprocess.run(assemble_cmd, cwd=root, check=True)

    html_out = root / "data" / "outputs" / "inquiry_paper.html"
    print(f"Inquiry paper HTML: {html_out}")
    try_register_studio_library_after_assembly(root)
    return 0
