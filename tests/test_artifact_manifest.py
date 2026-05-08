import hashlib
import json
from pathlib import Path

import pytest

from src.paper.artifact_manifest import (
    ArtifactManifestError,
    build_paper_artifact_manifest,
    write_paper_artifact_manifest,
)


def test_build_paper_artifact_manifest_records_required_artifacts(tmp_path: Path) -> None:
    paper_spec_path = tmp_path / "paper_spec.json"
    html_output_path = tmp_path / "inquiry_paper.html"

    paper_spec_path.write_text('{"title": "Test Paper"}', encoding="utf-8")
    html_output_path.write_text("<html><body>Test</body></html>", encoding="utf-8")

    manifest = build_paper_artifact_manifest(
        paper_spec_path=paper_spec_path,
        html_output_path=html_output_path,
    )

    manifest_dict = manifest.to_dict()

    assert manifest_dict["stage"] == "assemble_paper"

    artifacts = {
        artifact["label"]: artifact
        for artifact in manifest_dict["artifacts"]
    }

    assert artifacts["paper_spec"]["exists"] is True
    assert artifacts["paper_spec"]["size_bytes"] == len(
        paper_spec_path.read_bytes()
    )
    assert artifacts["paper_spec"]["sha256"] == hashlib.sha256(
        paper_spec_path.read_bytes()
    ).hexdigest()

    assert artifacts["html_paper"]["exists"] is True
    assert artifacts["html_paper"]["size_bytes"] == len(
        html_output_path.read_bytes()
    )
    assert artifacts["html_paper"]["sha256"] == hashlib.sha256(
        html_output_path.read_bytes()
    ).hexdigest()


def test_build_paper_artifact_manifest_records_optional_artifacts_when_present(
    tmp_path: Path,
) -> None:
    paper_spec_path = tmp_path / "paper_spec.json"
    html_output_path = tmp_path / "inquiry_paper.html"
    audit_report_path = tmp_path / "html_audit_report.json"
    run_report_path = tmp_path / "paper_assembly_run_report.json"

    paper_spec_path.write_text("spec", encoding="utf-8")
    html_output_path.write_text("html", encoding="utf-8")
    audit_report_path.write_text("audit", encoding="utf-8")
    run_report_path.write_text("run", encoding="utf-8")

    manifest = build_paper_artifact_manifest(
        paper_spec_path=paper_spec_path,
        html_output_path=html_output_path,
        audit_report_path=audit_report_path,
        run_report_path=run_report_path,
    )

    artifacts = {
        artifact.label: artifact
        for artifact in manifest.artifacts
    }

    assert artifacts["html_audit_report"].exists is True
    assert artifacts["html_audit_report"].sha256 == hashlib.sha256(
        audit_report_path.read_bytes()
    ).hexdigest()

    assert artifacts["paper_run_report"].exists is True
    assert artifacts["paper_run_report"].sha256 == hashlib.sha256(
        run_report_path.read_bytes()
    ).hexdigest()


def test_build_paper_artifact_manifest_records_missing_optional_artifact(
    tmp_path: Path,
) -> None:
    paper_spec_path = tmp_path / "paper_spec.json"
    html_output_path = tmp_path / "inquiry_paper.html"
    audit_report_path = tmp_path / "missing_html_audit_report.json"

    paper_spec_path.write_text("spec", encoding="utf-8")
    html_output_path.write_text("html", encoding="utf-8")

    manifest = build_paper_artifact_manifest(
        paper_spec_path=paper_spec_path,
        html_output_path=html_output_path,
        audit_report_path=audit_report_path,
    )

    artifacts = {
        artifact.label: artifact
        for artifact in manifest.artifacts
    }

    assert artifacts["html_audit_report"].exists is False
    assert artifacts["html_audit_report"].size_bytes is None
    assert artifacts["html_audit_report"].sha256 is None


def test_build_paper_artifact_manifest_rejects_missing_required_artifact(
    tmp_path: Path,
) -> None:
    paper_spec_path = tmp_path / "missing_paper_spec.json"
    html_output_path = tmp_path / "inquiry_paper.html"

    html_output_path.write_text("html", encoding="utf-8")

    with pytest.raises(ArtifactManifestError, match="Required artifact does not exist"):
        build_paper_artifact_manifest(
            paper_spec_path=paper_spec_path,
            html_output_path=html_output_path,
        )


def test_write_paper_artifact_manifest_writes_json_file(tmp_path: Path) -> None:
    paper_spec_path = tmp_path / "paper_spec.json"
    html_output_path = tmp_path / "inquiry_paper.html"
    manifest_output_path = tmp_path / "paper_artifact_manifest.json"

    paper_spec_path.write_text("spec", encoding="utf-8")
    html_output_path.write_text("html", encoding="utf-8")

    result = write_paper_artifact_manifest(
        output_path=manifest_output_path,
        paper_spec_path=paper_spec_path,
        html_output_path=html_output_path,
    )

    assert result == manifest_output_path
    assert manifest_output_path.exists()

    manifest = json.loads(manifest_output_path.read_text(encoding="utf-8"))

    assert manifest["stage"] == "assemble_paper"

    artifacts = {
        artifact["label"]: artifact
        for artifact in manifest["artifacts"]
    }

    assert artifacts["paper_spec"]["exists"] is True
    assert artifacts["html_paper"]["exists"] is True
