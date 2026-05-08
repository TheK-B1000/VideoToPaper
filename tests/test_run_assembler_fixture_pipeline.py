from src.pipelines.run_assembler_fixture_pipeline import (
    run_assembler_fixture_pipeline,
)


def test_run_assembler_fixture_pipeline_writes_fixture_files(tmp_path):
    exit_code = run_assembler_fixture_pipeline(
        [
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "claims.json").exists()
    assert (tmp_path / "speaker_perspective.json").exists()
    assert (tmp_path / "adjudications.json").exists()
    assert (tmp_path / "evidence_records.json").exists()
