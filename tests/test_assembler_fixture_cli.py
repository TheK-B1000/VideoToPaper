from src.evaluation.assembler_fixture_cli import main


def test_assembler_fixture_cli_writes_fixture_files(tmp_path, capsys):
    exit_code = main(
        [
            "--output-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Assembler fixtures written:" in captured.out

    assert (tmp_path / "claims.json").exists()
    assert (tmp_path / "speaker_perspective.json").exists()
    assert (tmp_path / "adjudications.json").exists()
    assert (tmp_path / "evidence_records.json").exists()
