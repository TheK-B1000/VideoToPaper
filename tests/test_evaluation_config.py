import json

import pytest

from src.evaluation.evaluation_config import (
    EvaluationOutputConfig,
    load_evaluation_runtime_config,
)


def test_load_evaluation_runtime_config_reads_thresholds_outputs_and_metadata(tmp_path):
    config_path = tmp_path / "evaluation_config.json"

    config_path.write_text(
        json.dumps(
            {
                "evaluation": {
                    "clip_tolerance_seconds": 2.5,
                    "minimum_balanced_retrieval_ratio": 0.9,
                },
                "outputs": {
                    "audit_report_path": "custom/audit_report.json",
                    "audit_summary_path": "custom/audit_summary.md",
                    "manifest_path": "custom/manifest.json",
                    "validation_report_path": "custom/validation_report.json",
                    "validation_summary_path": "custom/validation_summary.md",
                },
                "metadata": {
                    "run_family": "smoke_test",
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_evaluation_runtime_config(config_path)

    assert config.evaluation.clip_tolerance_seconds == 2.5
    assert config.evaluation.minimum_balanced_retrieval_ratio == 0.9
    assert config.outputs.audit_report_path == "custom/audit_report.json"
    assert config.outputs.audit_summary_path == "custom/audit_summary.md"
    assert config.outputs.manifest_path == "custom/manifest.json"
    assert config.outputs.validation_report_path == "custom/validation_report.json"
    assert config.outputs.validation_summary_path == "custom/validation_summary.md"
    assert config.metadata["run_family"] == "smoke_test"


def test_load_evaluation_runtime_config_uses_defaults_for_missing_sections(tmp_path):
    config_path = tmp_path / "evaluation_config.json"

    config_path.write_text("{}", encoding="utf-8")

    config = load_evaluation_runtime_config(config_path)

    assert config.evaluation.clip_tolerance_seconds == 1.0
    assert config.evaluation.minimum_balanced_retrieval_ratio == 0.8
    assert config.outputs == EvaluationOutputConfig()
    assert config.metadata == {}


def test_load_evaluation_runtime_config_raises_for_missing_file(tmp_path):
    missing_path = tmp_path / "missing_config.json"

    with pytest.raises(FileNotFoundError):
        load_evaluation_runtime_config(missing_path)
