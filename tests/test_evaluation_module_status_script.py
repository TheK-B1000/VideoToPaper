from scripts.evaluation_module_status import (
    REQUIRED_DOC_ARTIFACTS,
    REQUIRED_EXPORT_SMOKE_ARTIFACTS,
    REQUIRED_SMOKE_ARTIFACTS,
    all_present,
    check_required_files,
    main,
    render_status_report,
    write_status_report,
)


def _write_required_files(base_dir, relative_paths, content="{}"):
    for relative_path in relative_paths:
        path = base_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def test_all_present_returns_true_when_everything_exists():
    assert all_present({"a": True, "b": True}) is True


def test_all_present_returns_false_when_anything_is_missing():
    assert all_present({"a": True, "b": False}) is False


def test_check_required_files_reports_existing_and_missing_files(tmp_path):
    existing = tmp_path / "exists.txt"
    existing.write_text("ok", encoding="utf-8")

    results = check_required_files(
        tmp_path,
        [
            "exists.txt",
            "missing.txt",
        ],
    )

    assert results["exists.txt"] is True
    assert results["missing.txt"] is False


def test_render_status_report_marks_module_ready_when_all_artifacts_exist(tmp_path):
    smoke_results = {path: True for path in REQUIRED_SMOKE_ARTIFACTS}
    export_smoke_results = {path: True for path in REQUIRED_EXPORT_SMOKE_ARTIFACTS}
    docs_results = {path: True for path in REQUIRED_DOC_ARTIFACTS}

    report = render_status_report(
        smoke_output_dir=tmp_path / "smoke",
        export_smoke_output_dir=tmp_path / "export_smoke",
        docs_output_dir=tmp_path / "docs",
        smoke_results=smoke_results,
        export_smoke_results=export_smoke_results,
        docs_results=docs_results,
    )

    assert "# Evaluation Module Status Report" in report
    assert "**Module Ready:** YES" in report
    assert "## Export-And-Evaluate Bridge Artifacts" in report
    assert "ready to close" in report


def test_render_status_report_marks_module_not_ready_when_export_bridge_is_missing(tmp_path):
    smoke_results = {path: True for path in REQUIRED_SMOKE_ARTIFACTS}
    export_smoke_results = {path: True for path in REQUIRED_EXPORT_SMOKE_ARTIFACTS}
    docs_results = {path: True for path in REQUIRED_DOC_ARTIFACTS}
    export_smoke_results["paper_artifact.json"] = False

    report = render_status_report(
        smoke_output_dir=tmp_path / "smoke",
        export_smoke_output_dir=tmp_path / "export_smoke",
        docs_output_dir=tmp_path / "docs",
        smoke_results=smoke_results,
        export_smoke_results=export_smoke_results,
        docs_results=docs_results,
    )

    assert "**Module Ready:** NO" in report
    assert "- [ ] `paper_artifact.json`" in report
    assert "missing one or more required artifacts" in report


def test_write_status_report_creates_report(tmp_path):
    smoke_output_dir = tmp_path / "smoke"
    export_smoke_output_dir = tmp_path / "export_smoke"
    docs_output_dir = tmp_path / "docs"
    output_path = tmp_path / "status.md"

    _write_required_files(smoke_output_dir, REQUIRED_SMOKE_ARTIFACTS)
    _write_required_files(export_smoke_output_dir, REQUIRED_EXPORT_SMOKE_ARTIFACTS)
    _write_required_files(docs_output_dir, REQUIRED_DOC_ARTIFACTS, content="# doc\n")

    written_path = write_status_report(
        smoke_output_dir=smoke_output_dir,
        export_smoke_output_dir=export_smoke_output_dir,
        docs_output_dir=docs_output_dir,
        output_path=output_path,
    )

    assert written_path == output_path
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")

    assert "# Evaluation Module Status Report" in content
    assert "**Module Ready:** YES" in content
    assert "## Export-And-Evaluate Bridge Artifacts" in content


def test_status_cli_writes_report(tmp_path, capsys):
    smoke_output_dir = tmp_path / "smoke"
    export_smoke_output_dir = tmp_path / "export_smoke"
    docs_output_dir = tmp_path / "docs"
    output_path = tmp_path / "evaluation_module_status.md"

    _write_required_files(smoke_output_dir, REQUIRED_SMOKE_ARTIFACTS)
    _write_required_files(export_smoke_output_dir, REQUIRED_EXPORT_SMOKE_ARTIFACTS)
    _write_required_files(docs_output_dir, REQUIRED_DOC_ARTIFACTS, content="# doc\n")

    exit_code = main(
        [
            "--smoke-output-dir",
            str(smoke_output_dir),
            "--export-smoke-output-dir",
            str(export_smoke_output_dir),
            "--docs-output-dir",
            str(docs_output_dir),
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert output_path.exists()
    assert "Evaluation module status report written to:" in captured.out
